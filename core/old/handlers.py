from aiogram import F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.dispatcher import Dispatcher
import logging
import hashlib

from .database import (
    get_faq_answer,
    insert_faq_question,
    is_user_registered,
    insert_user,
    get_all_faq_questions,
    log_unanswered_question,
    get_question_by_hash
)

from .registration import start_registration, process_name, process_phone, RegistrationStates
from .nlp_utils import find_similar_questions
from core.keyboards import get_main_menu_keyboard

# ====================
# Кнопки
# ====================

CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ HELP"), KeyboardButton(text="📋 MENU")],
        [KeyboardButton(text="💬 Задать вопрос")]
    ],
    resize_keyboard=True,
    persistent=True
)

MENU_OPTIONS_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Выгрузка FAQ"), KeyboardButton(text="📖 Инструкция")],
        [KeyboardButton(text="🎫 Создать задачу"), KeyboardButton(text="◀️ Назад")]
    ],
    resize_keyboard=True,
    persistent=True
)

# ====================
# Основные функции
# ====================

async def cmd_start(message: Message):
    if is_user_registered(message.from_user.id):
        welcome_text = (
            "🤖 **Добро пожаловать в бот поддержки!**\n\n"
            "Выберите нужную опцию из меню ниже или просто напишите ваш вопрос."
        )
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "Сначала зарегистрируйтесь:",
            reply_markup=CONTACT_KB
        )

async def handle_faq(message: Message):
    await message.answer("Здесь будет выгрузка FAQ.")

async def handle_instruction(message: Message):
    await message.answer("Здесь будет инструкция.")

async def handle_create_task(message: Message):
    await message.answer("Функция создания задачи пока в разработке.")

async def handle_main_menu(message: Message):
    await message.answer("Вы снова в главном меню.", reply_markup=get_main_menu_keyboard())

async def contact_handler(message: Message, state: FSMContext):
    if message.contact:
        user = message.from_user
        insert_user(
            user_id=user.id,
            username=user.username or '',
            phone=message.contact.phone_number,
            full_name=message.contact.first_name or ''
        )
        welcome_text = (
            "✅ **Регистрация прошла успешно!**\n\n"
            "Теперь вы можете пользоваться всеми функциями бота. "
            "Выберите опцию из меню ниже или просто задайте вопрос."
        )
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
        await state.clear()

async def help_handler(message: Message):
    """Обработчик кнопки HELP"""
    help_text = (
        "🤖 **Помощь по боту**\n\n"
        "• **Задать вопрос** - получить ответ из базы знаний\n"
        "• **Выгрузка FAQ** - скачать базу часто задаваемых вопросов\n"
        "• **Инструкция** - руководство по использованию\n"
        "• **Создать задачу** - обратиться в техническую поддержку\n\n"
        "Для начала просто напишите ваш вопрос!"
    )
    await message.answer(help_text)

async def menu_handler(message: Message):
    """Показывает меню при нажатии кнопки 📋 MENU"""
    await message.answer(
        "📋 Выберите опцию:",
        reply_markup=MENU_OPTIONS_KB
    )

async def back_to_main_menu(message: Message):
    """Возврат в главное меню"""
    await message.answer(
        "Главное меню:",
        reply_markup=MAIN_MENU_KB
    )

async def export_faq_handler(message: Message):
    """Заглушка: выгрузка FAQ"""
    await message.answer("📥 Функция выгрузки FAQ в разработке...")

async def create_ticket_handler(message: Message):
    """Заглушка: создание задачи"""
    await message.answer("🎫 Функция создания задачи в разработке...")

async def faq_handler(message: Message, state: FSMContext):
    """Обработчик обычного текста для FAQ"""
    if message.text in ["❓ HELP", "📋 MENU", "📥 Выгрузка FAQ", "📖 Инструкция", "🎫 Создать задачу", "◀️ Назад"]:
        return  # Эти сообщения обрабатываются другими хендлерами

    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
        return

    user_question = message.text.strip()
    faq_questions = get_all_faq_questions()

    if not faq_questions:
        await message.answer("⚠️ База знаний пуста. Ожидайте ответа от оператора.")
        return

    similar = find_similar_questions(user_question, faq_questions, threshold=0.4)

    if similar:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for q, _ in similar:
            question_hash = hashlib.sha256(q.encode()).hexdigest()[:16]
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=q[:64], callback_data=f"faq:{question_hash}")]
            )
        await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
    else:
        insert_faq_question(user_question)
        log_unanswered_question(user_question)
        await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")

async def process_faq_choice(callback: CallbackQuery):
    """Обработчик выбора варианта FAQ по inline кнопке"""
    try:
        question_hash = callback.data.split(":")[1]
        original_question = get_question_by_hash(question_hash)

        if not original_question:
            raise ValueError("Question not found")

        answer = get_faq_answer(original_question)
        await callback.message.answer(f"💡 {answer}")
    except Exception:
        await callback.answer("⚠️ Ответ временно недоступен", show_alert=True)
    finally:
        await callback.answer()

async def inline_menu_handler(callback: CallbackQuery):
    """Обработчик inline меню"""
    try:
        action = callback.data.split(":")[1]

        if action == "export":
            await callback.message.answer("📥 **Выгрузка FAQ** в разработке...")

        elif action == "instruction":
            await callback.message.answer("📖 **Инструкция по использованию** в разработке...")

        elif action == "ticket":
            await callback.message.answer("🎫 **Создание задачи** в разработке...")

        elif action == "help":
            await callback.message.answer("❓ **Помощь по боту** в разработке...")

        elif action == "main":
            await callback.message.edit_text(
                "🏠 **Главное меню**",
                reply_markup=get_main_menu_keyboard()
            )

        await callback.answer()

    except Exception as e:
        logging.error(f"Ошибка в inline_menu_handler: {e}")
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)

# ====================
# Регистрация хендлеров
# ====================

async def register_handlers(dp: Dispatcher):
    # Команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_start, F.text == "/start")

    # Обработка кнопок меню
    dp.message.register(handle_faq, F.text == "Выгрузка FAQ")
    dp.message.register(handle_instruction, F.text == "Инструкция")
    dp.message.register(handle_create_task, F.text == "Создать задачу")
    dp.message.register(handle_main_menu, F.text == "Главное меню")
    dp.message.register(contact_handler, F.contact)

    # FSM регистрации
    dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))

    # Основные кнопки
    dp.message.register(help_handler, F.text == "❓ HELP")
    dp.message.register(menu_handler, F.text == "📋 MENU")
    dp.message.register(back_to_main_menu, F.text == "◀️ Назад")
    dp.message.register(export_faq_handler, F.text == "📥 Выгрузка FAQ")
    dp.message.register(handle_instruction, F.text == "📖 Инструкция")
    dp.message.register(create_ticket_handler, F.text == "🎫 Создать задачу")

    # FAQ обработка обычного текста
    dp.message.register(faq_handler, F.text)

    # Inline обработчики
    dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))
    dp.callback_query.register(inline_menu_handler, F.data.startswith("menu:"))
