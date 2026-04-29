import os

from .settings import *  # noqa

_test_engine = os.environ.get("TEST_DB_ENGINE", "sqlite").strip().lower()
if _test_engine in ("postgres", "postgresql"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("TEST_DB_NAME", os.environ.get("DB_NAME", "medisync_test")),
            "HOST": os.environ.get("TEST_DB_HOST", os.environ.get("DB_HOST", "localhost")),
            "PORT": os.environ.get("TEST_DB_PORT", os.environ.get("DB_PORT", "5432")),
            "USER": os.environ.get("TEST_DB_USER", os.environ.get("DB_USER", "postgres")),
            "PASSWORD": os.environ.get("TEST_DB_PASSWORD", os.environ.get("DB_PASSWORD", "postgres")),
            "CONN_MAX_AGE": 0,
            "CONN_HEALTH_CHECKS": True,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
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
