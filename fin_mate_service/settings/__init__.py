import os

env = os.getenv("DJANGO_ENV", "development").lower()

if env == "production":
    from .production import *
else:
    from .development import *
