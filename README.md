# 🐺 LLM Werewolf Arena

> **"The night has fallen... close your eyes."**

This project is an AI-powered **Werewolf (Mafia)** game arena where Large Language Models (LLMs) play against each other. It features a robust game engine, role-specific agent logic, and a real-time terminal viewer with typewriter-style streaming.

Instead of just chatting with an LLM, watch them deceive, deduce, and eliminate each other in a battle of wits.

## 🌟 Features

- **Multi-Agent System**: 6+ AI players (Werewolves, Seer, Witch, Villagers) powered by OpenRouter.
- **Role-Specific Logic**: 
  - 🐺 **Werewolves**: Coordinate with teammates (yes, they know who their pack is!) and choose night targets.
  - 🔮 **Seer**: Verifies identities and leads the village.
  - 🧙 **Witch**: Strategic use of Antidote and Poison.
  - 👤 **Villagers**: Deduce logic from discussions and votes.
- **Real-Time Streaming**: Watch the game unfold with a cinematic typewriter effect in your terminal.
- **God Mode**: Peek at all player roles and internal thought processes.
- **Configurable**: Easily toggle languages (EN/ZH), streaming effects, and model selection via YAML.

## 🛠️ Setup

This project uses **[uv](https://github.com/astral-sh/uv)** for lightning-fast Python dependency management.

### 1. Install Dependencies

Navigate to the backend directory and sync dependencies:

```bash
cd backend
uv sync
```

### 2. Configure API Key

Create a `.env` file in the `backend` directory:

```bash
# backend/.env
OPENROUTER_API_KEY=sk-or-v1-...
```

> Get your API key at [openrouter.ai](https://openrouter.ai).

### 3. Game Configuration (Optional)

Edit `backend/game_config.yaml` to customize the experience:

```yaml
# backend/game_config.yaml
language: zh              # 'en' or 'zh'
enable_streaming: true    # Typewriter effect
num_players: 6
roles:
  werewolf: 2
  seer: 1
  witch: 1
  villager: 2
```

## 🚀 Running the Arena

You need two terminal windows.

### Terminal 1: Game Server

Start the backend server:

```bash
cd backend
uv run main.py
```

### Terminal 2: Terminal Viewer

Launch the immersive terminal client:

```bash
cd backend
uv run src/play.py
```

Follow the prompts to enable **God Mode** if you want to see everyone's hidden roles!

## 🏗️ Tech Stack

- **Backend**: FastAPI, Python 3.10+, Asyncio
- **AI**: OpenRouter API (Access to GPT-4, Claude 3.5, Gemini Pro, etc.)
- **UI**: Rich (for beautiful terminal output)
- **Package Manager**: uv

## ⚠️ Vibe Code Alert

This project was vibe coded to explore agentic behaviors in social deduction games. It's designed to be fun, experimental, and a bit chaotic. The agents might hallucinate, the wolves might accidentally eat their friends (though we fixed that!), and the logic might get wild. Enjoy the show!
