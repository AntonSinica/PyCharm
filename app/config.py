import json

class Config:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, "r") as f:
            self._config = json.load(f)

    @property
    def telegram_token(self):
        return self._config["telegram"]["token"]

    @property
    def db_password(self):
        return self._config["db"]["password"]
