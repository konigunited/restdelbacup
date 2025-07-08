"""
PDF generation and manipulation service
"""
import asyncio
import aiofiles
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from src.services.sheets_service import sheets_service
from src.utils.logger import logger

class PDFService:
    """Сервис для работы с PDF файлами смет"""
    
    def __init__(self):
        self.output_dir = Path("output/pdfs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._pdf_cache = {}
        self._cleanup_interval = 3600  # 1 час
    
    async def generate_pdf_from_sheet(self, sheet_id: str, order_number: str) -> Optional[str]:
        """Генерация PDF из Google Sheets"""
        
        try:
            logger.info(f"Generating PDF from sheet | sheet_id={sheet_id}, order_number={order_number}")
            
            # Проверяем кэш
            cache_key = f"{sheet_id}_{order_number}"
            if cache_key in self._pdf_cache:
                cached_path = self._pdf_cache[cache_key]["path"]
                if Path(cached_path).exists():
                    logger.info(f"PDF found in cache | path={cached_path}")
                    return cached_path
            
            # Получаем PDF от Google Sheets
            pdf_content = await sheets_service.export_to_pdf(sheet_id)
            
            if not pdf_content:
                logger.error("Failed to get PDF content from sheets")
                return None
            
            # Сохраняем PDF файл
            pdf_filename = f"estimate_{order_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = self.output_dir / pdf_filename
            
            async with aiofiles.open(pdf_path, 'wb') as f:
                await f.write(pdf_content)
            
            # Добавляем в кэш
            self._pdf_cache[cache_key] = {
                "path": str(pdf_path),
                "created_at": datetime.now(),
                "size": len(pdf_content)
            }
            
            logger.info(f"PDF generated successfully | order_number={order_number}, pdf_path={pdf_path}, file_size={len(pdf_content)}")
            
            return str(pdf_path)
            
        except Exception as e:
            logger.error(f"PDF generation failed | sheet_id={sheet_id}, order_number={order_number}, error={str(e)}")
            return None
    
    async def get_pdf_content(self, pdf_path: str) -> Optional[bytes]:
        """Получение содержимого PDF файла"""
        
        try:
            path = Path(pdf_path)
            if not path.exists():
                logger.error(f"PDF file not found | path={pdf_path}")
                return None
            
            async with aiofiles.open(path, 'rb') as f:
                content = await f.read()
            
            logger.info(f"PDF content retrieved | path={pdf_path}, size={len(content)}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read PDF file | path={pdf_path}, error={str(e)}")
            return None
    
    async def create_combined_pdf(self, sheet_ids: List[str], output_name: str) -> Optional[str]:
        """Создание объединенного PDF из нескольких смет"""
        
        try:
            logger.info(f"Creating combined PDF | sheet_count={len(sheet_ids)}")
            
            # Генерируем PDF для каждой сметы
            pdf_contents = []
            for sheet_id in sheet_ids:
                pdf_content = await sheets_service.export_to_pdf(sheet_id)
                if pdf_content:
                    pdf_contents.append(pdf_content)
            
            if not pdf_contents:
                logger.error("No PDF content generated for combined PDF")
                return None
            
            # Простое объединение (в реальном проекте использовать PyPDF2 или similar)
            combined_filename = f"combined_{output_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            combined_path = self.output_dir / combined_filename
            
            # Пока просто сохраняем первый PDF (для демо)
            async with aiofiles.open(combined_path, 'wb') as f:
                await f.write(pdf_contents[0])
            
            logger.info(f"Combined PDF created | path={combined_path}")
            return str(combined_path)
            
        except Exception as e:
            logger.error(f"Combined PDF creation failed | error={str(e)}")
            return None
    
    def cleanup_old_pdfs(self, days_old: int = 30):
        """Очистка старых PDF файлов"""
        
        try:
            current_time = datetime.now()
            removed_count = 0
            
            for pdf_file in self.output_dir.glob("*.pdf"):
                file_time = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                if (current_time - file_time).days > days_old:
                    pdf_file.unlink()
                    removed_count += 1
            
            # Очищаем кэш от удаленных файлов
            keys_to_remove = []
            for key, info in self._pdf_cache.items():
                if not Path(info["path"]).exists():
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._pdf_cache[key]
            
            logger.info(f"PDF cleanup completed | removed_files={removed_count}, cache_cleaned={len(keys_to_remove)}")
            
        except Exception as e:
            logger.error(f"PDF cleanup failed | error={str(e)}")
    
    async def get_pdf_metadata(self, pdf_path: str) -> Dict[str, Any]:
        """Получение метаданных PDF файла"""
        
        try:
            path = Path(pdf_path)
            if not path.exists():
                return {}
            
            stat = path.stat()
            
            metadata = {
                "filename": path.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "exists": True
            }
            
            # Добавляем информацию из кэша если есть
            for cache_info in self._pdf_cache.values():
                if cache_info["path"] == str(path):
                    metadata.update({
                        "cached": True,
                        "cache_created": cache_info["created_at"].isoformat()
                    })
                    break
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get PDF metadata | path={pdf_path}, error={str(e)}")
            return {"exists": False, "error": str(e)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Статистика PDF сервиса"""
        
        total_files = len(list(self.output_dir.glob("*.pdf")))
        total_size = sum(f.stat().st_size for f in self.output_dir.glob("*.pdf"))
        
        return {
            "output_directory": str(self.output_dir),
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_entries": len(self._pdf_cache),
            "cache_keys": list(self._pdf_cache.keys())
        }

# Глобальный экземпляр сервиса
pdf_service = PDFService()
