from aiogram import F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.dispatcher import Dispatcher
import logging
import hashlib
from .database import get_user_questions, delete_user_question, add_user_question
from .database import get_faq_answer,insert_faq_question,is_user_registered,insert_user,get_all_faq_questions,log_unanswered_question,get_question_by_hash
from .registration import start_registration, process_name, process_phone, RegistrationStates
from .nlp_utils import find_similar_questions
# from core.keyboards import get_main_menu_keyboard

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



PROFILE_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📂 Мои вопросы"), KeyboardButton(text="✏️ Редактирование списка")],
        [KeyboardButton(text="📊 Статус"), KeyboardButton(text="◀️ Назад")]
    ],
    resize_keyboard=True
)

CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

MAIN_MENU_KB = ReplyKeyboardMarkup(
    keyboard=[

        [KeyboardButton(text="📥 Выгрузка FAQ"), KeyboardButton(text="📖 Инструкция")],
        [KeyboardButton(text="🎫 Создать задачу"), KeyboardButton(text="❓ HELP"), KeyboardButton(text="◀️ Назад")]
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

async def handle_status(message: Message):
    user_id = message.from_user.id
    questions = get_user_questions(user_id)
    total = len(questions)
    answered = len([q for q in questions if q[2]])
    unanswered = len([q for q in questions if not q[2]])
    rejected = len([q for q in questions if q[3] == "red"])
    text = (
        f"📊 Ваш статус:\n\n"
        f"— Всего вопросов: {total}\n"
        f"— С ответом: {answered} 🟢\n"
        f"— Без ответа: {unanswered} 🟡\n"
        f"— Отклонено: {rejected} 🔴"
    )
    await message.answer(text)

async def delete_question_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    q_id = int(callback.data.split(":")[1])
    success = delete_user_question(user_id, q_id)
    if success:
        await callback.message.answer("✅ Вопрос удалён из вашего списка.")
    else:
        await callback.message.answer("⚠️ Ошибка при удалении.")
    await callback.answer()

async def handle_my_questions(message: Message):
    user_id = message.from_user.id
    questions = get_user_questions(user_id)
    if not questions:
        await message.answer("📂 У вас пока нет вопросов.")
        return

    text = "📂 Ваши вопросы:\n\n"
    status_map = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
    for q_id, q, a, s in questions:
        text += f"{status_map.get(s,'❔')} {q}\n"
    await message.answer(text)

async def handle_edit_questions(message: Message):
    user_id = message.from_user.id
    questions = get_user_questions(user_id)
    if not questions:
        await message.answer("✏️ У вас пока нет вопросов для редактирования.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for q_id, q, a, s in questions:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"🗑 {q[:30]}...",
                callback_data=f"deleteq:{q_id}"
            )
        ])
    await message.answer("✏️ Выберите вопрос для удаления:", reply_markup=keyboard)

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

INSTRUCTION_TEXT = (
    "🤖✨ Привет! FAQ бот-помощник ауф\n\n"
    "Вот как со мной общаться:\n"
    "1️⃣ Пиши вопрос обычным человеческим языком.\n"
    "👉 Пример: 'Как обновить устройство?'\n"
    "2️⃣ Я ищу ответ по 🔍 базе знаний и FAQ.\n"
    "– Если нахожу похожее → покажу варианты.\n"
    "– Если не нахожу → тыкай кнопку ❌ 'Нет ответа' и вопрос уйдёт в базу.\n"
    "3️⃣ Выбирай самый подходящий вариант ответа 👍\n\n"
    "⚡ Важно:\n"
    "– Чем понятнее вопрос → тем точнее ответ.\n"
    "– Если текст ответа длинный, я его сокращу и покажу рейтинг (📊0.87*5).\n\n"
    "- 🧠 Ещё у меня есть память! Все твои вопросы, на которые я не нашёл ответ, "
    "я сохраняю в твоём профиле. Потом можешь зайти, посмотреть и гордиться, что ты умнее пары строк кода и алгоритмов 😎 "
    "\n\n🎉 Всё, больше думать не надо! Жми кнопки, смотри ответы и кайфуй 🕺💃"
)

async def handle_instruction(message: Message):
    await message.answer(INSTRUCTION_TEXT)

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
            reply_markup=MAIN_MENU_KB,
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
        "Профиль пользователя:",
        reply_markup=MAIN_MENU_KB
    )

async def export_faq_handler(message: Message):
    """Заглушка: выгрузка FAQ"""
    await message.answer("📥 Функция выгрузки FAQ в разработке...")

async def create_ticket_handler(message: Message):
    """Заглушка: создание задачи"""
    await message.answer("🎫 Функция создания задачи в разработке...")

unanswered_map = {}

