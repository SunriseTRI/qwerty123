from aiogram import F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.dispatcher import Dispatcher
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


HELP_EMOJI = "❓"
MENU_EMOJI = "📋"
EXPORT_EMOJI = "📥"
INSTRUCTION_EMOJI = "📖"
TICKET_EMOJI = "🎫"
BACK_EMOJI = "◀️"
QUESTION_EMOJI = "💬"

CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)


#+++++++++++++

async def inline_menu_handler(callback: CallbackQuery):
    """Обработчик нажатий на inline кнопки меню"""
    try:
        # Получаем действие из callback_data (формат "menu:action")
        action = callback.data.split(":")[1]

        if action == "export":
            await callback.message.answer("📥 **Выгрузка FAQ**\n\nФункция выгрузки базы знаний в разработке...")

        elif action == "instruction":
            instruction_text = (
                "📖 **Инструкция по использованию**\n\n"
                "1. 📝 **Задайте вопрос** - просто напишите ваш вопрос в чат\n"
                "2. 🔍 **Поиск ответа** - бот найдет похожие вопросы в базе знаний\n"
                "3. ✅ **Выбор варианта** - выберите подходящий вопрос из предложенных\n"
                "4. 📨 **Перевод оператору** - если ответ не найден, вопрос перейдет специалисту\n\n"
                "💡 **Совет:** формулируйте вопрос конкретно для лучшего поиска!"
            )
            await callback.message.answer(instruction_text, parse_mode="Markdown")

        elif action == "ticket":
            await callback.message.answer(
                "🎫 **Создание задачи в техподдержку**\n\n"
                "Функция создания заявки находится в разработке. "
                "Сейчас вы можете задать вопрос напрямую - он будет передан специалистам."
            )

        elif action == "help":
            help_text = (
                "❓ **Помощь по боту**\n\n"
                "• 💬 **Задать вопрос** - просто напишите вопрос в чат\n"
                "• 📖 **Инструкция** - руководство по использованию\n"
                "• 📥 **Выгрузка FAQ** - скачать базу знаний\n"
                "• 🎫 **Создать задачу** - обращение в техподдержку\n\n"
                "**Команды:**\n"
                "/start - начать работу\n"
                "/help - показать справку\n"
                "/reg - регистрация"
            )
            await callback.message.answer(help_text, parse_mode="Markdown")

        elif action == "main":
            # Обновляем сообщение, возвращая главное меню
            welcome_text = "🏠 **Главное меню**\n\nВыберите нужную опцию:"
            await callback.message.edit_text(
                welcome_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )

        # Подтверждаем обработку callback (убираем "часики" на кнопке)
        await callback.answer()

    except Exception as e:
        logging.error(f"Ошибка в inline_menu_handler: {e}")
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)


async def menu_handler(message: Message):
    """Обработчик кнопки MENU"""
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

# Заглушки для функционала меню
async def export_faq_handler(message: Message):
    """Выгрузка FAQ (заглушка)"""
    await message.answer("📥 Функция выгрузки FAQ в разработке...")

async def instruction_handler(message: Message):
    """Инструкция (заглушка)"""
    instruction_text = (
        "📖 **Инструкция по использованию**\n\n"
        "1. Задайте вопрос в свободной форме\n"
        "2. Бот найдет похожие вопросы в базе знаний\n"
        "3. Выберите подходящий вариант из предложенных\n"
        "4. Если ответ не найден, вопрос перейдет оператору\n\n"
        "🚀 Функционал постоянно расширяется!"
    )
    await message.answer(instruction_text)

async def create_ticket_handler(message: Message):
    """Создание задачи (заглушка)"""
    await message.answer("🎫 Функция создания заявки в техподдержку в разработке...")


#+++++++++++++
def generate_question_hash(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]


# async def cmd_start(message: Message):
#     if is_user_registered(message.from_user.id):
#         await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
#     else:
#         await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)

#+++
# async def cmd_start(message: Message):
#     if is_user_registered(message.from_user.id):
#         await message.answer(
#             "Привет! Выберите действие:",
#             reply_markup=MAIN_MENU_KB
#         )
#     else:
#         await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)


