from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# Створення SQLAlchemy-двигуна (engine)
engine = create_engine(DATABASE_URL, echo=False)

# Сесія для виконання запитів
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовий клас для моделей
Base = declarative_base() 
