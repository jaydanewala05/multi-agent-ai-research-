import json
from pathlib import Path

def load_json(path: str):
    """Load JSON file safely."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON {path}: {e}")
        return {}

def save_json(path: str, data: dict):
    """Save JSON data safely."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving JSON {path}: {e}")

def ensure_dir(path: str):
    """Ensure a directory exists."""
    Path(path).mkdir(parents=True, exist_ok=True)

def pretty_print(title: str, content: str):
    print("\n" + "=" * 60)
    print(title.upper())
    print("=" * 60)
    print(content)
    print("=" * 60 + "\n")
