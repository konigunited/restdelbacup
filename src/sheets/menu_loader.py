import gspread
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class MenuLoader:
    def __init__(self, credentials_path: str, sheet_url: str):
        self.credentials_path = credentials_path
        self.sheet_url = sheet_url
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self.creds = Credentials.from_service_account_file(self.credentials_path, scopes=self.scopes)
        self.client = gspread.authorize(self.creds)

    def load_menu(self) -> list[dict]:
        """Загружает все меню из всех листов Google-таблицы."""
        try:
            logger.info(f"Connecting to Google Sheet: {self.sheet_url}")
            spreadsheet = self.client.open_by_url(self.sheet_url)
            worksheets = spreadsheet.worksheets()
            
            full_menu = []
            
            for ws in worksheets:
                logger.info(f"Reading sheet: {ws.title}")
                # get_all_records предполагает, что первая строка - это заголовки
                records = ws.get_all_records()
                
                # Добавляем категорию из названия листа
                for record in records:
                    record['Категория'] = ws.title
                
                full_menu.extend(records)
            
            logger.info(f"Successfully loaded {len(full_menu)} menu items from {len(worksheets)} sheets.")
            return full_menu

        except gspread.exceptions.SpreadsheetNotFound:
            logger.error("Spreadsheet not found. Check the URL and share settings.")
            return []
        except Exception as e:
            logger.error(f"An error occurred while loading the menu: {e}")
            return []

# Пример использования (для отладки)
if __name__ == '__main__':
    # Укажите путь к вашим credentials и URL таблицы
    creds_path = 'credentials.json'
    sheet_url = 'https://docs.google.com/spreadsheets/d/1H3-cLpCqBg4Q6ysp7rDtw-MAFD2tTZh03CbprJlaJ68/edit?usp=sharing'
    
    loader = MenuLoader(credentials_path=creds_path, sheet_url=sheet_url)
    menu = loader.load_menu()
    
    if menu:
        import json
        # Выводим первые 5 позиций для проверки
        print(json.dumps(menu[:5], indent=2, ensure_ascii=False))
