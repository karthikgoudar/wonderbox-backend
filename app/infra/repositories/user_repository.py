from app.models.user import User


def get_by_id(db, user_id: str):
    return db.query(User).filter(User.id == user_id).first()


def get_by_email(db, email: str):
    return db.query(User).filter(User.email == email).first()


def create(db, user_data: dict):
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update(db, user, updates: dict):
    for key, value in updates.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user
