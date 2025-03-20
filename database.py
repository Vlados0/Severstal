from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import get_db_config

db_config = get_db_config()
SQLALCHEMY_DATABASE_URL = f"postgresql://{db_config['username']}:{db_config['password']}@{db_config['host']}/{db_config['database']}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
