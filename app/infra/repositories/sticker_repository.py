from app.models.sticker import Sticker


def create_sticker(db, sticker_data: dict):
    sticker = Sticker(**sticker_data)
    db.add(sticker)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(sticker)
    return sticker


def get_by_id(db, sticker_id: int):
    return db.query(Sticker).filter(Sticker.id == sticker_id).first()


def update(db, sticker, updates: dict):
    for key, value in updates.items():
        setattr(sticker, key, value)
    db.commit()
    db.refresh(sticker)
    return sticker
