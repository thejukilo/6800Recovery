from pathlib import Path

DEVICE_DB_PATH = Path("/opt/roche/var/lib/mobile-device/web-external-device.sqlite")
CONFIG_PATH = Path("/opt/roche/var/lib/mobile-device/config.json")
JWT_ALGORITHM = "HS256"

# Default lifetime of 30 days
DEFAULT_DEVICE_TOKEN_LIFETIME = 30
# Default lifetime of 5 minutes
DEFAULT_REGISTRATION_TOKEN_LIFETIME = 5

AUTH_TOKEN_KEY = "mobile_device_auth_token"
