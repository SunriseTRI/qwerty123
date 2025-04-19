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

CONTACT_KB = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)


def generate_question_hash(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()[:16]


async def cmd_start(message: Message):
    if is_user_registered(message.from_user.id):
        await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
    else:
        await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)


async def cmd_help(message: Message):
    help_text = (
        "/start - начать\n"
        "/reg - регистрация\n"
        "/faq - задать вопрос"
    )
    await message.answer(help_text)


async def cmd_reg(message: Message, state: FSMContext):
    await start_registration(message, state)


async def faq_handler(message: Message, state: FSMContext):
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


async def contact_handler(message: Message, state: FSMContext):
    if message.contact:
        user = message.from_user
        insert_user(
            user_id=user.id,
            username=user.username or '',
            phone=message.contact.phone_number,
            full_name=message.contact.first_name or ''
        )
        await message.answer("✅ Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())


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


async def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_reg, Command("reg"))
    dp.message.register(contact_handler, F.contact)
    dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
    dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
    dp.message.register(faq_handler, F.text)
    dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))

# from aiogram import F
# from aiogram.types import (
#     Message,
#     ReplyKeyboardMarkup,
#     KeyboardButton,
#     ReplyKeyboardRemove,
#     InlineKeyboardMarkup,
#     InlineKeyboardButton,
#     CallbackQuery
# )
# from aiogram.filters import Command, StateFilter
# from aiogram.fsm.context import FSMContext
# from aiogram.dispatcher.dispatcher import Dispatcher
# import hashlib
#
# from .database import (
#     get_faq_answer,
#     insert_faq_question,
#     is_user_registered,
#     insert_user,
#     get_all_faq_questions,
#     log_unanswered_question,
#     get_question_by_hash  # Новая функция в database.py
# )
#
# from .registration import start_registration, process_name, process_phone, RegistrationStates
# from .nlp_utils import find_similar_questions
#
# CONTACT_KB = ReplyKeyboardMarkup(
#     keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
#     resize_keyboard=True,
#     one_time_keyboard=True
# )
#
# def generate_question_hash(question: str) -> str:
#     return hashlib.sha256(question.encode()).hexdigest()[:16]
#
# async def cmd_start(message: Message):
#     if is_user_registered(message.from_user.id):
#         await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
#     else:
#         await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)
#
# async def cmd_help(message: Message):
#     help_text = (
#         "/start - начать\n"
#         "/reg - регистрация\n"
#         "/faq - задать вопрос"
#     )
#     await message.answer(help_text)
#
# async def cmd_reg(message: Message, state: FSMContext):
#     await start_registration(message, state)
#
# async def faq_handler(message: Message, state: FSMContext):
#     if not is_user_registered(message.from_user.id):
#         return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
#
#     user_question = message.text.strip()
#     faq_questions = get_all_faq_questions()
#     if not faq_questions:
#         await message.answer("⚠️ База знаний пуста. Ожидайте ответа от оператора.")

