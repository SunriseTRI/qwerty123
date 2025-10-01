from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Выгрузка FAQ"),
            KeyboardButton(text="Инструкция")
        ],
        [
            KeyboardButton(text="Создать задачу"),
            KeyboardButton(text="Профиль пользователя")
        ]
    ],
    resize_keyboard=True,   # кнопки подгоняются под ширину
    one_time_keyboard=False # False — чтобы не исчезали после первого нажатия
)

def get_main_menu_keyboard():
    """
    Главное inline-меню бота
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📥 Выгрузка FAQ", callback_data="menu:export"),
            InlineKeyboardButton(text="📖 Инструкция", callback_data="menu:instruction")
        ],
        [
            InlineKeyboardButton(text="🎫 Создать задачу", callback_data="menu:ticket"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="menu:help")
        ],
        [
            InlineKeyboardButton(text="🏠 Профиль пользователя", callback_data="menu:main")
        ]
    ])
