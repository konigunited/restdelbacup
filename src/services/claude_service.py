"""
High-performance Claude API integration with retry logic
"""
import asyncio
import aiohttp
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from anthropic import AsyncAnthropic
from src.utils.logger import logger
from config.settings import settings

@dataclass
class ClaudeMessage:
    """Структура сообщения для Claude"""
    role: str  # 'user' or 'assistant'
    content: str

@dataclass
class ClaudeResponse:
    """Структура ответа от Claude"""
    content: str
    usage: Dict[str, int]
    model: str
    stop_reason: str

def extract_json_from_response(response_text: str) -> dict:
    """Извлечение JSON из ответа Claude, даже если он в markdown блоке"""
    
    # Убираем markdown блоки если есть
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        json_text = json_match.group(1)
    else:
        # Ищем JSON в тексте
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
        else:
            json_text = response_text
    
    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        # Если не удалось распарсить, возвращаем ошибку с исходным текстом
        raise ValueError(f"Failed to parse JSON: {e}. Original text: {response_text[:200]}...")

class ClaudeService:
    """Высокопроизводительный сервис для работы с Claude API"""
    
    def __init__(self):
        self.client = AsyncAnthropic(
            api_key=settings.CLAUDE_API_KEY,
            timeout=settings.CLAUDE_TIMEOUT
        )
        self._request_count = 0
        self._error_count = 0
    
    async def send_message(
        self,
        system_prompt: str,
        user_message: str,
        context: Optional[List[ClaudeMessage]] = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> ClaudeResponse:
        """Отправка сообщения Claude с retry логикой"""
        
        temperature = temperature or settings.CLAUDE_TEMPERATURE
        max_tokens = max_tokens or settings.CLAUDE_MAX_TOKENS
        
        messages = []
        
        # Добавляем контекст если есть
        if context:
            for msg in context:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                self._request_count += 1
                
                logger.info(f"Sending message to Claude | request_id={self._request_count}, model={settings.CLAUDE_MODEL}, temperature={temperature}, max_tokens={max_tokens}, message_length={len(user_message)}")
                
                response = await self.client.messages.create(
                    model=settings.CLAUDE_MODEL,
                    system=system_prompt,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                logger.info(f"Claude response received | request_id={self._request_count}, usage={response.usage.dict()}, stop_reason={response.stop_reason}")
                
                return ClaudeResponse(
                    content=response.content[0].text,
                    usage=response.usage.dict(),
                    model=response.model,
                    stop_reason=response.stop_reason
                )
                
            except Exception as e:
                retry_count += 1
                self._error_count += 1
                
                logger.error(f"Claude API error | request_id={self._request_count}, retry_count={retry_count}, error={str(e)}, error_type={type(e).__name__}")
                
                if retry_count >= max_retries:
                    raise Exception(f"Claude API failed after {max_retries} retries: {str(e)}")
                
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
    
    async def send_structured_request(
        self,
        system_prompt: str,
        user_message: str,
        expected_format: str = "json",
        context: Optional[List[ClaudeMessage]] = None
    ) -> Dict[str, Any]:
        """Отправка структурированного запроса с улучшенным парсингом JSON"""
        
        # Улучшаем промпт для более надежного JSON
        enhanced_user_message = f"""
{user_message}

ВАЖНО: Ответь СТРОГО в формате {expected_format.upper()}.
Не используй markdown блоки ```json``` - только чистый JSON.
Проверь валидность JSON перед отправкой.
"""
        
        try:
            response = await self.send_message(
                system_prompt=system_prompt,
                user_message=enhanced_user_message,
                context=context
            )
            
            # Извлекаем JSON с улучшенным парсингом
            return extract_json_from_response(response.content)
            
        except Exception as e:
            logger.error("Structured request failed", error=str(e))
            # Возвращаем базовую структуру при ошибке
            return {
                "error": str(e),
                "fallback": True,
                "original_response": response.content if 'response' in locals() else "No response"
            }
    
    def get_stats(self) -> Dict[str, int]:
        """Получить статистику использования API"""
        return {
            "total_requests": self._request_count,
            "error_count": self._error_count,
            "success_rate": (self._request_count - self._error_count) / max(1, self._request_count) * 100
        }

# Глобальный экземпляр сервиса
claude_service = ClaudeService()