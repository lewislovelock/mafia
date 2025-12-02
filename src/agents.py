import os

from openai import AsyncOpenAI
from dotenv import load_dotenv
from typing import List, AsyncGenerator

load_dotenv()

# Import prompts
from .prompts import PROMPTS_EN, PROMPTS_ZH  
from .config import GameConfig

# Initialize config to get language setting
_config = GameConfig("game_config.yaml")
PROMPTS = PROMPTS_ZH if _config.config['language'] == 'zh' else PROMPTS_EN

# Initialize OpenAI client for OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

class Agent:
    def __init__(self, name: str, model: str, role: str, system_prompt: str):
        self.name = name
        self.model = model
        self.role = role
        self.system_prompt = system_prompt
        self.is_alive = True
        self.status = "idle"
        self.thought_process = ""
        self.last_message = ""
        self.history: List[dict] = []  # Memory: list of {role: str, content: str}
    
    def add_memory(self, content: str):
        """Add a system notification to agent's memory"""
        self.history.append({"role": "user", "content": f"[System Notification]: {content}"})
    
    async def vote(self, context: str, round_num: int, game_intro: str, broadcast_callback=None) -> str:
        """Vote for a player to eliminate during day phase"""
        task = "Vote to eliminate one player you believe is a werewolf."
        instruction = "Output ONLY the player's name. No other text."
        
        return await self.act(context, round_num, game_intro, task, instruction, broadcast_callback)

    async def think(self, context: str, round_num: int, game_intro: str) -> AsyncGenerator[str, None]:
        self.status = "reasoning"
        self.thought_process = ""
        
        prompt = PROMPTS["think"].format(
            context=context,
            round=round_num,
            game_intro=game_intro,
            player_name=self.name
        )
        async for chunk in self.call_model(prompt, stream=_config.config['enable_streaming']):
            yield chunk

        self.status = "idle"

    async def speak(self, context: str, round_num: int, game_intro: str) -> AsyncGenerator[str, None]:
        self.status = "speaking"
        self.last_message = ""
        
        prompt = PROMPTS["speak"].format(
            context=context,
            round=round_num,
            game_intro=game_intro,
            player_name=self.name,
            thought_process=self.thought_process
        )
        async for chunk in self.call_model(prompt, stream=_config.config['enable_streaming']):
            yield chunk

        self.status = "idle"        

    async def act(self, context: str, round_num: int, game_intro: str, task: str, output_instruction: str, broadcast_callback=None):
        """
        Generic method for agent to make a decision.
        Returns the decision as a string.
        Optionally broadcasts thought chunks via callback.
        """
        self.status = "reasoning"
        self.thought_process = ""
        
        # 1. First, think about the decision
        think_prompt = PROMPTS["act_think"].format(
            context=context,
            round=round_num,
            game_intro=game_intro,
            player_name=self.name,
            task=task
        )
        
        # Stream the thought process
        if broadcast_callback:
            async for chunk in self.call_model(think_prompt, stream=_config.config['enable_streaming']):
                await broadcast_callback("thought", self.name, chunk)
        else:
            # If no callback, just run it non-stream to populate thought_process
            async for _ in self.call_model(think_prompt, stream=False):
                pass
        
        # 2. Then, make the final decision
        decide_prompt = PROMPTS["act_decide"].format(
            context=context,
            round=round_num,
            game_intro=game_intro,
            player_name=self.name,
            thought_process=self.thought_process,
            task=task,
            output_instruction=output_instruction
        )
        
        decision = ""
        try:
            self.last_message = ""
            if broadcast_callback:
                # If broadcasting, we can stream the action too if desired, 
                # but usually action is short. Let's stream it for consistency if callback exists.
                async for chunk in self.call_model(decide_prompt, stream=_config.config['enable_streaming']):
                    await broadcast_callback("action", self.name, chunk)
            else:
                # Non-stream call for decision
                async for _ in self.call_model(decide_prompt, stream=False):
                    pass
            
            decision = self.last_message.strip()
            
        except Exception as e:
            decision = f"Error deciding: {str(e)}"

        self.status = "idle"
        return decision

    def add_memory(self, content: str):
        """
        Inject external information into the agent's memory.
        """
        self.history.append({"role": "user", "content": f"[System Notification]: {content}"})

    async def call_model(self, prompt: str, stream: bool = True) -> AsyncGenerator[str, None]:
        """
        Call the LLM model.
        :param prompt: The user prompt
        :param stream: Whether to stream the response (yield chunks) or yield once (full response)
        """
        try:
            # Construct messages with history
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": prompt})

            if stream:
                response_stream = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True
                )

                full_response = ""
                async for chunk in response_stream:
                    content = chunk.choices[0].delta.content
                    if content:
                        self.thought_process += content if self.status == "reasoning" else ""
                        self.last_message += content
                        full_response += content
                        yield content
                # Yield a newline to ensure the viewer flushes the buffer
                yield "\n"
            else:
                response = await client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=False
                )
                
                content = response.choices[0].message.content or ""
                self.thought_process += content if self.status == "reasoning" else ""
                self.last_message += content
                full_response = content
                # Append newline to ensure viewer flushes
                yield content + "\n"

            # Update history after successful completion
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_msg = f"Error speaking: {str(e)}"
            self.last_message = error_msg
            yield error_msg


