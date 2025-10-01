import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Resolve backend directory (this file is backend/app/db.py)
BACKEND_DIR = Path(__file__).resolve().parents[1]  # .../backend

# Ensure data directory exists under backend/data
DB_DIR = BACKEND_DIR / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)

# Default SQLite DB path under backend/data
default_sqlite_url = f"sqlite:///{(DB_DIR / 'floatchat.db').as_posix()}"

# Prefer DATABASE_URL from environment if provided
DATABASE_URL = os.getenv("DATABASE_URL", default_sqlite_url)

# Create SQLAlchemy engine with proper sqlite connect args
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Yield a database session and ensure it's closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
