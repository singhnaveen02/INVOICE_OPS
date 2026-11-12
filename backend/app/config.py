from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./invoiceops.db"
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf"]
    PRICE_TOLERANCE_PERCENT: float = 2.0
    QUANTITY_TOLERANCE_PERCENT: float = 1.0
    FUZZY_MATCH_THRESHOLD: int = 80
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    USE_BEDROCK: bool = False
    SECRET_KEY: str = "change-me-in-production"

    class Config:
        env_file = ".env"


settings = Settings()
