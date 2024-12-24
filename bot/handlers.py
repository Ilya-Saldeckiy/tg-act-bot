from aiogram import types, Router
from aiogram.types import ContentType
from pathlib import Path
import asyncio


async def create_act(user_id: int, user_data: dict, bot, dp):
    # Папка для сохранения фотографий
    PHOTOS_DIR = Path("photos")
    PHOTOS_DIR.mkdir(exist_ok=True)

    iteration_id = len(user_data.get(user_id, {})) + 1
    user_data.setdefault(user_id, {})
    user_data[user_id][iteration_id] = {"texts": [], "photos": []}

    task_done = asyncio.Event()
    router = Router()

    @router.message()
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

            await message.answer(
                f"Картинка сохранена! {f'Описание: {caption}' if caption else ''}"
            )

        elif message.content_type == ContentType.TEXT:
            user_data[user_id][iteration_id]["texts"].append(message.text)
            await message.answer("Текст сохранён!")

        if user_data[user_id][iteration_id]["photos"] or user_data[user_id][iteration_id]["texts"]:
            task_done.set()

    dp.include_router(router)

    try:
        await task_done.wait()

        if not user_data[user_id][iteration_id]["photos"] and not user_data[user_id][iteration_id]["texts"]:
            await bot.send_message(user_id, "Для создания акта необходимо загрузить хотя бы одно фото или написать текст.")
            return None

        print('user_data in def', user_data)
        return user_data

    finally:
        dp.sub_routers.remove(router)
