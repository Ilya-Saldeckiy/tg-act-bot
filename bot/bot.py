import sys, aiohttp
from turtle import st
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from handlers import create_act, set_info_for_act, send_file, change_file
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from pathlib import Path
from os import getenv
from core.helpers import load_env_file

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from aiogram.types.callback_query import CallbackQuery

from core.utils.logger import Log, LogLevels

import re, os, math

# Загружаем .env
env_path = Path(".") / ".env"
load_env_file(env_path)

# Создаем бота
storage = MemoryStorage()
bot = Bot(token=getenv("TELEGRAM_TOKEN"))
dp = Dispatcher(storage=storage)

# Словарь для хранения данных пользователей
user_data = {}
user_act_data = {}
callback_state = False
act_id_storage = {}
page_index = 0
send_file_menu = {"status": True}

print("BOT запущен")

# Создаём кнопки
button1 = types.InlineKeyboardButton(text="Создать АКТ", callback_data="create_act")
button2 = types.InlineKeyboardButton(text="Хранилище актов", callback_data="storage_acts:0")
button_send_file = types.InlineKeyboardButton(text="Скачать АКТ в DOCX", callback_data="send_file:docx")
button_send_file_pdf = types.InlineKeyboardButton(text="Скачать АКТ в PDF", callback_data="send_file:pdf")
go_to_start = types.InlineKeyboardButton(text="Вернуться в меню", callback_data="go_to_start")
cancel_create = types.InlineKeyboardButton(text="Отменить создание", callback_data="go_to_start")

button_create_act_continue = types.InlineKeyboardButton(text="Добавить элемент в акт?", callback_data="create_act_continue")
button_save_create_act = types.InlineKeyboardButton(text="Сохранить АКТ", callback_data="button_save_create_act")
button_upload_changed_act = types.InlineKeyboardButton(text="Заменить АКТ", callback_data="upload_changed_act")

keyboard_main = types.InlineKeyboardMarkup(inline_keyboard=[[button1, button2]])
keyboard_saved = types.InlineKeyboardMarkup(inline_keyboard=[[button_send_file, go_to_start]])
keyboard_create_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_create_act_continue, button_save_create_act]])
keyboard_upload_changed_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_upload_changed_act, go_to_start]])
keyboard_create_act = types.InlineKeyboardMarkup(inline_keyboard=[[button_create_act_continue, button_save_create_act], [cancel_create]])


def create_storage_keyboard(item_id, act_name, page):
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                button_upload_changed_act,
                types.InlineKeyboardButton(text="Удалить АКТ", callback_data=f"delete_act:{item_id}:{act_name}"),
            ],
            [button_send_file, button_send_file_pdf],
            [
                types.InlineKeyboardButton(text="Вернуться в хранилище", callback_data=f"storage_acts:{page}"),
                types.InlineKeyboardButton(text="Вернуться в меню", callback_data="go_to_start"),
            ],
        ]
    )


FIO_PATTERN = r"^[А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+$"


class UserStates(StatesGroup):
    waiting_for_full_name = State()


async def fetch_data(endpoint):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{getenv("URL")}/{endpoint}") as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                print(f"Ошибка: {response.status}")
                Log(f"Ошибка: {response.status}", "bot", LogLevels.ERROR)
                return None


async def validate_full_name(full_name: str) -> bool:
    return re.match(FIO_PATTERN, full_name) is not None


async def create_user_in_db(user_id: int, full_name: str) -> dict | None:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{os.getenv('URL')}/create_user/",
            json={"tg_id": user_id, "full_name": full_name},
        ) as response:
            if response.status == 200:
                return await response.json()
            return None


@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user = await fetch_data(f"check_user/{user_id}")

    print(f"[DEBUG] user from fetch_data: {user}")

    if not user:
        await message.answer("Представьтесь. Напишите своё ФИО.")
        await state.set_state(UserStates.waiting_for_full_name)
    else:
        await message.answer("Выберите действие", reply_markup=keyboard_main)