#         return
#     similar = find_similar_questions(user_question, faq_questions, threshold=0.4)
#
#     if similar:
#         keyboard = InlineKeyboardMarkup(inline_keyboard=[])
#         for q, _ in similar:
#             question_hash = generate_question_hash(q)
#             keyboard.inline_keyboard.append(
#                 [InlineKeyboardButton(
#                     text=q[:64],  # Обрезаем текст кнопки до 64 символов
#                     callback_data=f"faq:{question_hash}"
#                 )]
#             )
#         await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
#     else:
#         insert_faq_question(user_question)
#         log_unanswered_question(user_question)
#         await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")
#
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
#
# async def process_faq_choice(callback: CallbackQuery):
#     try:
#         question_hash = callback.data.split(":")[1]
#         original_question = get_question_by_hash(question_hash)
#
#         if not original_question:
#             raise ValueError("Question not found")
#
#         answer = get_faq_answer(original_question)
#         await callback.message.answer(f"💡 {answer}")
#     except Exception as e:
#         await callback.answer("⚠️ Ответ временно недоступен", show_alert=True)
#     finally:
#         await callback.answer()
#
# async def register_handlers(dp: Dispatcher):
#     dp.message.register(cmd_start, Command("start"))
#     dp.message.register(cmd_help, Command("help"))
#     dp.message.register(cmd_reg, Command("reg"))
#     dp.message.register(contact_handler, F.contact)
#     dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
#     dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
#     dp.message.register(faq_handler, F.text)
#     dp.callback_query.register(process_faq_choice, F.data.startswith("faq:"))
#
#
# # # from aiogram import F
#
#
#
#
#
#
#
# # # from aiogram.types import (
# # #     Message,
# # #     ReplyKeyboardMarkup,
# # #     KeyboardButton,
# # #     ReplyKeyboardRemove,
# # #     InlineKeyboardMarkup,  # ✅ Добавлено
# # #     InlineKeyboardButton  # ✅ Добавлено
# # # )
# # # from aiogram.filters import Command, StateFilter
# # # from aiogram.fsm.context import FSMContext
# # # from aiogram.dispatcher.dispatcher import Dispatcher
# # # from aiogram.types import CallbackQuery
# # #
# # # from .database import (
# # #     get_faq_answer,
# # #     insert_faq_question,
# # #     is_user_registered,
# # #     insert_user,
# # #     get_all_faq_questions,  # ✅ Убедитесь, что эта функция есть в database.py
# # #     log_unanswered_question  # ✅ Убедитесь, что эта функция есть в database.py
# # # )
# # # from .registration import start_registration, process_name, process_phone, RegistrationStates
# # # from .generator import generate_response
# # # from .nlp_utils import find_similar_questions  # ✅ Убедитесь, что файл существует
# # #
# # #
# # # # Клавиатура запроса контакта
# # # CONTACT_KB = ReplyKeyboardMarkup(
# # #     keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
# # #     resize_keyboard=True,
# # #     one_time_keyboard=True
# # # )
# # #
# # # # Команда /start
# # # async def cmd_start(message: Message):
# # #     if is_user_registered(message.from_user.id):
# # #         await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
# # #     else:
# # #         await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)
# # #
# # # # Команда /help
# # # async def cmd_help(message: Message):
# # #     help_text = (
# # #         "/start - начать\n"
# # #         "/reg - регистрация\n"
# # #         "/faq - задать вопрос"
# # #     )
# # #     await message.answer(help_text)
# # #
# # # # Команда /reg
# # # async def cmd_reg(message: Message, state: FSMContext):
# # #     await start_registration(message, state)
# # #
# # # # Обработка входящего текстового вопроса
# # # async def faq_handler(message: Message, state: FSMContext):
# # #     if not is_user_registered(message.from_user.id):
# # #         return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
# # #
# # #     user_question = message.text.strip()
# # #
# # #     # Поиск похожих вопросов
# # #     faq_questions = get_all_faq_questions()
# # #     similar = find_similar_questions(user_question, faq_questions, threshold=0.4)
# # #
# # #     if similar:
# # #         # Если есть похожие вопросы, предлагаем выбор
# # #         keyboard = InlineKeyboardMarkup(inline_keyboard=[])
# # #         for q, _ in similar:
# # #             keyboard.inline_keyboard.append(
# # #                 [InlineKeyboardButton(text=q, callback_data=f"faq_choose:{q}")]
# # #             )
# # #         await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
# # #     else:
# # #         # Если вопрос новый, сохраняем
# # #         insert_faq_question(user_question)
# # #         log_unanswered_question(user_question)
# # #         await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")
# # #
# # # # Обработка выбора вопроса
# # # @dp.callback_query(F.data.startswith("faq_choose:"))
# # # async def process_faq_choice(callback: CallbackQuery):
# # #     selected_question = callback.data.split(":")[1]
# # #     answer = get_faq_answer(selected_question)
# # #     await callback.message.answer(f"💡 {answer}")
# # #     await callback.answer()
# # #
# # # # Обработка контакта (через кнопку)
# # # async def contact_handler(message: Message, state: FSMContext):
# # #     if message.contact:
# # #         user = message.from_user
# # #         name = message.contact.first_name or ''
# # #         phone = message.contact.phone_number
# # #         insert_user(user.id, user.username or '', phone, name)
# # #         await message.answer("✅ Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())
# # #
# # #
# # #
# # # async def register_handlers(dp: Dispatcher):
# # #     dp.message.register(cmd_start, Command("start"))
# # #     dp.message.register(cmd_help, Command("help"))
# # #     dp.message.register(cmd_reg, Command("reg"))
# # #     dp.message.register(contact_handler, lambda msg: msg.contact is not None)
# # #     dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
# # #     dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
# # #     dp.message.register(faq_handler, F.text)
# # #     dp.callback_query(F.data.startswith("faq_choose:"))
# # #     register_callback_handlers(dp)  # ✅ Колбэки регистрируются здесь
# # #
# # # # Колбэк-хэндлеры
# # # def register_callback_handlers(dp: Dispatcher):
# # #     @dp.callback_query(F.data.startswith("faq_choose:"))
# # #     async def process_faq_choice(callback: CallbackQuery):
# # #         selected_question = callback.data.split(":")[1]
# # #         answer = get_faq_answer(selected_question)
# # #         await callback.message.answer(f"💡 {answer}")
# # #         await callback.answer()
# #
# # from aiogram import F
# # from aiogram.types import (
# #     Message,
# #     ReplyKeyboardMarkup,
# #     KeyboardButton,
# #     ReplyKeyboardRemove,
# #     InlineKeyboardMarkup,
# #     InlineKeyboardButton,
# #     CallbackQuery
# # )
# # from aiogram.filters import Command, StateFilter
# # from aiogram.fsm.context import FSMContext
# # from aiogram.dispatcher.dispatcher import Dispatcher
# #
# # from .database import (
# #     get_faq_answer,
# #     insert_faq_question,
# #     is_user_registered,
# #     insert_user,
# #     get_all_faq_questions,
# #     log_unanswered_question
# # )
# # from .registration import start_registration, process_name, process_phone, RegistrationStates
# # from .generator import generate_response
# # from .nlp_utils import find_similar_questions
# #
# # # Клавиатура запроса контакта
# # CONTACT_KB = ReplyKeyboardMarkup(
# #     keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]],
# #     resize_keyboard=True,
# #     one_time_keyboard=True
# # )
# #
# #
# # # Команда /start
# # async def cmd_start(message: Message):
# #     if is_user_registered(message.from_user.id):
# #         await message.answer("Привет! Задайте ваш вопрос.", reply_markup=ReplyKeyboardRemove())
# #     else:
# #         await message.answer("Сначала зарегистрируйтесь:", reply_markup=CONTACT_KB)
# #
# #
# # # Команда /help
# # async def cmd_help(message: Message):
# #     help_text = (
# #         "/start - начать\n"
# #         "/reg - регистрация\n"
# #         "/faq - задать вопрос"
# #     )
# #     await message.answer(help_text)
# #
# #
# # # Команда /reg
# # async def cmd_reg(message: Message, state: FSMContext):
# #     await start_registration(message, state)
# #
# #
# # # Обработка входящего текстового вопроса
# # async def faq_handler(message: Message, state: FSMContext):
# #     if not is_user_registered(message.from_user.id):
# #         return await message.answer("❌ Сначала пройдите регистрацию!", reply_markup=CONTACT_KB)
# #
# #     user_question = message.text.strip()
# #
# #     # Поиск похожих вопросов
# #     faq_questions = get_all_faq_questions()
# #     similar = find_similar_questions(user_question, faq_questions, threshold=0.4)
# #
# #     if similar:
# #         # Если есть похожие вопросы, предлагаем выбор
# #         keyboard = InlineKeyboardMarkup(inline_keyboard=[])
# #         # for q, _ in similar:
# #         #     keyboard.inline_keyboard.append(
# #         #         [InlineKeyboardButton(text=q, callback_data=f"faq_choose:{q}")]
# #         #     )
# #         for q, _ in similar:
# #             # Проверяем длину callback_data (макс. 64 байта)
# #             callback_data = f"faq:{q[:50]}"  # Обрезаем вопрос до 50 символов
# #             keyboard.inline_keyboard.append(
# #                 [InlineKeyboardButton(text=q, callback_data=callback_data)]
# #             )
# #         await message.answer("🔍 Возможно, вы имели в виду:", reply_markup=keyboard)
# #     else:
# #         # Если вопрос новый, сохраняем
# #         insert_faq_question(user_question)
# #         log_unanswered_question(user_question)
# #         await message.answer("📝 Вопрос передан специалистам. Мы ответим вам в ближайшее время!")
# #
# #
# # # Обработка контакта (через кнопку)
# # async def contact_handler(message: Message, state: FSMContext):
# #     if message.contact:
# #         user = message.from_user
# #         name = message.contact.first_name or ''
# #         phone = message.contact.phone_number
# #         insert_user(user.id, user.username or '', phone, name)
# #         await message.answer("✅ Регистрация прошла успешно!", reply_markup=ReplyKeyboardRemove())
# #
# #
# # # Регистрация всех обработчиков
# # async def register_handlers(dp: Dispatcher):
# #     # Регистрация message handlers
# #     dp.message.register(cmd_start, Command("start"))
# #     dp.message.register(cmd_help, Command("help"))
# #     dp.message.register(cmd_reg, Command("reg"))
# #     dp.message.register(contact_handler, F.contact)
# #     dp.message.register(process_name, StateFilter(RegistrationStates.waiting_for_name))
# #     dp.message.register(process_phone, StateFilter(RegistrationStates.waiting_for_phone))
# #     dp.message.register(faq_handler, F.text)
# #
# #     # Регистрация callback handlers
# #     dp.callback_query.register(process_faq_choice, F.data.startswith("faq_choose:"))
# #
# #
# # # Обработка выбора вопроса (теперь внутри области видимости)
# # async def process_faq_choice(callback: CallbackQuery):
# #     selected_question = callback.data.split(":")[1]
# #     answer = get_faq_answer(selected_question)
# #     await callback.message.answer(f"💡 {answer}")
# #     await callback.answer()