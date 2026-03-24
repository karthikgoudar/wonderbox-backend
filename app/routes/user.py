from fastapi import APIRouter

router = APIRouter()


@router.get("/stickers")
def list_stickers():
    # Placeholder for parent app listing
    return {"stickers": []}
