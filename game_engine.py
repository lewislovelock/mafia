import asyncio
import json
from typing import List, Dict, Optional
from agents import Agent, God, Werewolf, Seer, Witch

class GameEngine:
    def __init__(self, players: List[Agent]):
        self.players = players
        self.alive_players = [p.name for p in players if p.is_alive and p.role != "God"]
        self.god = next((p for p in players if isinstance(p, God)), None)
        self.roles = {p.name: p.role for p in players}
        self.event_queue = asyncio.Queue()
        self.is_game_over = False
        
        if not self.god:
            raise ValueError("Game must have a God agent.")

    async def broadcast(self, event_type: str, agent_name: str, content: str):
        event = {
            "type": event_type,
            "agent": agent_name,
            "content": content
        }
        await self.event_queue.put(json.dumps(event))

    async def start_game(self):
        await self.broadcast("system", "System", "Game Started")
        
        while not self.is_game_over:
            # Night Phase
            await self.run_night_phase()
            if self.check_game_over(): break
            
            # Day Phase
            await self.run_day_phase()
            if self.check_game_over(): break

    async def run_night_phase(self):
        await self.broadcast("phase", "System", "Night Phase Started")
        
        async for chunk in self.god.announce("The night has fallen. Everyone close your eyes."):
            await self.broadcast("speech", "God", chunk)
        
        # 1. Werewolves Action
        victim = await self.process_werewolves()
        
        # 2. Seer Action
        await self.process_seer()
        
        # 3. Witch Action
        final_victim = await self.process_witch(victim)
        
        # 4. Resolve Night
        if final_victim:
            self.eliminate_player(final_victim)
            async for chunk in self.god.announce(f"Last night, {final_victim} died."):
                await self.broadcast("speech", "God", chunk)
        else:
            async for chunk in self.god.announce("Last night, no one died. It was a peaceful night."):
                await self.broadcast("speech", "God", chunk)
            
        await self.broadcast("phase", "System", "Night Phase Ended")

    async def run_day_phase(self):
        await self.broadcast("phase", "System", "Day Phase Started")
        
        # 1. Discussion (Simplified: Random subset speaks)
        speakers = [p for p in self.players if p.name in self.alive_players][:3]
        for speaker in speakers:
            context = f"Alive players: {', '.join(self.alive_players)}. Discuss who might be the werewolf."
            
            # Think
            await self.broadcast("thought", speaker.name, "[Thinking...]")
            async for chunk in speaker.think(context):
                await self.broadcast("thought", speaker.name, chunk)
            
            # Speak
            async for chunk in speaker.speak(context):
                await self.broadcast("speech", speaker.name, chunk)
            
            await asyncio.sleep(1.5)  # Rate limit protection between speakers

        # 2. Voting - Collect votes from all players
        await self.broadcast("system", "System", "Voting phase started.")
        
        votes = {}  # {voter_name: voted_name}
        voters = [p for p in self.players if p.name in self.alive_players]
        
        for voter in voters:
            context = f"Alive players: {', '.join(self.alive_players)}. Based on today's discussion, who should be eliminated?"
            
            vote = await voter.vote(context, broadcast_callback=self.broadcast)
            votes[voter.name] = vote
            await self.broadcast("action", voter.name, f"Voted for {vote}")
            await asyncio.sleep(1)  # Rate limit protection
        
        # Count votes
        from collections import Counter
        vote_counts = Counter(votes.values())
        
        if vote_counts:
            # Get player with most votes
            eliminated, count = vote_counts.most_common(1)[0]
            
            # Check if they're actually alive (LLM might hallucinate)
            if eliminated in self.alive_players:
                self.eliminate_player(eliminated)
                async for chunk in self.god.announce(f"By majority vote, {eliminated} has been eliminated."):
                    await self.broadcast("speech", "God", chunk)
            else:
                await self.broadcast("system", "System", f"Invalid vote target: {eliminated}. No elimination.")
        
        await self.broadcast("phase", "System", "Day Phase Ended")

    async def process_werewolves(self) -> Optional[str]:
        werewolves = [p for p in self.players if isinstance(p, Werewolf) and p.is_alive]
        if not werewolves:
            return None
            
        votes = []
        for wolf in werewolves:
            vote = await wolf.kill(self.alive_players, teammate_votes=votes, broadcast_callback=self.broadcast)
            votes.append(vote)
            await asyncio.sleep(1)  # Rate limit protection
            
        if not votes:
            return None
            
        from collections import Counter
        vote_counts = Counter(votes)
        victim = vote_counts.most_common(1)[0][0]
        
        for wolf in werewolves:
            wolf.add_memory(f"The pack decided to target {victim}.")
            
        return victim

    async def process_seer(self):
        seer = next((p for p in self.players if isinstance(p, Seer) and p.is_alive), None)
        if not seer:
            return

        target_name = await seer.verify(self.alive_players, broadcast_callback=self.broadcast)
        
        target_role = self.roles.get(target_name, "Unknown")
        seer.add_memory(f"You checked {target_name}: {target_role}.")
        await asyncio.sleep(1)  # Rate limit protection

    async def process_witch(self, victim: Optional[str]) -> Optional[str]:
        witch = next((p for p in self.players if isinstance(p, Witch) and p.is_alive), None)
        if not witch:
            return victim

        night_info = f"Target attacked: {victim}." if victim else "No attack tonight."
        
        decision = await witch.use_potion(night_info, broadcast_callback=self.broadcast)
        
        parts = decision.split()
        action = parts[0].upper()
        
        if action == "SAVE" and victim:
            witch.add_memory(f"You saved {victim}.")
            await asyncio.sleep(1)  # Rate limit protection
            return None
        elif action == "POISON" and len(parts) > 1:
            target = parts[1]
            if target in self.alive_players:
                witch.add_memory(f"You poisoned {target}.")
                await asyncio.sleep(1)  # Rate limit protection
                return target
        
        await asyncio.sleep(1)  # Rate limit protection
        return victim

    def eliminate_player(self, player_name: str):
        if player_name in self.alive_players:
            self.alive_players.remove(player_name)
            player = next((p for p in self.players if p.name == player_name), None)
            if player:
                player.is_alive = False
                player.status = "dead"
                
    def check_game_over(self) -> bool:
        wolves = [p for p in self.players if isinstance(p, Werewolf) and p.is_alive]
        villagers = [p for p in self.players if not isinstance(p, Werewolf) and p.role != "God" and p.is_alive]
        
        if not wolves:
            self.is_game_over = True
            asyncio.create_task(self.broadcast("game_over", "System", "Villagers Win! All Werewolves are dead."))
            return True
        if len(wolves) >= len(villagers):
            self.is_game_over = True
            asyncio.create_task(self.broadcast("game_over", "System", "Werewolves Win! They outnumber the Villagers."))
            return True
            
        return False
