import configparser

def load_config(file_path):
    cfg = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):  # skip comments
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    return cfg