async def faq_handler(message: Message, state: FSMContext):
    if message.text in ["❓ HELP", "📋 MENU", "📥 Выгрузка FAQ", "📖 Инструкция", "🎫 Создать задачу", "◀️ Назад"]:
        return
    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
        return
    user_question = message.text.strip()
    faq_questions = get_all_faq_questions()
    if not faq_questions:
        await message.answer("⚠️ База знаний пуста. Ожидайте ответа от оператора.")
        return
    similar = find_similar_questions(user_question, faq_questions)
    if similar:
        # сортируем по средней оценке (desc)
        similar = sorted(similar, key=lambda x: x[1], reverse=True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for item in similar:
            q = item[0]
            avg = item[1] if len(item) > 1 else 0.0
            count = item[2] if len(item) > 2 else 1
            display_text = q[:35] + ("..." if len(q) > 35 else "")
            score_text = f" (🔎={avg:.2f}|⚙={count})"
            btn_text = f"{display_text}{score_text}"
            q_hash = hashlib.sha256(q.encode()).hexdigest()[:16]
            keyboard.inline_keyboard.append(
                [InlineKeyboardButton(text=btn_text, callback_data=f"faq:{q_hash}")]
            )
        keyboard.inline_keyboard.append(
            [InlineKeyboardButton(text="🔴Нет ответа на мой вопрос🔴", callback_data="unanswered:add")]
        )
        bot_msg = await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
        unanswered_map[(bot_msg.chat.id, bot_msg.message_id)] = user_question
    else:
        # Если ничего не найдено — сохраняем и уведомляем (как раньше)
        insert_faq_question(user_question)
        log_unanswered_question(user_question)
        await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")

async def handle_unanswered(callback: CallbackQuery):
    try:
        key = (callback.message.chat.id, callback.message.message_id)
        user_q = unanswered_map.pop(key, None)
        if not user_q:
            await callback.answer("Вопрос добавлен. (оригинал не найден в кеше)", show_alert=True)
            return
        insert_faq_question(user_q)
        log_unanswered_question(user_q)
        await callback.answer("📝 Ваш вопрос добавлен в список для оператора. Спасибо!", show_alert=True)
        await callback.message.reply("Вопрос добавлен в очередь оператору. Мы уведомим вас, когда ответим.")
    except Exception as e:
        logging.exception("Ошибка в handle_unanswered:")
        await callback.answer("Ошибка при добавлении вопроса. Попробуйте ещё раз.", show_alert=True)


async def process_faq_choice(callback: CallbackQuery):
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
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import logging


async def inline_menu_handler(callback: CallbackQuery):
    try:
        action = callback.data.split(":")[1]

        if action == "export":
            await callback.message.answer("📥 **Выгрузка FAQ** в разработке...")

        elif action == "instruction":
            await callback.message.answer(INSTRUCTION_TEXT)

        elif action == "ticket":
            await callback.message.answer("🎫 **Создание задачи** в разработке...")

        elif action == "help":
            await callback.message.answer("❓ **Помощь по боту** в разработке...")

        elif action == "main":
            try:
                await callback.message.edit_text(
                    "🏠 **Профиль пользователя**",
                    reply_markup=get_main_menu_keyboard()
                )
            except TelegramBadRequest as e:
                # если сообщение не изменилось — просто игнорим
                if "message is not modified" in str(e):
                    await callback.answer()
                    return
                raise
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка в inline_menu_handler: {e}")
        await callback.answer("⚠️ Произошла ошибка", show_alert=True)

async def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_start, F.text == "/start")
    dp.message.register(handle_faq, F.text == "Выгрузка FAQ")
    dp.message.register(handle_instruction, F.text == "Инструкция")
    dp.message.register(handle_create_task, F.text == "Создать задачу")
    dp.message.register(handle_main_menu, F.text == "Профиль пользователя")
    dp.message.register(contact_handler, F.contact)
    dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
    dp.message.register(help_handler, F.text == "❓ HELP")
    dp.message.register(menu_handler, F.text == "📋 MENU")
    dp.message.register(back_to_main_menu, F.text == "◀️ Назад")
    dp.message.register(export_faq_handler, F.text == "📥 Выгрузка FAQ")
    dp.message.register(handle_instruction, F.text == "📖 Инструкция")
    dp.message.register(create_ticket_handler, F.text == "🎫 Создать задачу")
    dp.message.register(handle_my_questions, F.text == "📂 Мои вопросы")
    dp.message.register(handle_edit_questions, F.text == "✏️ Редактирование списка")
    dp.message.register(handle_status, F.text == "📊 Статус")
    dp.callback_query.register(delete_question_callback, F.data.startswith("deleteq:"))
    dp.message.register(faq_handler, F.text)
    dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))
    dp.callback_query.register(inline_menu_handler, F.data.startswith("menu:"))
    dp.callback_query.register(handle_unanswered, F.data == "unanswered:add")