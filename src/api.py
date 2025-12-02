import asyncio
import json
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from .agents import Agent, God, Werewolf, Seer, Witch
from .game_engine import GameEngine

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global game engine instance
engine: GameEngine = None

def init_game():
    global engine
    print("Initializing Werewolf Arena...")
    
    # Load configuration
    from .config import GameConfig
    config = GameConfig("game_config.yaml")
    
    # Get prompts based on language
    prompts = config.get_prompts()
    
    # Assign roles randomly
    player_configs = config.assign_roles()
    
    print(f"Game Mode: {config.config['mode']}")
    print(f"Language: {config.config['language']}")
    print("\nPlayer Assignment:")
    for pc in player_configs:
        print(f"  - {pc['name']}: {pc['role']} (Model: {pc['model']})")
    print()
    
    # Create God
    god = God("God", "x-ai/grok-4.1-fast:free", "God", prompts["god"])
    
    # Create players based on configuration
    players = [god]
    for pc in player_configs:
        role_type = pc["role"]
        name = pc["name"]
        model = pc["model"]
        prompt = prompts.get(role_type, prompts["villager"])
        
        if role_type == "werewolf":
            players.append(Werewolf(name, model, "Werewolf", prompt))
        elif role_type == "seer":
            players.append(Seer(name, model, "Seer", prompt))
        elif role_type == "witch":
            players.append(Witch(name, model, "Witch", prompt))
        else:  # villager
            players.append(Agent(name, model, "Villager", prompt))
    
    engine = GameEngine(players)
    
    # Store role mapping for God Mode in terminal
    engine.role_mapping = {p.name: p.role for p in players if p.name != "God"}

@app.on_event("startup")
async def startup_event():
    init_game()

@app.post("/start")
async def start_game():
    if not engine:
        init_game()
    
    # Run game in background
    asyncio.create_task(engine.start_game())
    return {"status": "Game started"}

@app.get("/roles")
async def get_roles():
    """Endpoint for God Mode to get player roles"""
    if not engine:
        return {}
    return getattr(engine, 'role_mapping', {})

@app.get("/stream")
async def stream(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            
            # Get event from queue
            event_json = await engine.event_queue.get()
            yield f"data: {event_json}\n\n"
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")
