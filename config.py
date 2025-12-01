import yaml
import random
from typing import List, Dict
from prompts import PROMPTS_EN, PROMPTS_ZH

# Default configuration
DEFAULT_CONFIG = {
    "mode": "test",  # "test" or "arena"
    "language": "en",  # "en" or "zh"
    "num_players": 6,
    "roles": {
        "werewolf": 2,
        "seer": 1,
        "witch": 1,
        "villager": 2
    },
    "player_names": [
        "Alice", "Bob", "Charlie", "Diana", 
        "Eve", "Frank", "Grace", "Henry"
    ],
    "models": {
        "test": "x-ai/grok-4.1-fast:free",
        "arena": [
            "openai/gpt-5.1",
            "google/gemini-3-pro-preview",
            "anthropic/claude-sonnet-4.5",
            "x-ai/grok-4",
            "moonshotai/kimi-k2-thinking",
            "qwen/qwen3-235b-a22b-2507",
            "deepseek/deepseek-chat-v3-0324"
        ]
    }
}


class GameConfig:
    def __init__(self, config_path: str = None):
        self.config = DEFAULT_CONFIG.copy()
        if config_path:
            self.load_config(config_path)
    
    def load_config(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                self.config.update(user_config)
        except FileNotFoundError:
            print(f"Config file {path} not found. Using default config.")
    
    def get_prompts(self) -> Dict[str, str]:
        """Get prompts based on language setting"""
        if self.config["language"] == "zh":
            return PROMPTS_ZH
        return PROMPTS_EN
    
    def get_models(self) -> List[str]:
        """Get model list based on mode"""
        if self.config["mode"] == "arena":
            return self.config["models"]["arena"]
        else:
            # Test mode: use free model for all players
            return [self.config["models"]["test"]]
    
    def assign_roles(self) -> List[Dict[str, str]]:
        """Randomly assign roles to players"""
        roles = []
        for role, count in self.config["roles"].items():
            roles.extend([role] * count)
        
        # Shuffle roles
        random.shuffle(roles)
        
        # Assign names
        names = self.config["player_names"][:len(roles)]
        random.shuffle(names)
        
        # Get models
        models = self.get_models()
        
        # Assign models (in arena mode, one model per player)
        if self.config["mode"] == "arena":
            random.shuffle(models)
            player_models = models[:len(roles)]
        else:
            # Test mode: same model for all
            player_models = [models[0]] * len(roles)
        
        # Create player configurations
        players = []
        for name, role, model in zip(names, roles, player_models):
            players.append({
                "name": name,
                "role": role,
                "model": model
            })
        
        return players
