import os

class Settings:
    PROJECT_NAME = "WonderBox Backend"
    STORAGE_DIR = os.getenv("STORAGE_DIR", "./storage")
    DEFAULT_EXPIRY_DAYS = int(os.getenv("DEFAULT_EXPIRY_DAYS", "25"))


settings = Settings()