@dp.message(UserStates.waiting_for_full_name)
async def process_full_name(message: types.Message, state: FSMContext):
    full_name = message.text.strip()

    if await validate_full_name(full_name):
        user_id = message.from_user.id
        user = await create_user_in_db(user_id, full_name)

        if user:
            await message.answer("ФИО успешно сохранено!")
            await state.clear()
            await message.answer("Выберите действие", reply_markup=keyboard_main)
        else:
            await message.answer("Ошибка при сохранении. Попробуйте ещё раз.")
    else:
        await message.answer("Некорректное ФИО. Убедитесь, что оно состоит из трёх слов и каждое начинается с заглавной буквы.")


class PaginationCallback(CallbackData, prefix="pagination"):
    page: int


# Функция для обрезки строки
def truncate_string(s: str, max_length: int = 60) -> str:
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s


# Функция для формирования клавиатуры
def get_pagination_keyboard(page: int, ITEMS_PER_PAGE: int, items: list, max_pages_display: int = 2) -> types.InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    # Определяем общее количество страниц
    total_items = len(items)
    total_pages = math.ceil(total_items / ITEMS_PER_PAGE)  # Округление вверх

    # Определяем диапазон элементов для текущей страницы
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_items = items[start:end]

    # Добавляем кнопки с элементами
    for item in current_items:
        item_id = item.get("id", None)
        file_path = item.get("file_path", None)

        if file_path:
            file_name = file_path.replace("acts/", "")
            button_name = truncate_string(f"{item_id}. {file_name}", 30)
            builder.row(types.InlineKeyboardButton(text=button_name, callback_data=str(f"item:{item_id}:{button_name}")))

    # Добавляем кнопки для номеров страниц
    pagination_row = []

    if total_pages <= max_pages_display + 2:
        start_page = 1
        end_page = total_pages
    elif page >= total_pages - 1:
        start_page = max(1, total_pages - 3)
        end_page = total_pages
    else:
        start_page = max(1, page)
        end_page = min(total_pages, start_page + max_pages_display)

    # Добавляем первую страницу, если нужно
    if start_page > 1:
        pagination_row.append(types.InlineKeyboardButton(text="1", callback_data=PaginationCallback(page=0).pack()))

    # Добавляем диапазон страниц
    for p in range(start_page, end_page + 1):
        if p == page + 1:
            pagination_row.append(types.InlineKeyboardButton(text=f"[{p}]", callback_data="ignore"))
        else:
            pagination_row.append(types.InlineKeyboardButton(text=str(p), callback_data=PaginationCallback(page=p - 1).pack()))

    # Добавляем последнюю страницу, если нужно
    if end_page < total_pages:
        pagination_row.append(
            types.InlineKeyboardButton(text=str(total_pages), callback_data=PaginationCallback(page=int(total_pages - 1)).pack())
        )

    builder.row(*pagination_row)

    navigation_row = []
    if page > 0:
        navigation_row.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=PaginationCallback(page=page - 1).pack()))
    if end < total_items:
        navigation_row.append(types.InlineKeyboardButton(text="Вперед ➡️", callback_data=PaginationCallback(page=page + 1).pack()))

    if navigation_row:
        builder.row(*navigation_row)

    # Добавляем кнопку "Вернуться в меню"
    builder.button(text="Вернуться в меню", callback_data="go_to_start")

    return builder.as_markup()


# Обработчик callback'ов для пагинации
@dp.callback_query(PaginationCallback.filter())
async def pagination_handler(callback: CallbackQuery, callback_data: PaginationCallback):
    storage_acts = await fetch_data("all-acts/")

    page = callback_data.page

    keyboard = get_pagination_keyboard(page, 5, storage_acts)
    await callback.message.edit_text("Выберите элемент:", reply_markup=keyboard)


