import os

from .settings import *  # noqa

TEST_DB_NAME = (os.environ.get("TEST_DB_NAME") or os.environ.get("DB_NAME") or "").strip()
TEST_DB_HOST = (os.environ.get("TEST_DB_HOST") or os.environ.get("DB_HOST") or "").strip()
TEST_DB_PORT = (os.environ.get("TEST_DB_PORT") or os.environ.get("DB_PORT") or "5432").strip()
TEST_DB_USER = (os.environ.get("TEST_DB_USER") or os.environ.get("DB_USER") or "").strip()
TEST_DB_PASSWORD = (os.environ.get("TEST_DB_PASSWORD") or os.environ.get("DB_PASSWORD") or "").strip()

missing = [
    k
    for k, v in {
        "TEST_DB_NAME": TEST_DB_NAME,
        "TEST_DB_HOST": TEST_DB_HOST,
        "TEST_DB_PORT": TEST_DB_PORT,
        "TEST_DB_USER": TEST_DB_USER,
        "TEST_DB_PASSWORD": TEST_DB_PASSWORD,
    }.items()
    if not v
]
if missing:
    raise RuntimeError(f"Missing required PostgreSQL test settings: {', '.join(missing)}")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": TEST_DB_NAME,
        "HOST": TEST_DB_HOST,
        "PORT": TEST_DB_PORT,
        "USER": TEST_DB_USER,
        "PASSWORD": TEST_DB_PASSWORD,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": True,
    }
}

# Speed up tests: disable password validators, channels layers, etc. as needed
AUTH_PASSWORD_VALIDATORS = []

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

CHANNEL_LAYERS = {
    "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"},
}
