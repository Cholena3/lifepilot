"""Create all database tables from SQLAlchemy models.

Usage: python create_tables.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import get_settings
from app.core.database import Base, engine

# Import all models so they register with Base.metadata
import app.models  # noqa


async def create_all():
    settings = get_settings()
    print(f"Database URL: {settings.database_url}")
    print("Creating all tables...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("Done! All tables created.")


if __name__ == "__main__":
    asyncio.run(create_all())
