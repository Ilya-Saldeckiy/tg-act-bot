import sys, aiohttp
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from handlers import create_act, set_title_act, send_file, change_file
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import ContentType
from pathlib import Path
from os import getenv
from core.helpers import load_env_file

# Загружаем .env
env_path = Path('.') / '.env'
load_env_file(env_path)

# Создаем бота
bot = Bot(token=getenv("TELEGRAM_TOKEN"))
dp = Dispatcher()

# Словарь для хранения данных пользователей
user_data = {}
user_act_data = {}
callback_state = False
act_id = {}

print("BOT запущен")

# Создаём кнопки
button1 = types.InlineKeyboardButton(text="Создать АКТ", callback_data="create_act")
button2 = types.InlineKeyboardButton(text="Кнопка №2", callback_data="button2")
button_send_file = types.InlineKeyboardButton(text="Скачать АКТ", callback_data="send_file")
go_to_start = types.InlineKeyboardButton(text="Вернуться в главное меню", callback_data="go_to_start")

# Создаём клавиатуру
keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button1, button2]])
keyboard_saved = types.InlineKeyboardMarkup(inline_keyboard=[[button_send_file, go_to_start]])


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer("Выбери действие", reply_markup=keyboard)

button_create_act_continue = types.InlineKeyboardButton(text="Добавить элемент в акт?", callback_data="create_act_continue")
button_save_create_act = types.InlineKeyboardButton(text="Сохранить АКТ", callback_data="button_save_create_act")
button_upload_changed_act = types.InlineKeyboardButton(text="Заменить АКТ", callback_data="upload_changed_act")

keyboard_create_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_create_act_continue, button_save_create_act]])
keyboard_upload_changed_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_upload_changed_act, go_to_start]])


# Обработчик текстов
# @dp.message(F.text)
# async def handle_unexpected_text(message: types.Message):
#     user_id = message.from_user.id
    
#     if callback_state:
    
#         if user_data.get(user_id):
#             keyboard_state = keyboard_create_act
#         else:
#             keyboard_state = keyboard
            
#         await message.answer("Пожалуйста, используйте кнопки для взаимодействия.", reply_markup=keyboard_state)


# Обработка нажатий на кнопки
@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if callback_query.data == "go_to_start":
        user_data[user_id] = {}
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        await callback_query.message.answer("Выбери действие", reply_markup=keyboard)
        
    elif callback_query.data == "create_act":
        
        user_data[user_id] = {}
        
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        await callback_query.message.answer("Для создания акта напишите описание и прикрепите фотографии")
        
        result = await create_act(user_id, user_data, bot, dp)
        
        if result is None:
            # @TODO Добавить возможность заново загрузить данные
            await callback_query.message.answer("Пожалуйста, добавьте хотя бы один текст или фотографию.", reply_markup=keyboard)
            return

        await callback_query.message.answer("Выбери действие", reply_markup=keyboard_create_act)

    elif callback_query.data == "button2":
        await callback_query.message.answer("Выберите следующее действие", reply_markup=keyboard)
        
    elif callback_query.data == "create_act_continue":
        
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        await callback_query.message.answer("Продолжаем создание акта!")
        
        result = await create_act(user_id, user_data, bot, dp)
        
        if result is None:
            await callback_query.message.answer("Пожалуйста, добавьте хотя бы один текст или фотографию.", reply_markup=keyboard)
            return

        await callback_query.message.answer("Выбери действие", reply_markup=keyboard_create_act)
        
    elif callback_query.data == "button_save_create_act":
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        await callback_query.message.answer("Введите название акта")
        
        title = await set_title_act(user_id, bot, dp)
        
        if title:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{getenv("URL")}/create_act/",
                        json={
                            "tg_id": str(user_id),
                            "title": str(title),
                            "data_obj": user_data.get(user_id, {})
                        }
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            await callback_query.message.answer(
                                "Акт успешно сохранён.\nВыберите следующее действие",
                                reply_markup=keyboard_saved
                            )
                            user_data[user_id] = {}
                            
                            user_act_data[user_id] = response_data
                            
                            print('repsonse', response_data)
                            
                            act_id["id"] = response_data.get('id', None)
                            
                            return response_data
                        else:
                            await callback_query.message.answer("Возникла ошибка, сохранение не удалось")
                            return False
                except aiohttp.ClientError as e:
                    await callback_query.message.answer(f"Ошибка сети: {e}")
                    return False
    elif callback_query.data == "send_file":
        
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        act_data = user_act_data.get(user_id)
        
        if act_data:
            file_path = act_data.get("file_path")
            
            if file_path:
                await send_file(callback_query, file_path)
                
                await callback_query.message.answer("Выбери действие", reply_markup=keyboard_upload_changed_act)
                
    elif callback_query.data == "upload_changed_act":
        await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
        await callback_query.message.answer("Загрузите изменённый АКТ")
        new_file_path = await change_file(bot, dp)
        
        if new_file_path:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{getenv("URL")}/update_docx_file/",
                        json={
                            "id": act_id.get("id", None),
                            "file_path": str(new_file_path)
                        }
                    ) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            await callback_query.message.answer(
                                "Изменённый АКТ сохранён.\nВыберите следующее действие",
                                reply_markup=keyboard_upload_changed_act
                            )
                            
                            return response_data
                        else:
                            await callback_query.message.answer("Возникла ошибка, сохранение не удалось")
                            return False
                except aiohttp.ClientError as e:
                    await callback_query.message.answer(f"Ошибка сети: {e}")
                    return False
        
    await callback_query.answer()


# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
