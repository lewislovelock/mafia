import asyncio
import httpx
import json
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

# Role to emoji mapping
ROLE_EMOJIS = {
    "Werewolf": "🐺",
    "Seer": "🔮",
    "Witch": "🧙",
    "Villager": "👤",
    "God": "⚡"
}

class GameViewer:
    def __init__(self, god_mode: bool = False):
        self.buffer = {}  # {(type, agent): accumulated_content}
        self.player_roles = {}  # {agent_name: role}
        self.god_mode = god_mode
        
    async def watch_stream(self):
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", "http://127.0.0.1:8000/stream", timeout=None) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        event = json.loads(data)
                        await self.handle_event(event)
    
    def get_emoji(self, agent_name):
        """Get emoji for agent based on their role (if God Mode) or generic"""
        # God is always known
        if agent_name == "God":
            return ROLE_EMOJIS["God"]
        
        # In God Mode, show real role emoji
        if self.god_mode and agent_name in self.player_roles:
            role = self.player_roles[agent_name]
            return ROLE_EMOJIS.get(role, "🎭")
        
        # Normal mode: generic player emoji
        return "🎭"
    
    async def handle_event(self, event):
        event_type = event["type"]
        agent = event["agent"]
        content = event["content"]
        key = (event_type, agent)
        
        # For system and phase, display immediately (no buffering)
        if event_type in ["system", "phase"]:
            if event_type == "system":
                console.print(Panel(f"[bold cyan]{content}[/]", title="⚙️ System", border_style="cyan"))
                
                # Check if this is role assignment info (parse from startup)
                if "Player Assignment" in content and self.god_mode:
                    # We'll receive role info from API eventually
                    pass
                    
            elif event_type == "phase":
                console.print(f"\n[bold yellow]{'━' * 70}[/]")
                console.print(Panel(f"[bold yellow]{content}[/]", title="🎭 Phase", border_style="yellow"))
                console.print(f"[bold yellow]{'━' * 70}[/]\n")
            return
        
        # Buffer thought, speech, action chunks
        if event_type in ["thought", "speech", "action"]:
            if key not in self.buffer:
                self.buffer[key] = ""
            self.buffer[key] += content
            
            # Check if this seems like end of message (newline or sentence end)
            if content.endswith(("\n", ".", "!", "?")):
                # Display accumulated message
                full_message = self.buffer[key].strip()
                if full_message:
                    self.display_message(event_type, agent, full_message)
                # Clear buffer
                del self.buffer[key]
        
        # Game over
        elif event_type == "game_over":
            console.print(Panel(f"[bold red]{content}[/]", title="🏁 Game Over", border_style="red"))
    
    def display_message(self, event_type, agent, content):
        emoji = self.get_emoji(agent)
        
        if event_type == "thought":
            console.print(f"[dim italic cyan]💭 {emoji} {agent}: {content}[/]")
        elif event_type == "speech":
            console.print(f"[bold white]{emoji} {agent}:[/] [green]{content}[/]")
        elif event_type == "action":
            console.print(f"[bold magenta]⚡ {emoji} {agent} → {content}[/]")

async def fetch_role_mapping(viewer: GameViewer):
    """Fetch role mapping from API for God Mode"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://127.0.0.1:8000/roles")
            if response.status_code == 200:
                viewer.player_roles = response.json()
                console.print("[dim]God Mode: Role mapping loaded[/]\n")
    except:
        console.print("[dim yellow]Warning: Could not load role mapping[/]\n")

async def main():
    console.print(Panel("[bold cyan]🐺 Werewolf Arena - Terminal Viewer 🐺[/]", border_style="cyan"))
    
    # Ask for God Mode
    god_mode = Confirm.ask("🔮 Enable God Mode (see real player roles)?", default=False)
    
    console.print("[dim]Connecting to game stream...[/]\n")
    
    # Start game
    async with httpx.AsyncClient() as client:
        await client.post("http://127.0.0.1:8000/start")
    
    viewer = GameViewer(god_mode=god_mode)
    
    # Fetch roles if God Mode enabled
    if god_mode:
        await fetch_role_mapping(viewer)
    
    await viewer.watch_stream()

if __name__ == "__main__":
    asyncio.run(main())
