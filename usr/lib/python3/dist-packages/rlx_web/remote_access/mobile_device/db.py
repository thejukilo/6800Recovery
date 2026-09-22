import functools

from typing import List, Optional, Dict

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from .constants import DEVICE_DB_PATH
from .exceptions import DuplicateMobileDeviceNameException, InvalidMobileDeviceException
from .models import Base, Device, Secret, DeviceUpdateData
from rlx_web.log import logger


def init_session() -> Session:
    """Initialize the sqlite session and create the database tables"""
    try:
        engine = create_engine(f"sqlite+pysqlite:///{DEVICE_DB_PATH}", echo=False)
        Base.metadata.create_all(engine, checkfirst=True)
        session_factory = sessionmaker(
            bind=engine, info=dict(description="Mobile Device Database", url=engine.url)
        )

    except OperationalError:
        logger.warning(
            "Could not connect to database file. Switching to non-persistent in-memory database."
        )
        engine = create_engine(
            "sqlite://",
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        Base.metadata.create_all(engine, checkfirst=True)
        session_factory = sessionmaker(
            bind=engine, info=dict(description="Mobile Device Database", url=engine.url)
        )
    return scoped_session(session_factory)


ScopedSession = init_session()


def session_wrapper_async(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        ScopedSession()

        try:
            return await func(*args, **kwargs)
        finally:
            ScopedSession.remove()

    return wrapper


def session_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ScopedSession()

        try:
            return func(*args, **kwargs)
        finally:
            ScopedSession.remove()

    return wrapper


def select_secret(kid: int) -> Optional[Secret]:
    """Returns a secret from database identified by kid. If no secret is found, returns None."""
    return ScopedSession.get(Secret, kid)


def insert_secret(secret: Secret) -> None:
    """Inserts a new secret into the database."""
    try:
        ScopedSession.add(secret)
        ScopedSession.commit()
    except SQLAlchemyError as e:
        logger.error(e)


def select_all_devices() -> List[Dict]:
    """Returns a list of all devices in the database. If no devices are found, returns empty list."""
    try:
        devices = ScopedSession.query(Device).all()
        return [d.asdict() for d in devices]
    except OSError as e:
        logger.warning(e)
    except ValidationError as e:
        logger.error(e)

    return []


def select_device(device_id: int) -> Optional[Device]:
    """Returns a device from database identified by device_id. If no device is found, returns None."""
    return ScopedSession.get(Device, device_id)


def insert_device(device: Device) -> None:
    """Inserts a new device into the database."""
    try:
        ScopedSession.add(device)
        ScopedSession.commit()
    except IntegrityError:
        raise DuplicateMobileDeviceNameException()
    except SQLAlchemyError as e:
        logger.error(e)
        raise InvalidMobileDeviceException(f"Unknown error: {e.code}")


def delete_device_by_id(device_id: int) -> bool:
    """
    Deletes a device identified by device_id from the database.
    Returns True if successful, False otherwise.
    """
    try:
        query = ScopedSession.query(Device).filter(Device.id == device_id)
        if not query.count():
            logger.info(f"No device with id {device_id} registered")
            return False

        query.delete(synchronize_session=False)
        ScopedSession.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error deleting device with id={device_id}")
        logger.error(e)

    return False


def update_device_by_id(device_id: int, data: DeviceUpdateData) -> bool:
    """
    Updates a device identified by device_id in the database.
    Returns True if successful, False otherwise.
    """
    try:
        query = ScopedSession.query(Device).filter(Device.id == device_id)
        if not query.count():
            logger.error(
                f"Error updating device. No device with id {device_id} registered"
            )
            return False

        query.update({Device.name: data.name}, synchronize_session=False)
        ScopedSession.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error updating device with id={device_id}")
        logger.error(e)

    return False


def update_granted_status_by_id(device_id: int, granted: bool) -> bool:
    """
    Updates the granted status of device identified by device_id in the database.
    Returns True if successful, False otherwise.
    """
    try:
        query = ScopedSession.query(Device).filter(Device.id == device_id)
        if not query.count():
            logger.error(
                f"Error updating grant access for device. No device with id {device_id} registered"
            )
            return False
        query.update({Device.granted: granted}, synchronize_session=False)
        ScopedSession.commit()
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error updating grant access for device with id={device_id}")
        logger.error(e)

    return False


def granted_status_by_id(device_id: int) -> bool:
    """Returns the granted status of device identified by device_id."""
    device = select_device(device_id)
    return device.granted if device is not None else False
