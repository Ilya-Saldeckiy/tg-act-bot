# Используем официальный образ Python
FROM python:3.12

# Обновляем apt-get и устанавливаем необходимые пакеты
RUN apt-get update -o Acquire::Retries=3 --allow-releaseinfo-change && \
    apt-get install -y --no-install-recommends libreoffice --fix-missing && \
    rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию в контейнере
WORKDIR /app

# Копируем файлы проекта в контейнер
COPY . /app

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Открываем порт для приложения
EXPOSE 8000
