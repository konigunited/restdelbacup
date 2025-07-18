import logging
import json
from typing import Dict, Optional
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class SheetsGenerator:
    def __init__(self, credentials_path: str):
        self.credentials_path = credentials_path
        with open(self.credentials_path, 'r') as f:
            self.creds_json = json.load(f)
        
        self.credentials = service_account.Credentials.from_service_account_info(
            self.creds_json,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.project_id = self.creds_json['project_id']
        
        self.sheets_service = self._get_service('sheets', 'v4')
        self.drive_service = self._get_service('drive', 'v3')

    def _get_service(self, service_name: str, version: str):
        try:
            service = build(
                service_name, 
                version, 
                credentials=self.credentials.with_quota_project(self.project_id), 
                cache_discovery=False
            )
            logger.info(f"Successfully initialized {service_name} service.")
            return service
        except Exception as e:
            logger.error(f"Failed to initialize {service_name} service: {e}")
            raise

    async def create_quote_from_template(self, template_id: str, order_data: Dict) -> str:
        try:
            quote_name = self._generate_quote_name(order_data)
            
            new_spreadsheet_id = await self._copy_template(template_id, quote_name)
            
            await self._fill_data(new_spreadsheet_id, order_data)
            
            sheet_ids = self._get_sheet_ids(new_spreadsheet_id)

            await self._apply_filters(new_spreadsheet_id, sheet_ids)

            pdf_link = await self._export_to_pdf(new_spreadsheet_id, sheet_ids)
            
            return pdf_link
            
        except Exception as e:
            logger.error(f"Critical error in quote generation process: {e}")
            raise

    async def _copy_template(self, template_id: str, title: str) -> str:
        try:
            copy_request = {
                'name': title,
                'parents': ['1DA2CRtL82fUsojHjW8s-0QfhyHQFZ1Mb']
            }
            copied_file = self.drive_service.files().copy(
                fileId=template_id,
                body=copy_request,
                fields='id'
            ).execute()
            new_id = copied_file['id']
            logger.info(f"Template copied successfully. New spreadsheet ID: {new_id}")
            return new_id
        except HttpError as e:
            logger.error(f"Drive API copy failed: {e}")
            raise

    async def _fill_data(self, spreadsheet_id: str, order_data: Dict):
        try:
            values = [
                [order_data.get('order_number', f"P-{datetime.now().strftime('%Y%m%d%H%M')}")],
                [order_data.get('event_date', '')],
                [order_data.get('event_address', 'Адрес не указан')],
                [order_data.get('event_time', '')],
                [order_data.get('guests_count', 0)]
            ]
            body = {'values': values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Смета!C9:C13',
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            logger.info(f"Successfully filled basic data for spreadsheet: {spreadsheet_id}")
        except HttpError as e:
            logger.error(f"Error filling basic data: {e}")
            raise

    def _get_sheet_ids(self, spreadsheet_id: str) -> Dict[str, int]:
        try:
            spreadsheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            sheets = spreadsheet_metadata.get('sheets', '')
            sheet_ids = {sheet['properties']['title']: sheet['properties']['sheetId'] for sheet in sheets}
            logger.info(f"Retrieved sheet IDs: {sheet_ids}")
            return sheet_ids
        except HttpError as e:
            logger.error(f"Failed to retrieve sheet IDs: {e}")
            return {}

    async def _apply_filters(self, spreadsheet_id: str, sheet_ids: Dict[str, int]):
        requests = []
        
        # 1. Filter for "Смета"
        if 'Смета' in sheet_ids:
            requests.append({
                'setBasicFilter': {
                    'filter': {
                        'range': {
                            'sheetId': sheet_ids['Смета'],
                            'startRowIndex': 33, 'endRowIndex': 449,
                            'startColumnIndex': 0, 'endColumnIndex': 7
                        },
                        'criteria': {
                            # Column C (порций) is not empty
                            2: {'condition': {'type': 'NOT_BLANK'}}
                        }
                    }
                }
            })
            logger.info("Prepared filter for 'Смета' sheet.")

        # 2. Filter for "Банкетка NES"
        if 'Банкетка NES' in sheet_ids:
            requests.append({
                'setBasicFilter': {
                    'filter': {
                        'range': {
                            'sheetId': sheet_ids['Банкетка NES'],
                            'startRowIndex': 27, 'endRowIndex': 74,
                            'startColumnIndex': 0, 'endColumnIndex': 7
                        },
                        'criteria': {
                            # Column F (количество) is not empty
                            5: {'condition': {'type': 'NOT_BLANK'}}
                        }
                    }
                }
            })
            logger.info("Prepared filter for 'Банкетка NES' sheet.")

        # 3. Filter for "Меню фото NEW"
        if 'Меню фото NEW' in sheet_ids:
            requests.append({
                'setBasicFilter': {
                    'filter': {
                        'range': {
                            'sheetId': sheet_ids['Меню фото NEW'],
                            'startRowIndex': 25, 'endRowIndex': 161,
                            'startColumnIndex': 0, 'endColumnIndex': 10
                        },
                        'criteria': {
                            # Column C is not 0
                            2: {'condition': {'type': 'NUMBER_NOT_EQ', 'values': [{'userEnteredValue': '0'}]}}
                        }
                    }
                }
            })
            logger.info("Prepared filter for 'Меню фото NEW' sheet.")

        if requests:
            try:
                body = {'requests': requests}
                self.sheets_service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body=body
                ).execute()
                logger.info(f"Successfully applied all filters to spreadsheet: {spreadsheet_id}")
            except HttpError as e:
                logger.error(f"Error applying filters: {e}")
                # Decide if we should raise or just log
                raise

    async def _is_banquet_sheet_empty(self, spreadsheet_id: str) -> bool:
        try:
            range_to_check = 'Банкетка NES!F28:F74'
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_to_check
            ).execute()
            
            values = result.get('values', [])
            is_empty = not any(row for row in values if row)
            logger.info(f"Is 'Банкетка NES' empty? {is_empty}")
            return is_empty
        except HttpError as e:
            # If sheet or range doesn't exist, treat as empty
            logger.warning(f"Could not check 'Банкетка NES' sheet, assuming it's empty. Error: {e}")
            return True

    async def _export_to_pdf(self, spreadsheet_id: str, sheet_ids: Dict[str, int]) -> str:
        try:
            is_banquet_empty = await self._is_banquet_sheet_empty(spreadsheet_id)
            
            # Base URL for PDF export
            export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=pdf"
            
            # Common PDF export parameters
            params = {
                'format': 'pdf',
                'size': 'a4',
                'portrait': 'false', # Horizontal orientation
                'fitw': 'true', # Align to width
                'top_margin': '0.75',
                'bottom_margin': '0.75',
                'left_margin': '0.7',
                'right_margin': '0.7',
                'gridlines': 'false',
                'printnotes': 'false',
                'pageorder': '1',
                'horizontal_alignment': 'CENTER',
                'vertical_alignment': 'TOP',
                'printtitle': 'false',
                'sheetnames': 'false',
                'fzr': 'false',
                'fzc': 'false'
            }
            
            # Add all sheets by default
            gid_params = [f"gid={gid}" for title, gid in sheet_ids.items() if title != 'Банкетка NES']

            if not is_banquet_empty and 'Банкетка NES' in sheet_ids:
                gid_params.append(f"gid={sheet_ids['Банкетка NES']}")
            
            # Build the final URL
            full_export_url = f"{export_url}&{'&'.join(gid_params)}"
            
            logger.info(f"Generated PDF export link: {full_export_url}")
            return full_export_url

        except Exception as e:
            logger.error(f"Failed to generate PDF export link: {e}")
            # Fallback to returning a link to the sheet itself
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"

    def _generate_quote_name(self, order_data: Dict) -> str:
        try:
            order_number = f"P-{datetime.now().strftime('%Y%m%d%H%M')}"
            event_date = order_data.get('event_date', datetime.now().strftime('%Y-%m-%d'))
            event_type = order_data.get('event_type', 'мероприятие')
            guests = order_data.get('guests_count', 0)
            return f"{order_number}_Смета_{event_type}_{guests}гост_{event_date}"
        except Exception as e:
            logger.error(f"Error generating quote name: {e}")
            return f"Смета_{datetime.now().strftime('%Y%m%d_%H%M')}"

    def determine_template_type(self, order_data: Dict) -> str:
        """Определяет тип шаблона на основе данных заказа."""
        # По вашей просьбе, временно отключаю сложный шаблон.
        # Теперь для всех заказов будет использоваться 'simple'.
        logger.info("Forcing 'simple' template as requested.")
        return 'simple'

        # Код ниже сохранен, чтобы его можно было легко вернуть:
        # event_type = order_data.get('event_type', '').lower()
        
        # # Гибкая проверка на "кофе-брейк"
        # if 'кофе' in event_type and 'брейк' in event_type:
        #     logger.info(f"Determined template type as 'simple' for event: {event_type}")
        #     return 'simple'
        # else:
        #     logger.info(f"Determined template type as 'complex' for event: {event_type}")
        #     return 'complex'
