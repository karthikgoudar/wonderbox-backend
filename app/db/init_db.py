from app.db.session import engine
from app.db.base import Base

def init_db():
    # Import models so they are registered on the metadata
    import app.models.user
    import app.models.child
    import app.models.device
    import app.models.sticker
    import app.models.usage
    import app.models.subscription
    import app.models.notification

    Base.metadata.create_all(bind=engine)
