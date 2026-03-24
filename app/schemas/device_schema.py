from pydantic import BaseModel


class DeviceIn(BaseModel):
    device_id: str
