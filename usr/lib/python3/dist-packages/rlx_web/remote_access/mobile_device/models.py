from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, backref

Base = declarative_base()


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True)
    name = Column(String(length=20), default="", unique=True)
    ip = Column(String(length=15), default="")
    registration_date = Column(DateTime(), default=datetime.now())
    valid_until = Column(DateTime(), default=None)
    otp = Column(String())
    granted = Column(Boolean, default=False)

    def __repr__(self):
        return f"Device(id={self.id}, name={self.name}, ip={self.ip}, granted={self.granted})"

    def asdict(self) -> dict[str, Union[str, int]]:
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "registration_date": self.registration_date.isoformat(),
            "valid_until": self.valid_until.isoformat(),
            "otp": self.otp,
            "granted": self.granted,
        }


class Secret(Base):
    __tablename__ = "secrets"

    id = Column(Integer, primary_key=True)
    value = Column(String())
    device_id = Column(
        Integer(), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    device = relationship("Device", backref=backref("secrets", passive_deletes=True))

    def __repr__(self):
        return f"Secret(id={self.id}, value=*****)"


class DeviceConfig(BaseModel):
    id: int
    name: str
    ip: Optional[str]


class DeviceRegistrationRequest(BaseModel):
    token: str
    name: str = ""


class DeviceDeleteRequest(BaseModel):
    id: int


class DeviceUpdateParams(BaseModel):
    id: int


class DeviceUpdateData(BaseModel):
    name: str
