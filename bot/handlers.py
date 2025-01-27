from aiogram.types import ContentType
from aiogram import types, Router
from aiogram.types import ContentType
from pathlib import Path
from aiogram.types import FSInputFile

from core.utils.logger import Log, LogLevels

import asyncio, os


async def create_act(user_id: int, user_data: dict, bot, dp):
    # Папка для сохранения фотографий
    PHOTOS_DIR = Path("photos")
    PHOTOS_DIR.mkdir(exist_ok=True)

    if user_id not in user_data:
        user_data[user_id] = {}

    iteration_id = len(user_data.get(user_id, {})) + 1
    user_data[user_id][iteration_id] = {"texts": [], "photos": []}

    task_done = asyncio.Event()
    router = Router()

    @router.message(lambda message: message.from_user.id == user_id)
    async def handle_message(message: types.Message):
        if message.content_type == ContentType.PHOTO:
            photo = message.photo[-1]
            file = await bot.get_file(photo.file_id)

            file_name = f"{file.file_id}.jpg"
            file_path = PHOTOS_DIR / file_name
            await bot.download_file(file.file_path, destination=file_path)

            caption = message.caption
            if caption:
                user_data[user_id][iteration_id]["texts"].append(caption)

            user_data[user_id][iteration_id]["photos"].append(str(file_path))

        elif message.content_type == ContentType.TEXT:
            user_data[user_id][iteration_id]["texts"].append(message.text)

        if user_data[user_id][iteration_id]["photos"] or user_data[user_id][iteration_id]["texts"]:
            task_done.set()

    dp.include_router(router)

    try:
        await task_done.wait()
        return user_data
    finally:
        dp.sub_routers.remove(router)
        

async def set_title_act(user_id: int, bot, dp):
    
    task_done = asyncio.Event()
    router = Router()
    title_act = None
    
    @router.message()
    async def handle_message(message: types.Message):
        nonlocal title_act
        
        if message.content_type == ContentType.TEXT and len(message.text) > 1:
            title_act = message.text
            task_done.set()
        else:
            await bot.send_message(user_id, "Для окончания сохранения нужно написать корректное название.")

    dp.include_router(router)

    try:
        await task_done.wait()
        return str(title_act)

    finally:
        dp.sub_routers.remove(router)
        
        
async def send_file(callback_query: types.CallbackQuery, file_path: str, menu: bool = True):
    """
    Отправляет файл в ответ на callback-запрос.

    :param callback_query: Объект callback-запроса.
    :param file_path: Путь к файлу.
    """
    try:
        # Проверяем существование файла
        if not os.path.exists(file_path):
            await callback_query.message.answer("Файл не найден. Попробуйте позже.")
            return

        # Создаем InputFile из пути к файлу
        input_file = FSInputFile(file_path)
        
        # Отправляем файл
        await callback_query.message.answer_document(
            document=input_file,
            caption="Вот ваш файл!"
        )

    except FileNotFoundError:
        await callback_query.message.answer("Файл не найден. Попробуйте позже.")
    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {e}")
        Log(f"Произошла ошибка: {e}", "handlers", LogLevels.ERROR)
    
        
async def change_file(user_id: int, bot, dp):
    # Папка для сохранения фотографий
    ACTS_DIR = Path("acts")

    task_done = asyncio.Event()
    router = Router()
    
    file_path = None

    @router.message(lambda message: message.from_user.id == user_id)
    async def handle_message(message: types.Message):
        nonlocal file_path
                
        if message.content_type == ContentType.DOCUMENT:
            document = message.document
                        
            file = await bot.get_file(document.file_id)

            file_name = f"{document.file_name}"
            file_path = str(ACTS_DIR / file_name)
                        
            await bot.download_file(file.file_path, destination=file_path)

        if file_path and os.path.exists(file_path):
            task_done.set()

    dp.include_router(router)

    try:
        await task_done.wait()
        return file_path

    finally:
        dp.sub_routers.remove(router)
