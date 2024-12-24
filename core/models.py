from pathlib import Path
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.types import TypeDecorator, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from os import getenv
import json

from core.helpers import load_env_file

env_path = Path('.') / '.env'
load_env_file(env_path)

DATABASE_URL = f"{getenv("SQL_ENGINE")}{getenv("SQL_DATABASE")}.db"

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class JSONEncodedDict(TypeDecorator):
    """
    Преобразует dict в JSON для хранения в базе данных.
    """
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)  # Сериализация JSON

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)  # Десериализация JSON


# Определяем модель для базы данных
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    data_obj = Column(JSONEncodedDict, nullable=True) 


# Создание таблиц
Base.metadata.create_all(bind=engine)