class God(Agent):
    def __init__(self, name: str, model: str, role: str, system_prompt: str):
        super().__init__(
            "GOD", 
            "x-ai/grok-4.1-fast:free", # Use a fast model for the host
            "God", 
            "You are the God of the Werewolf Arena. You are omniscient and omnipotent. You can see the inner thoughts of all players."
        )

    async def announce(self, message: str) -> AsyncGenerator[str, None]:
        self.status = "speaking"
        self.last_message = ""
        
        prompt = PROMPTS["god_announce"].format(message=message)

        async for chunk in self.call_model(prompt, stream=_config.config['enable_streaming']):
            yield chunk

        self.status = "idle"

class Werewolf(Agent):
    def __init__(self, name: str, model: str, role: str, system_prompt: str):
        super().__init__(
            name, 
            model, 
            role, 
            system_prompt
        )
    
    async def kill(self, alive_players: List[str], round_num: int, game_intro: str, teammates: List[str] = None, teammate_votes: List[str] = None, broadcast_callback=None) -> str:
        context = f"Alive players: {', '.join(alive_players)}"
        if teammates:
            # Filter out self from teammates list for clarity
            other_wolves = [t for t in teammates if t != self.name]
            if other_wolves:
                context += f"\nYour Werewolf Teammates: {', '.join(other_wolves)}"
        
        if teammate_votes:
            context += f"\nOther pack members voted: {', '.join(teammate_votes)}"
            
        task = "Choose one player to eliminate tonight."
        instruction = "Output ONLY the name. No other text."
        
        return await self.act(context, round_num, game_intro, task, instruction, broadcast_callback)


class Seer(Agent):
    def __init__(self, name: str, model: str, role: str, system_prompt: str):
        super().__init__(
            name, 
            model, 
            role, 
            system_prompt
        )
    
    async def verify(self, alive_players: List[str], round_num: int, game_intro: str, broadcast_callback=None) -> str:
        context = f"Alive players: {', '.join(alive_players)}"
        task = "Choose one player to check their identity."
        instruction = "Output ONLY the name. No other text."
        
        return await self.act(context, round_num, game_intro, task, instruction, broadcast_callback)

class Witch(Agent):
    def __init__(self, name: str, model: str, role: str, system_prompt: str):
        super().__init__(
            name, 
            model, 
            role, 
            system_prompt
        )
    
    async def use_potion(self, night_info: str, round_num: int, game_intro: str, broadcast_callback=None) -> str:
        context = f"Night Info: {night_info}"
        task = "Decide potion usage: Save victim, Poison someone, or Pass."
        instruction = "Output format: 'SAVE' or 'POISON <Name>' or 'PASS'. Output ONLY the decision."
        
        return await self.act(context, round_num, game_intro, task, instruction, broadcast_callback)