import os
import pickle
from pathlib import Path

BASE = Path(os.getenv("CACHE_DIR", "/tmp/ai_stock_agent_cache"))
BASE.mkdir(parents=True, exist_ok=True)

def save(name: str, obj):
    path = BASE / f"{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load(name: str):
    path = BASE / f"{name}.pkl"
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)
