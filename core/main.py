from fastapi import FastAPI, Depends
from typing import Union
from sqlalchemy import desc, exists
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.models import ItemDB, SessionLocal
from PIL import Image
from pathlib import Path
from textwrap import wrap
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from core.helpers import create_pdf_file, create_docx_file

import os

import datetime

app = FastAPI()


# Зависимость для получения сессии базы данных
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic-модель для валидации данных
class Item(BaseModel):
    id: int | None = None
    tg_id: int | None = None
    title: str | None = None
    description: str | None = None
    data_obj: dict | None = {}
    file_path: str | None = None
    
    class Config:
        orm_mode = True


@app.post("/create_act/", response_model=Item)
def create_act(item: Item, db: Session = Depends(get_db)):
    # Получаем последний ID или начинаем с 1
    last_item = db.query(ItemDB).order_by(ItemDB.id.desc()).first()
    act_id = (last_item.id if last_item else 0) + 1

    # Создаём объект SQLAlchemy
    db_item = ItemDB(
        id=act_id,
        tg_id=item.tg_id,
        title=item.title,
        description=item.description,
        data_obj=item.data_obj
    )

    # Сохраняем в базе данных
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    create_docx_file(item.tg_id, db)
    
    return db_item


@app.post("/update_docx_file/")
def update_docx_file_path(item: Item, db: Session = Depends(get_db)) -> None:
    
    db_item = ItemDB(
        id=item.id,
        file_path=item.file_path
    )
    
    db.query(ItemDB).filter(ItemDB.id == db_item.id).update({"file_path": db_item.file_path})
    db.commit()
    
    return {"file_path": db_item.file_path}


@app.get("/last_act_id/")
def last_act_id(db: Session = Depends(get_db)):
    last_record = db.query(ItemDB).order_by(desc(ItemDB.id)).first()
    return last_record.id if last_record else None
    

@app.get("/send_file/{act_id}")
def read_root(act_id: int, db: Session = Depends(get_db)):
    data_obj = db.query(ItemDB).filter(ItemDB.id == act_id).first()
    
    return {"file_path": data_obj.file_path}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
