"""Configuration for file share service."""

import os
from pathlib import Path

# Upload directory for file storage
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))

# Database service URL
DATABASE_URL = os.getenv("DATABASE_URL", "http://database:5000")
