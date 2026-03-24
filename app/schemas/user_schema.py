from pydantic import BaseModel
from typing import Optional


class UserOut(BaseModel):
    id: int
    email: str
    name: Optional[str]

    class Config:
        orm_mode = True
