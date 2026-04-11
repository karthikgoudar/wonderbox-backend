from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.analytics_event import AnalyticsEvent


def track_event(
    db: Session,
    event_type: str,
    user_id: Optional[int] = None,
    device_id: Optional[int] = None,
    properties: Optional[Dict[str, Any]] = None,
) -> AnalyticsEvent:
    event = AnalyticsEvent(
        event_type=event_type,
        user_id=user_id,
        device_id=device_id,
        properties=properties or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
