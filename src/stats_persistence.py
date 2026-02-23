import json
import os

STATS_FILE = "data/stats.json"

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"hits": 0, "misses": 0, "total_input": 0, "total_output": 0}

def save_stats(hits, misses, total_input, total_output):
    data = {
        "hits": hits,
        "misses": misses,
        "total_input": total_input,
        "total_output": total_output
    }
    try:
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Warning: Could not save stats to {STATS_FILE}: {e}")
