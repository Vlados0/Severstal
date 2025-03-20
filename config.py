import os
from configparser import ConfigParser
from typing import Dict


def get_db_config() -> Dict[str, str]:
    config = ConfigParser()
    config.read("config.ini")

    db_config = {
        "host": os.getenv("DB_HOST", config.get("database", "DB_HOST")),
        "database": os.getenv("DB_NAME", config.get("database", "DB_NAME")),
        "username": os.getenv("DB_USER", config.get("database", "DB_USER")),
        "password": os.getenv("DB_PASSWORD", config.get("database", "DB_PASSWORD")),
    }

    return db_config
