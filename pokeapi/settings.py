"""Single-container, snapshot-backed PokéAPI for the local demo."""

from .settings import *

DEBUG = False
ALLOWED_HOSTS = ["*"]
ROOT_URLCONF = "config.demo_urls"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "pokeapi-demo",
    }
}
