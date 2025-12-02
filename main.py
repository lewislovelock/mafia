import asyncio
import uvicorn
from src.agents import Agent, God, Werewolf, Seer, Witch
from src.game_engine import GameEngine
from src.api import app


if __name__ == "__main__":
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=True)
