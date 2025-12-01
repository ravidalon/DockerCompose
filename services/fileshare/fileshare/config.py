import os
from pathlib import Path

UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))
DATABASE_URL: str = os.getenv("DATABASE_URL", "http://database:5000")