async def cmd_start(message: Message):
    """Обработчик команды /start"""
    if is_user_registered(message.from_user.id):
        # Показываем приветствие с inline меню
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
        # Регистрация (оставляем старую клавиатуру с контактом)
        await message.answer(
            "Сначала зарегистрируйтесь:",
            reply_markup=CONTACT_KB
        )

async def cmd_help(message: Message):
    help_text = (
        "/start - начать\n"
        "/reg - регистрация\n"
        "/faq - задать вопрос"
    )
    await message.answer(help_text)


async def cmd_reg(message: Message, state: FSMContext):
    await start_registration(message, state)


async def inline_menu_handler(callback: CallbackQuery):
    """Обработчик нажатий на inline кнопки меню"""
    try:
        # Получаем действие из callback_data (формат "menu:action")
        action = callback.data.split(":")[1]

        if action == "export":
            await callback.message.answer("📥 **Выгрузка FAQ**\n\nФункция выгрузки базы знаний в разработке...")

        elif action == "instruction":
            instruction_text = (
                "📖 **Инструкция по использованию**\n\n"
                "1. 📝 **Задайте вопрос** - просто напишите ваш вопрос в чат\n"
                "2. 🔍 **Поиск ответа** - бот найдет похожие вопросы в базе знаний\n"
                "3. ✅ **Выбор варианта** - выберите подходящий вопрос из предложенных\n"
                "4. 📨 **Перевод оператору** - если ответ не найден, вопрос перейдет специалисту\n\n"
                "💡 **Совет:** формулируйте вопрос конкретно для лучшего поиска!"
            )
            await callback.message.answer(instruction_text, parse_mode="Markdown")

        elif action == "ticket":
            await callback.message.answer(
                "🎫 **Создание задачи в техподдержку**\n\n"
                "Функция создания заявки находится в разработке. "
                "Сейчас вы можете задать вопрос напрямую - он будет передан специалистам."
            )

        elif action == "help":
            help_text = (
                "❓ **Помощь по боту**\n\n"
                "• 💬 **Задать вопрос** - просто напишите вопрос в чат\n"
                "• 📖 **Инструкция** - руководство по использованию\n"
                "• 📥 **Выгрузка FAQ** - скачать базу знаний\n"
                "• 🎫 **Создать задачу** - обращение в техподдержку\n\n"
                "**Команды:**\n"
                "/start - начать работу\n"
                "/help - показать справку\n"
                "/reg - регистрация"
            )
            await callback.message.answer(help_text, parse_mode="Markdown")

        elif action == "main":
            # Обновляем сообщение, возвращая главное меню
            welcome_text = "🏠 **Главное меню**\n\nВыберите нужную опцию:"
            await callback.message.edit_text(
                welcome_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )

        # Подтверждаем обработку callback (убираем "часики" на кнопке)
        await callback.answer()

    except Exception as e:
        logging.error(f"Ошибка в inline_menu_handler: {e}")
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)

# async def faq_handler(message: Message, state: FSMContext):
#     if not is_user_registered(message.from_user.id):
#         return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
#
#     user_question = message.text.strip()
#     faq_questions = get_all_faq_questions()
#
#     if not faq_questions:
#         await message.answer("⚠️ База знаний пуста. Ожидайте ответа от оператора.")
#         return
#
#     similar = find_similar_questions(user_question, faq_questions, threshold=0.4)
#
#     if similar:
#         keyboard = InlineKeyboardMarkup(inline_keyboard=[])
#         for q, _ in similar:
#             question_hash = generate_question_hash(q)
#             keyboard.inline_keyboard.append(
#                 [InlineKeyboardButton(
#                     text=q[:64],
#                     callback_data=f"faq:{question_hash}"
#                 )]
#             )
#         await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
#     else:
#         insert_faq_question(user_question)
#         log_unanswered_question(user_question)
#         await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")


# async def contact_handler(message: Message, state: FSMContext):
#     if message.contact:
#         user = message.from_user
#         insert_user(
#             user_id=user.id,
#             username=user.username or '',
#             phone=message.contact.phone_number,
#             full_name=message.contact.first_name or ''
#         )
#         await message.answer("✅ Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())


#+++


