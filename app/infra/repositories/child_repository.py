from app.models.child import Child


def get_by_id(db, child_id: str):
    return db.query(Child).filter(Child.id == child_id).first()


def create(db, child_data: dict):
    child = Child(**child_data)
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


def update(db, child, updates: dict):
    for key, value in updates.items():
        setattr(child, key, value)
    db.commit()
    db.refresh(child)
    return child
