import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from .handlers import router
from ..config import Config

logger = logging.getLogger(__name__)

async def main(menu_json_str: str):
    """
    Основная функция для запуска бота.
    Принимает меню в виде JSON-строки.
    """
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    storage = MemoryStorage()
    
    # ПРАВИЛЬНЫЙ СПОСОБ: Передаем меню как именованный аргумент в Dispatcher.
    # Теперь он будет доступен во всех хендлерах.
    dp = Dispatcher(storage=storage, menu_json=menu_json_str)

    dp.include_router(router)

    logger.info("Starting REST Delivery Bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)