async def faq_handler(message: Message, state: FSMContext):
    # Проверяем, что сообщение не является командой меню
    if message.text in ["❓ HELP", "📋 MENU", "📥 Выгрузка FAQ", "📖 Инструкция", "🎫 Создать задачу", "◀️ Назад"]:
        return  # Эти сообщения обрабатываются другими хендлерами

    if not is_user_registered(message.from_user.id):
        return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)

    user_question = message.text.strip()
    faq_questions = get_all_faq_questions()

    if not faq_questions:
        await message.answer("⚠️ База знаний пуста. Ожидайте ответа от оператора.")
        return

    similar = find_similar_questions(user_question, faq_questions, threshold=0.4)

    if similar:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for q, _ in similar:
            question_hash = generate_question_hash(q)
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(
                    text=q[:64],
                    callback_data=f"faq:{question_hash}"
                )]
            )
        await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
    else:
        insert_faq_question(user_question)
        log_unanswered_question(user_question)
        await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")

# async def contact_handler(message: Message, state: FSMContext):
#     if message.contact:
#         user = message.from_user
#         insert_user(
#             user_id=user.id,
#             username=user.username or '',
#             phone=message.contact.phone_number,
#             full_name=message.contact.first_name or ''
#         )
#         await message.answer(
#             "✅ Регистрация прошла успешно!",
#             reply_markup=MAIN_MENU_KB  # Показываем основное меню после регистрации
#         )
#         await state.clear()


#+++++
async def contact_handler(message: Message, state: FSMContext):
    if message.contact:
        user = message.from_user
        insert_user(
            user_id=user.id,
            username=user.username or '',
            phone=message.contact.phone_number,
            full_name=message.contact.first_name or ''
        )
        # Показываем inline меню вместо Reply-клавиатуры
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


async def process_faq_choice(callback: CallbackQuery):
    try:
        question_hash = callback.data.split(":")[1]
        original_question = get_question_by_hash(question_hash)

        if not original_question:
            raise ValueError("Question not found")

        answer = get_faq_answer(original_question)
        await callback.message.answer(f"💡 {answer}")
    except Exception as e:
        await callback.answer("⚠️ Ответ временно недоступен", show_alert=True)
    finally:
        await callback.answer()


MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❓ HELP"), KeyboardButton(text="📋 MENU")],
        [KeyboardButton(text="💬 Задать вопрос")]
    ],
    resize_keyboard=True,
    persistent=True
)

# Меню дополнительных опций
MENU_OPTIONS_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📥 Выгрузка FAQ"), KeyboardButton(text="📖 Инструкция")],
        [KeyboardButton(text="🎫 Создать задачу"), KeyboardButton(text="◀️ Назад")]
    ],
    resize_keyboard=True,
    persistent=True
)

# async def register_handlers(dp: Dispatcher):
#     dp.message.register(cmd_start, Command("start"))
#     dp.message.register(cmd_help, Command("help"))
#     dp.message.register(cmd_reg, Command("reg"))
#     dp.message.register(contact_handler, F.contact)
#     dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
#     dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
#     dp.message.register(faq_handler, F.text)
#     dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))


#+++++++++++

async def cmd_menu(message: Message):
    """Показ меню по команде /menu"""
    if not is_user_registered(message.from_user.id):
        return await message.answer("❌ Сначала пройдите регистрацию!")

    await message.answer(
        "📋 **Меню бота**\n\nВыберите опцию:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="Markdown"
    )




async def register_handlers(dp: Dispatcher):
    # Команды
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_reg, Command("reg"))
    dp.message.register(cmd_menu, Command("menu"))

    # Регистрация по контакту
    dp.message.register(contact_handler, F.contact)

    # FSM регистрации
    dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))

    # Обработчики меню
    dp.message.register(help_handler, F.text == "❓ HELP")
    dp.message.register(menu_handler, F.text == "📋 MENU")
    dp.message.register(back_to_main_menu, F.text == "◀️ Назад")
    dp.message.register(export_faq_handler, F.text == "📥 Выгрузка FAQ")
    dp.message.register(instruction_handler, F.text == "📖 Инструкция")
    dp.message.register(create_ticket_handler, F.text == "🎫 Создать задачу")

    # Основной обработчик вопросов (работает для любого текста, кроме команд меню)
    dp.message.register(faq_handler, F.text)

    # Inline обработчики
    dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))
    dp.callback_query.register(inline_menu_handler, F.data.startswith("menu:"))