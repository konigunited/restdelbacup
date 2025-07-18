import asyncio
import logging
import json
from src.bot.main import main as run_bot
from src.sheets.menu_loader import MenuLoader
from src.config import Config

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL вашей таблицы с меню
MENU_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1H3-cLpCqBg4Q6ysp7rDtw-MAFD2tTZh03CbprJlaJ68/edit?usp=sharing'

async def main():
    """Главная функция: загружает меню и запускает бота."""
    logger.info("Starting application...")
    
    # 1. Загрузка меню
    logger.info("Loading menu from Google Sheets...")
    menu_loader = MenuLoader(credentials_path=Config.GOOGLE_CREDENTIALS_PATH, sheet_url=MENU_SHEET_URL)
    menu_data = menu_loader.load_menu()
    
    if not menu_data:
        logger.error("Failed to load menu. Bot cannot start without menu data. Exiting.")
        return

    # Конвертируем меню в JSON-строку для передачи в FSMContext
    menu_json_str = json.dumps(menu_data, ensure_ascii=False)
    
    # 2. Запуск бота с передачей меню
    logger.info("Menu loaded successfully. Starting bot...")
    await run_bot(menu_json_str)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.critical(f"A critical error occurred: {e}")
