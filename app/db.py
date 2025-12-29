import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# اگر DATABASE_URL ست شده باشد از آن استفاده می‌کنیم، وگرنه همین پیش‌فرض
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://kataeinnorabadi@localhost:5432/relay",
)

engine = create_engine(DATABASE_URL, future=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
