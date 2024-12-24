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
    name: str | None = None
    description: str | None = None
    data_obj: dict | None = {}
    
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
        name=item.name,
        description=item.description,
        data_obj=item.data_obj
    )

    # Сохраняем в базе данных
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/last_act_id/")
def last_act_id(db: Session = Depends(get_db)):
    last_record = db.query(ItemDB).order_by(desc(ItemDB.id)).first()
    return last_record.id if last_record else None
    

@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/create_pdf/{user_id}")
def create_pdf_file(user_id: int, db: Session = Depends(get_db)):
    text_data = [
        "first",
        "second",
        "Three",
        "Four"
    ]

    images = [
        "photos/AgACAgIAAxkBAAICyWdpTg3ZA-Z6MnLi-pQOMIyfVyKrAAKn6jEbh_BIS2VS5xeob6cAAQEAAwIAA20AAzYE.jpg",  # Убедитесь, что путь к изображениям правильный
        "photos/AgACAgIAAxkBAAICyWdpTg3ZA-Z6MnLi-pQOMIyfVyKrAAKn6jEbh_BIS2VS5xeob6cAAQEAAwIAA20AAzYE.jpg"
    ]
    
    def hex_to_rgb(hex_color):
        """Конвертирует цвет в формате #RRGGBB в значения RGB (от 0 до 1)."""
        hex_color = hex_color.lstrip('#')  # Убираем символ #
        return tuple(int(hex_color[i:i+2], 16) / 255 for i in (0, 2, 4))
    
    data_obj = db.query(ItemDB).filter(ItemDB.name == user_id).all()
    
    if data_obj:
        data = data_obj[-1]
        
    title = f"АКТ № 1607АЛ{data.id if data.id >= 10 else "0" + data.id} выявленных недостатков, дефектов и несоответствий работ"
    
    # Регистрация шрифтов
    pdfmetrics.registerFont(TTFont('Carlito', './core/fonts/Carlito-Regular.ttf'))
    pdfmetrics.registerFont(TTFont('CarlitoBold', './core/fonts/Carlito-Bold.ttf'))
    
    filename = "output.pdf"
    
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime("%m/%d/%Y")
    current_time = current_datetime.strftime("%H:%M")
    
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    # Устанавливаем шрифт
    font_name = "Carlito"
    font_size = 12
    margin = 20
    line_height = font_size + 4
    text_y_position = height - 30
    text_x_position = margin
    
    c.setFont("Carlito", 26)
    
    max_text_width = width - 2 * margin
    char_width = c.stringWidth("A", "Carlito", 26)
    wrapped_title = wrap(title, width=int(max_text_width / char_width))
    
    # if text_y_position < margin:  # Если текст достигает нижнего края страницы
    #     c.showPage()  # Создаем новую страницу
    #     c.setFont()  # Переустанавливаем шрифт
    #     text_y_position = height - margin  # Сбрасываем позицию Y

    for line in wrapped_title:
        c.drawString(text_x_position, text_y_position, line)
        text_y_position -= 30
        
    c.setFont("Carlito", 13)
    background_rgb = hex_to_rgb("#9E9E9E")
    c.setFillColorRGB(*background_rgb)
    
    c.drawString(text_x_position, text_y_position, current_date)
    text_x_position_time = c.stringWidth(current_date) + 50
    
    c.drawString(text_x_position_time, text_y_position, current_time)

    # Ставим настройки текста для оставшегося отчёта
    c.setFont("Carlito", 13)
    background_rgb = hex_to_rgb("#000000")
    c.setFillColorRGB(*background_rgb)
    
    text_y_position -= 120
    
    # c.drawString(text_x_position, text_y_position, "test test")
        
    for item_id, item in data.data_obj.items():
        counter = item_id
        has_counter = False
        print('counter', counter)
        
        for text in item.get("texts"):
            
            if text_y_position < 30:
                c.showPage()
                text_y_position = height - 30
            
            c.drawString(text_x_position, text_y_position, f"{counter}. {text}")
            has_counter = True
            text_y_position -= 30
            
        for photo in item.get("photos"):
            if Path(photo).exists():
            
                with Image.open(photo) as image:
                    width, height = image.size

                if width > 380:
                    width = 380
                elif height > 500:
                    height = 500
                    
                text_y_position = text_y_position - height

                if text_y_position < 30:
                    c.showPage()  # Создаем новую страницу, если не хватает места
                    text_y_position = height - 30  # Сброс позиции
                
                if not has_counter:
                    has_counter = True
                    c.drawString(text_x_position, text_y_position, counter)
                    text_y_position -= 15

                c.drawImage(photo, text_x_position, text_y_position, width=width, height=height)  # Размер и позиция изображения
                text_y_position -= 40  # Смещение вниз после добавления изображения
    
    print('last_item', data.data_obj)
    
    # for img_path in images:
    #     if Path(img_path).exists():
            
    #         with Image.open(img_path) as image:
    #             width, height = image.size

    #         if width > 380:
    #             width = 380
    #         elif height > 500:
    #             height = 500
                
    #         text_y_position = text_y_position - height

    #         c.drawImage(img_path, text_x_position, text_y_position, width=width, height=height)  # Размер и позиция изображения
    #         text_y_position -= 40  # Смещение вниз после добавления изображения

    #         if text_y_position < 30:
    #             c.showPage()  # Создаем новую страницу, если не хватает места
    #             text_y_position = height - 30  # Сброс позиции

    # Сохранение PDF
    return c.save()


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}
