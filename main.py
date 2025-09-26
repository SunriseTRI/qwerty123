import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from core.handlers import register_handlers
from core.database import init_db

# === Логи ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# === Токен ===
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# === Основная функция ===
async def main():
    init_db()
    from core.database import merge_faq_from_excel
    try:
        new, updated = merge_faq_from_excel("faq.xlsx")
        logger.info(f"FAQ синхронизирован. Новые: {new}, Обновленные: {updated}")
    except Exception as e:
        logger.error(f"Ошибка синхронизации FAQ: {e}")

    await register_handlers(dp)
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
