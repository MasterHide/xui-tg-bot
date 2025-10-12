import json, os, sys

def load_config():
    path = "config/config.json"
    if not os.path.exists(path):
        print("❌ Missing config/config.json. Copy from config.sample.json and edit.")
        sys.exit(1)
    with open(path) as f:
        return json.load(f)
