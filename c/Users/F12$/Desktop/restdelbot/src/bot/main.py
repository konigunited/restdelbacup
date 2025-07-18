import asyncio
import logging
import json
from aiogram import Bot, Dispatcher

from .handlers import router
from config.settings import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    try:
        Config.validate()
        
        # Отладка credentials
        try:
            with open(Config.GOOGLE_CREDENTIALS_PATH, 'r') as f:
                creds = json.load(f)
                logger.info(f"Using project_id: {creds['project_id']}")
                logger.info(f"Using email: {creds['client_email']}")
        except Exception as e:
            logger.error(f"Error reading credentials: {e}")
        
        # Создаем бота БЕЗ parse_mode
        bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        
        dp = Dispatcher()
        dp.include_router(router)
        
        logger.info("Starting REST Delivery Bot...")
        
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())