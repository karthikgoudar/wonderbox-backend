from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StickerOut(BaseModel):
    id: int
    original_text: Optional[str]
    normalized_prompt: Optional[str]
    language: Optional[str]
    image_url: Optional[str]
    is_favorited: bool
    expires_at: Optional[datetime]

    class Config:
        orm_mode = True
