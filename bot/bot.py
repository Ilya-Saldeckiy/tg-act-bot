import sys, aiohttp
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from handlers import create_act
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

print("BOT запущен")

# Создаём кнопки
button1 = types.InlineKeyboardButton(text="Создать АКТ", callback_data="create_act")
button2 = types.InlineKeyboardButton(text="Кнопка №2", callback_data="button2")

# Создаём клавиатуру
keyboard = types.InlineKeyboardMarkup(inline_keyboard=[[button1, button2]])


@dp.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.answer("Выбери действие", reply_markup=keyboard)

button_create_act_continue = types.InlineKeyboardButton(text="Добавить элемент в акт?", callback_data="create_act_continue")
button_save_create_act = types.InlineKeyboardButton(text="Сохранить АКТ", callback_data="button_save_create_act")

keyboard_create_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_create_act_continue, button_save_create_act]])


# Обработчик текстов
@dp.message(F.text)
async def handle_unexpected_text(message: types.Message):
    user_id = message.from_user.id
    
    if user_data.get(user_id):
        keyboard_state = keyboard_create_act
    else:
        keyboard_state = keyboard
        
    await message.answer("Пожалуйста, используйте кнопки для взаимодействия.", reply_markup=keyboard_state)


# Обработка нажатий на кнопки
@dp.callback_query()
async def handle_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    
    print('callback_query', callback_query)
    print('callback_query.data', callback_query.data)

    if callback_query.data == "create_act":
        
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
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{getenv("URL")}/create_act/",
                    json={
                        "name": str(user_id),
                        "description": "This is a test description",
                        "data_obj": user_data.get(user_id, {})
                    }
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        await callback_query.message.edit_text(
                            "Акт успешно сохранён.\nВыберите следующее действие",
                            reply_markup=keyboard
                        )
                        user_data[user_id] = {}
                        return response_data
                    else:
                        await callback_query.message.answer("Возникла ошибка, сохранение не удалось")
                        return False
            except aiohttp.ClientError as e:
                await callback_query.message.answer(f"Ошибка сети: {e}")
                return False
    elif not callback_query.data:
        await callback_query.message.answer("Нужно выбрать действие!")

    await callback_query.answer()
    
    print("last user_data", user_data)
    

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
