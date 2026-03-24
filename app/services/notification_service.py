from app.models.notification import Notification

def send_sticker_created(db, sticker, message: str):
    # Minimal: store notification for now
    notif = Notification(user_id=None, message=message)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif
