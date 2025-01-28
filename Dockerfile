# Используем официальный образ Python
FROM python:3.12

# Обновляем apt-get и устанавливаем необходимые пакеты
RUN apt-get update && apt-get install -y \
    libreoffice \
    --fix-missing \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "alembic upgrade head"]

# Открываем порт для приложения
EXPOSE 8000
