import os

# Set before the app is imported so cached settings pick these up.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_VERSION", "0.1.0-test")
os.environ.setdefault("POWERTOOLS_SERVICE_NAME", "athletiq")
