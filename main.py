import asyncio
import uvicorn
from agents import Agent, God, Werewolf, Seer, Witch
from game_engine import GameEngine


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
