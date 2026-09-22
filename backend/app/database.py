import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


_postgres_dll_directory = None

if os.name == "nt":
    postgres_bin = Path(
        "C:/Program Files/PostgreSQL/18/bin"
    )

    if postgres_bin.exists():
        os.environ["PATH"] = (
            f"{postgres_bin}{os.pathsep}{os.environ['PATH']}"
        )
        _postgres_dll_directory = os.add_dll_directory(
            str(postgres_bin)
        )


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_db():
    with SessionLocal() as session:
        yield session