# Обработчик выбранного элемента
@dp.callback_query(lambda call: call.data.startswith("item:"))
async def item_handler(callback_query: types.CallbackQuery):
    _, item_id, item_name = callback_query.data.split(":")
    await callback_query.message.delete()

    page = int(item_id) // 5 - 1 if int(item_id) % 5 == 0 else int(item_id) // 5
    act_id_storage["id"] = item_id
    send_file_menu["status"] = False

    short_item_name = truncate_string(item_name, 25)

    storage_keyboard = create_storage_keyboard(item_id, short_item_name, page)

    await callback_query.message.answer(f"Вы выбрали: {item_name}\nЧто нужно сделать?", reply_markup=storage_keyboard)


@dp.callback_query(lambda call: call.data.startswith("delete_act:"))
async def delete_act_handler(callback_query: types.CallbackQuery):
    _, act_id, act_name = callback_query.data.split(":")
    page = (
        (int(act_id) // 5) - 1 if int(act_id) >= 5 and (str(int(act_id) / 5).endswith(".2") or int(act_id) % 5 == 0) else int(act_id) // 5
    )

    async with aiohttp.ClientSession() as session:
        async with session.delete(f"{getenv('URL')}/delete-act/{act_id}") as response:
            if response.status == 200:
                storage_acts = await fetch_data("all-acts/")
                keyboard = get_pagination_keyboard(page, 5, storage_acts)

                await callback_query.message.delete()
                await callback_query.message.answer(f"Акт {act_name} успешно удален.", reply_markup=keyboard)
            else:
                await callback_query.message.answer(f"Ошибка при удалении: {response.status}")

    await callback_query.answer()


async def process_go_to_start(message: types.Message, custom_menu: list = None):
    user_id = message.from_user.id
    user_data[user_id] = {}

    if custom_menu:
        keyboard_custom = types.InlineKeyboardMarkup(inline_keyboard=custom_menu)
    else:
        keyboard_custom = keyboard_main

    await message.answer("Выбери действие", reply_markup=keyboard_custom)


@dp.callback_query(lambda c: c.data == "go_to_start")
async def callback_go_to_start(callback_query: types.CallbackQuery):
    await callback_query.message.delete()
    await process_go_to_start(callback_query.message)


@dp.callback_query(lambda c: c.data == "create_act")
async def callback_create_act(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    user_data[user_id] = {}

    await callback_query.message.edit_text(callback_query.message.text, reply_markup=None)
    await callback_query.message.answer("Для создания акта нужно: Прикрепить картинку и написать текст или просто написать текст")

    await create_act(user_id, user_data, bot, dp)

    await callback_query.message.answer("Выбери действие", reply_markup=keyboard_create_act)


@dp.callback_query(lambda c: c.data.startswith("storage_acts"))
async def callback_storage_acts(callback_query: types.CallbackQuery):
    _, page_number = callback_query.data.split(":")

    page_number = page_index if not page_number else page_number
    await callback_query.message.delete()
    storage_acts = await fetch_data("all-acts/")

    keyboard = get_pagination_keyboard(int(page_number), 5, storage_acts)

    if keyboard:
        await callback_query.message.answer("Выберите АКТ для работы с ним:", reply_markup=keyboard)
    else:
        await callback_query.message.answer("Хранилище пустое, нужно добавить акт.")
        await process_go_to_start(callback_query.message)


@dp.callback_query(lambda c: c.data == "create_act_continue")
async def callback_create_act_continue(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    await callback_query.message.delete()
    await callback_query.message.answer("Продолжаем создание акта!")

    result = await create_act(user_id, user_data, bot, dp)

    if result is None:
        await callback_query.message.answer("Пожалуйста, добавьте хотя бы один текст или фотографию.", reply_markup=keyboard_main)
        return

    await callback_query.message.answer("Выбери действие", reply_markup=keyboard_create_act)


@dp.callback_query(lambda c: c.data == "button_save_create_act")
async def callback_button_save_create_act(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    await callback_query.message.delete()
    await callback_query.message.answer("Напишите название объекта")

    object_name = await set_info_for_act(user_id, bot, dp)

    await callback_query.message.answer("Напишите название проекта")

    project_name = await set_info_for_act(user_id, bot, dp)

    await callback_query.message.answer("Напишите название компании")

    company_name = await set_info_for_act(user_id, bot, dp)

    await callback_query.message.answer("Напишите название акта")

    title = await set_info_for_act(user_id, bot, dp)

    if title:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{getenv("URL")}/create_act/",
                    json={
                        "tg_id": str(user_id),
                        "object_name": str(object_name),
                        "project_name": str(project_name),
                        "company_name": str(company_name),
                        "title": str(title),
                        "data_obj": user_data.get(user_id, {}),
                    },
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        await callback_query.message.answer("Акт успешно сохранён.")

                        await callback_query.message.answer("Выберите следующее действие", reply_markup=keyboard_saved)
                        user_data[user_id] = {}

                        user_act_data[user_id] = response_data
                        act_id_storage["id"] = response_data.get("id", None)

                        return response_data
                    else:
                        await callback_query.message.answer("Возникла ошибка, сохранение не удалось")
                        return False
            except aiohttp.ClientError as e:
                await callback_query.message.answer(f"Ошибка сети: {e}")
                return False


@dp.callback_query(lambda c: c.data.startswith("send_file"))
async def callback_send_file(callback_query: types.CallbackQuery):
    await callback_query.message.delete()

    _, file_format = callback_query.data.split(":")

    act_id = act_id_storage.get("id", None)
    act_data = await fetch_data(f"get-file-path/{act_id}")

    if act_data:
        file_path = act_data.get("file_path_pdf") if str(file_format) == "pdf" else act_data.get("file_path")

        if not file_path:
            await callback_query.message.answer("Не найден акт для скачивания.")
            await process_go_to_start(callback_query.message)

        if file_path:
            await send_file(callback_query, file_path)

            if send_file_menu.get("status", False):
                await callback_query.message.answer("Выбери действие", reply_markup=keyboard_upload_changed_act)
            else:

                page = int(act_id) // 5 - 1 if int(act_id) % 5 == 0 else int(act_id) // 5

                button_name_short = truncate_string(f"item:{act_id}:{act_id}. {file_path.replace("acts/", "")}", 30)

                inline_keyboard = [
                    [types.InlineKeyboardButton(text="Вернуться к акту", callback_data=button_name_short)],
                    [
                        types.InlineKeyboardButton(text="Вернуться в хранилище", callback_data=f"storage_acts:{page}"),
                        types.InlineKeyboardButton(text="Вернуться в меню", callback_data="go_to_start"),
                    ],
                ]

                await process_go_to_start(callback_query.message, inline_keyboard)


@dp.callback_query(lambda c: c.data == "upload_changed_act")
async def callback_upload_changed_act(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    await callback_query.message.delete()
    await callback_query.message.answer("Загрузите изменённый АКТ")
    new_file_path = await change_file(user_id, bot, dp)

    if new_file_path:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{getenv("URL")}/update_docx_file/", json={"id": act_id_storage.get("id", None), "file_path": str(new_file_path)}
                ) as response:
                    if response.status == 200:
                        response_data = await response.json()

                        await callback_query.message.answer(
                            "Изменённый АКТ сохранён.\nВыберите следующее действие", reply_markup=keyboard_upload_changed_act
                        )

                        return response_data
                    else:
                        await callback_query.message.answer("Возникла ошибка, сохранение не удалось")
                        return False
            except aiohttp.ClientError as e:
                await callback_query.message.answer(f"Ошибка сети: {e}")
                Log(f"Ошибка сети: {e}", "bot", LogLevels.ERROR)
                return False


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
