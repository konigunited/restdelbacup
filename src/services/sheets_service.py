"""
High-performance Google Sheets integration service - FIXED
"""
import asyncio
import json
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import gspread_asyncio
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import aiohttp
from datetime import datetime
from src.utils.logger import logger

class GoogleSheetsService:
    """Высокопроизводительный сервис для работы с Google Sheets"""
    
    def __init__(self):
        self.credentials = None
        self.service = None
        self.agcm = None
        self.template_id = "1poO2idpiXsC8kN5C3EuuXycyPGQU-LWy1t7Mzs6dEtM"
        self._initialized = False
        self._cache = {}
    
    async def initialize(self):
        """Инициализация сервиса с проверкой доступов"""
        try:
            logger.info("Initializing Google Sheets Service")
            
            # Загрузка credentials
            creds_path = Path("config/google_credentials.json")
            if not creds_path.exists():
                raise FileNotFoundError(f"Google credentials not found: {creds_path}")
            
            # Создание credentials для gspread-asyncio
            def get_creds():
                return Credentials.from_service_account_file(
                    str(creds_path),
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
            
            self.agcm = gspread_asyncio.AsyncioGspreadClientManager(get_creds)
            
            # Создание синхронного сервиса для некоторых операций
            self.credentials = get_creds()
            self.service = build('sheets', 'v4', credentials=self.credentials)
            
            # Создание Drive API для копирования файлов
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            
            # Проверка доступа к шаблону
            await self._verify_template_access()
            
            self._initialized = True
            logger.info("Google Sheets Service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Google Sheets Service", error=str(e))
            raise
    
    async def _verify_template_access(self):
        """Проверка доступа к шаблону"""
        try:
            agc = await self.agcm.authorize()
            template = await agc.open_by_key(self.template_id)
            worksheets = await template.worksheets()
            
            sheet_names = [ws.title for ws in worksheets]
            logger.info("Template access verified", 
                       template_id=self.template_id,
                       sheets=sheet_names)
            
            return True
            
        except Exception as e:
            logger.error("Template access verification failed", 
                        template_id=self.template_id,
                        error=str(e))
            raise
    
    async def create_estimate_sheet(self, estimate_data: Dict[str, Any]) -> Tuple[str, str]:
        """Создание новой сметы на основе шаблона"""
        
        if not self._initialized:
            await self.initialize()
        
        order_number = estimate_data.get("order_info", {}).get("number", "P-00000")
        logger.info("Creating estimate sheet", order_number=order_number)
        
        try:
            # Создание копии с использованием Drive API (синхронно)
            new_sheet_title = f"Смета {order_number} - {datetime.now().strftime('%d.%m.%Y')}"
            
            # Копируем файл через Drive API
            copied_file = self.drive_service.files().copy(
                fileId=self.template_id,
                body={'name': new_sheet_title}
            ).execute()
            
            new_sheet_id = copied_file['id']
            logger.info("Template copied via Drive API", 
                       new_sheet_id=new_sheet_id,
                       title=new_sheet_title)
            
            # Теперь открываем скопированный файл через gspread для заполнения
            agc = await self.agcm.authorize()
            new_sheet = await agc.open_by_key(new_sheet_id)
            
            # Заполнение данными
            await self._fill_estimate_data(new_sheet, estimate_data)
            
            # Создание публичной ссылки
            share_url = await self._create_public_link(new_sheet_id)
            
            logger.info("Estimate sheet created successfully",
                       order_number=order_number,
                       sheet_id=new_sheet_id,
                       url=share_url)
            
            return new_sheet_id, share_url
            
        except Exception as e:
            logger.error("Failed to create estimate sheet",
                        order_number=order_number,
                        error=str(e))
            raise
    
    async def _fill_estimate_data(self, sheet, estimate_data: Dict[str, Any]):
        """Заполнение данных в созданной смете"""
        
        try:
            # Получаем все листы
            worksheets = await sheet.worksheets()
            sheets_dict = {ws.title: ws for ws in worksheets}
            
            # Заполняем лист "Смета"
            if "Смета" in sheets_dict:
                await self._fill_main_estimate(sheets_dict["Смета"], estimate_data)
            
            # Заполняем лист "Банкетка NES" если есть услуги
            banquet_sheet_name = "Банкетка NES" if "Банкетка NES" in sheets_dict else "Банкетка"
            if banquet_sheet_name in sheets_dict and estimate_data.get("services"):
                await self._fill_services_sheet(sheets_dict[banquet_sheet_name], estimate_data)
            
            logger.info("Estimate data filled successfully")
            
        except Exception as e:
            logger.error("Failed to fill estimate data", error=str(e))
            raise
    
    async def _fill_main_estimate(self, worksheet, estimate_data: Dict[str, Any]):
        """Заполнение основного листа сметы"""
        
        order_info = estimate_data.get("order_info", {})
        menu_items = estimate_data.get("menu_items", [])
        totals = estimate_data.get("totals", {})
        
        # Обновления для основной информации
        updates = []
        
        # Информация о заказе (примерные ячейки, может потребоваться корректировка)
        if order_info.get("number"):
            updates.append({
                'range': 'B2',
                'values': [[order_info["number"]]]
            })
        
        if order_info.get("date"):
            updates.append({
                'range': 'B3', 
                'values': [[order_info["date"]]]
            })
        
        if order_info.get("guests"):
            updates.append({
                'range': 'B4',
                'values': [[order_info["guests"]]]
            })
        
        # Тип мероприятия
        if order_info.get("event_type"):
            updates.append({
                'range': 'B5',
                'values': [[order_info["event_type"]]]
            })
        
        # Меню позиции (начиная с строки 8, примерно)
        if menu_items:
            menu_rows = []
            for item in menu_items:
                menu_rows.append([
                    item.get("name", ""),
                    item.get("quantity", 0),
                    f"{item.get('weight_per_set', 0)}г",
                    f"{item.get('price_per_set', 0)}₽",
                    f"{item.get('total_weight', 0)}г",
                    f"{item.get('total_price', 0):,}₽"
                ])
            
            if menu_rows:
                updates.append({
                    'range': f'A8:F{7+len(menu_rows)}',
                    'values': menu_rows
                })
        
        # Итоги (примерное расположение)
        if totals:
            total_cost = totals.get("total_cost", 0)
            total_weight = totals.get("total_weight", 0)
            
            updates.append({
                'range': 'F50',
                'values': [[f"{total_cost:,}₽"]]
            })
            
            updates.append({
                'range': 'E51',
                'values': [[f"{total_weight}г"]]
            })
        
        # Применяем все обновления batch-операцией
        if updates:
            await self._batch_update_worksheet(worksheet, updates)
    
    async def _fill_services_sheet(self, worksheet, estimate_data: Dict[str, Any]):
        """Заполнение листа услуг обслуживания"""
        
        services = estimate_data.get("services", [])
        
        if not services:
            return
        
        # Услуги обслуживания
        service_rows = []
        for service in services:
            service_rows.append([
                service.get("name", ""),
                service.get("description", ""),
                service.get("quantity", 0),
                service.get("unit", "шт"),
                f"{service.get('price_per_unit', 0):,}₽",
                f"{service.get('total_price', 0):,}₽"
            ])
        
        if service_rows:
            updates = [{
                'range': f'A7:F{6+len(service_rows)}',
                'values': service_rows
            }]
            
            await self._batch_update_worksheet(worksheet, updates)
    
    async def _batch_update_worksheet(self, worksheet, updates: List[Dict]):
        """Batch обновление ячеек worksheet"""
        
        try:
            # Конвертируем в формат для batch_update
            batch_data = []
            for update in updates:
                batch_data.append({
                    'range': update['range'],
                    'values': update['values']
                })
            
            # Выполняем batch update
            await worksheet.batch_update(batch_data, value_input_option='USER_ENTERED')
            
            logger.info("Batch update completed", updates_count=len(updates))
            
        except Exception as e:
            logger.error("Batch update failed", error=str(e))
            # Не прерываем процесс, если не удалось заполнить данные
            logger.warning("Continuing with empty sheet")
    
    async def _create_public_link(self, sheet_id: str) -> str:
        """Создание публичной ссылки на смету"""
        
        try:
            # Делаем файл доступным для просмотра по ссылке
            permission = {
                'type': 'anyone',
                'role': 'reader'
            }
            
            self.drive_service.permissions().create(
                fileId=sheet_id,
                body=permission
            ).execute()
            
            share_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit?usp=sharing"
            return share_url
            
        except Exception as e:
            logger.error("Failed to create public link", sheet_id=sheet_id, error=str(e))
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
    
    async def update_estimate_sheet(self, sheet_id: str, updates: Dict[str, Any]) -> bool:
        """Обновление существующей сметы"""
        
        try:
            agc = await self.agcm.authorize()
            sheet = await agc.open_by_key(sheet_id)
            
            # Применяем обновления
            await self._fill_estimate_data(sheet, updates)
            
            logger.info("Estimate sheet updated", sheet_id=sheet_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update estimate sheet", 
                        sheet_id=sheet_id, 
                        error=str(e))
            return False
    
    async def get_estimate_data(self, sheet_id: str) -> Dict[str, Any]:
        """Получение данных из существующей сметы"""
        
        try:
            agc = await self.agcm.authorize()
            sheet = await agc.open_by_key(sheet_id)
            
            # Получаем основные данные
            main_sheet = await sheet.worksheet("Смета")
            all_values = await main_sheet.get_all_values()
            
            # Простой парсинг
            estimate_data = {
                "sheet_id": sheet_id,
                "title": sheet.title,
                "data": all_values[:10],  # Первые 10 строк
                "order_number": all_values[1][1] if len(all_values) > 1 and len(all_values[1]) > 1 else "Unknown",
                "retrieved_at": datetime.now().isoformat()
            }
            
            return estimate_data
            
        except Exception as e:
            logger.error("Failed to get estimate data", 
                        sheet_id=sheet_id,
                        error=str(e))
            return {"sheet_id": sheet_id, "error": str(e)}
    
    async def export_to_pdf(self, sheet_id: str) -> Optional[bytes]:
        """Экспорт сметы в PDF"""
        
        try:
            # URL для экспорта в PDF
            pdf_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=pdf&portrait=false&size=A4&gid=0"
            
            # Обновляем токен если нужно
            if hasattr(self.credentials, 'expired') and self.credentials.expired:
                self.credentials.refresh()
            
            # Получаем PDF через HTTP запрос с авторизацией
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Authorization': f'Bearer {self.credentials.token}'
                }
                
                async with session.get(pdf_url, headers=headers) as response:
                    if response.status == 200:
                        pdf_content = await response.read()
                        logger.info("PDF export successful", 
                                   sheet_id=sheet_id,
                                   size=len(pdf_content))
                        return pdf_content
                    else:
                        logger.error("PDF export failed", 
                                   sheet_id=sheet_id,
                                   status=response.status)
                        return None
            
        except Exception as e:
            logger.error("PDF export error", sheet_id=sheet_id, error=str(e))
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика использования сервиса"""
        return {
            "initialized": self._initialized,
            "template_id": self.template_id,
            "service_account": self.credentials.service_account_email if self.credentials else None,
            "status": "ready" if self._initialized else "not_initialized",
            "cache_size": len(self._cache),
            "has_drive_service": hasattr(self, 'drive_service')
        }

# Глобальный экземпляр сервиса
sheets_service = GoogleSheetsService()