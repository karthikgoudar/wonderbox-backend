from fastapi import APIRouter

router = APIRouter()


@router.post("/device/{id}/pause")
def pause_device(id: str):
    return {"status": "paused", "device": id}


@router.post("/device/{id}/set-limit")
def set_limit(id: str):
    return {"status": "limit set", "device": id}
