from aiogram import F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.dispatcher import Dispatcher

from .database import get_faq_answer, insert_faq_question, is_user_registered, insert_user
from .registration import start_registration, process_name, process_phone, RegistrationStates
from .generator import generate_response
# from .okdesk_integration import create_ticket  # отключено

# Клавиатура запроса контакта
CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# Команда /start
async def cmd_start(message: Message):
    if is_user_registered(message.from_user.id):
        await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)

# Команда /help
async def cmd_help(message: Message):
    help_text = (
        "/start - начать\n"
        "/reg - регистрация\n"
        "/faq - задать вопрос"
    )
    await message.answer(help_text)

# Команда /reg
async def cmd_reg(message: Message, state: FSMContext):
    await start_registration(message, state)

# Обработка входящего текстового вопроса
async def faq_handler(message: Message, state: FSMContext):
    if not is_user_registered(message.from_user.id):
        return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)

    question = message.text.strip()
    answer = get_faq_answer(question)

    if answer:
        await message.answer(f"💡 {answer}")
    else:
        insert_faq_question(question)
        await message.answer("❓ Вопрос сохранён для обработки. Спасибо!")

# Обработка контакта (через кнопку)
async def contact_handler(message: Message, state: FSMContext):
    if message.contact:
        user = message.from_user
        name = message.contact.first_name or ''
        phone = message.contact.phone_number
        insert_user(user.id, user.username or '', phone, name)
        await message.answer("✅ Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())

# Регистрация всех хэндлеров
async def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_reg, Command("reg"))
    dp.message.register(contact_handler, lambda msg: msg.contact is not None)

    dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))

    dp.message.register(faq_handler, F.text)
