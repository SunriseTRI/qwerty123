from core.keyboards import get_main_menu_keyboard
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from .database import insert_user
import re


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


PHONE_REGEX = r"^\+\d{1,3}\d{7,10}$"


async def start_registration(message: types.Message, state: FSMContext):
    await message.answer("Введите ваше имя:")
    await state.set_state(RegistrationStates.waiting_for_name)


async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер телефона (+XXXXXXXXXXX):")
    await state.set_state(RegistrationStates.waiting_for_phone)


async def process_phone(message: types.Message, state: FSMContext):
    if not re.match(PHONE_REGEX, message.text):
        return await message.answer("Неверный формат. Попробуйте ещё раз:")

    data = await state.get_data()
    name = data.get('name', '')
    phone = message.text
    user = message.from_user

    insert_user(
        user_id=user.id,
        username=user.username or '',
        phone=phone,
        full_name=name
    )

    # Показываем inline меню после регистрации
    welcome_text = f"✅ **Регистрация завершена, {name}!**\n\nВыберите опцию из меню ниже."
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),  # ← ИМЕННО ЭТУ ФУНКЦИЮ НУЖНО ДОБАВИТЬ
        parse_mode="Markdown"
    )
    await state.clear()