import os, datetime
from turtle import title
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from pathlib import Path
from textwrap import wrap
from reportlab.lib import fonts
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from PIL import Image, ImageSequence


def load_env_file(file_path: str):
    if not file_path.is_file():
        print(f"Файл {file_path} не найден.")
        return
    
    with open(file_path, 'r') as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            key, value = line.split('=', 1)
            os.environ[key] = value
            
            
# def create_pdf_with_text_and_images():
