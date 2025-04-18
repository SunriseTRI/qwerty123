import asyncio
import logging
from aiogram import F, Bot, Dispatcher
from core.handlers import register_handlers
from core.database import init_db
from dotenv import load_dotenv
load_dotenv()
# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка токена из .env
from dotenv import load_dotenv
import os
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def main():
    init_db()
    await register_handlers(dp)  # 🟢 обязательно await!
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")