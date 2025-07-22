import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold, GenerationConfig
from .prompts import SYSTEM_PROMPT, MENU_GENERATION_PROMPT

logger = logging.getLogger(__name__)

class GeminiExpert:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        generation_config = GenerationConfig(response_mime_type="application/json")

        self.analysis_model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        self.proposal_model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.info("Using Gemini model: gemini-2.5-pro with custom safety settings.")

    async def analyze_request(self, text: str) -> Dict[str, Any]:
        try:
            logger.info(f"Analyzing request: {text[:100]}...")
            response = await self.analysis_model.generate_content_async(f"Проанализируй запрос клиента: {text}")
            
            if not response.parts:
                logger.error("Analysis response is empty. Finish reason: %s", response.prompt_feedback)
                return {"error": "Failed to analyze request due to empty response."}
            
            raw_text = response.text
            # Очищаем ответ от лишних символов и Markdown-оберток
            cleaned_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()
            
            return json.loads(cleaned_text)
        except Exception as e:
            logger.error(f"Error in analyze_request: {str(e)}")
            logger.error(f"Failed to parse JSON from analyze_request: {response.text}")
            return {"error": "Failed to analyze request."}

    async def generate_proposal(
        self,
        event_details: Dict[str, Any],
        menu_json: str,
        previous_menu: str = "",
        user_edits: str = ""
    ) -> Dict[str, Any]:
        response = None  # Инициализируем переменную заранее
        try:
            logger.info("Generating full proposal...")
            
            # Экранируем фигурные скобки в JSON-данных, чтобы избежать конфликтов с .format()
            safe_event_details = json.dumps(event_details, ensure_ascii=False).replace("{", "{{").replace("}", "}}")
            safe_menu_json = menu_json.replace("{", "{{").replace("}", "}}")
            safe_previous_menu = previous_menu.replace("{", "{{").replace("}", "}}")

            prompt = MENU_GENERATION_PROMPT.format(
                event_details=safe_event_details,
                menu_json=safe_menu_json,
                previous_menu=safe_previous_menu,
                user_edits=user_edits
            )
            
            logger.info(f"Generated prompt size: {len(prompt)} characters.")
            response = await self.proposal_model.generate_content_async(prompt)

            # --- Улучшенная диагностика ---
            if not response.parts:
                logger.error("Proposal response is empty! Finish reason: %s", response.prompt_feedback)
                # Записываем в файл причину, даже если ответ пустой
                with open("gemini_error_feedback.txt", "w", encoding="utf-8") as f:
                    f.write(str(response.prompt_feedback))
                return {"error": "Failed to generate proposal due to an empty or blocked response."}
            
            raw_text = response.text
            # Если ответ не пустой, записываем его для анализа
            with open("gemini_raw_response.txt", "w", encoding="utf-8") as f:
                f.write(raw_text)
            # --- Конец диагностики ---

            # Очищаем ответ от лишних символов и Markdown-оберток
            cleaned_text = raw_text.strip().removeprefix("```json").removesuffix("```").strip()

            return json.loads(cleaned_text)
        except Exception as e:
            logger.error(f"Critical error in generate_proposal: {str(e)}", exc_info=True) # Добавляем exc_info=True
            if response:
                logger.error(f"Failed to parse JSON from generate_proposal: {response.text}")
            else:
                logger.error("Failed to get a response from Gemini API. The request itself may have failed.")
            return {"error": "Failed to generate proposal."}

    @staticmethod
    def format_proposal_for_telegram(proposal_json: Dict[str, Any]) -> str:
        if not proposal_json or "error" in proposal_json:
            return "К сожалению, не удалось составить предложение. Попробуйте еще раз."

        def escape_markdown(text: str) -> str:
            """Экранирует специальные символы Markdown."""
            if not isinstance(text, str):
                return ""
            # Основные символы, которые могут вызвать проблемы в нашем форматировании
            escape_chars = r'[_*`'
            return ''.join(f'\{char}' if char in escape_chars else char for char in text)

        text = escape_markdown(proposal_json.get("proposal_text", "Ваше предложение по меню готово:"))
        text += "\n\n"

        for category in proposal_json.get("menu_items", []):
            category_name = escape_markdown(category.get('category', 'Категория'))
            text += f"*{category_name}*\n"
            for item in category.get("items", []):
                name = escape_markdown(item.get('name'))
                weight = escape_markdown(str(item.get('weight', 'N/A')))
                price = item.get('price_per_item', 0)
                quantity = item.get('quantity', 0)
                text += f"- {name} ({weight}, {price} руб.) x {quantity} шт.\n"
            text += "\n"

        summary = proposal_json.get("summary") or {}
        text += f"*Итого по меню:*\n"
        text += f"- На одного гостя: ~{summary.get('price_per_guest', 0)} руб.\n"
        text += f"- Общая граммовка на гостя: {summary.get('weight_per_guest_grams', 0)}г\n"
        text += f"- Общая стоимость меню: {summary.get('total_menu_price', 0)} руб.\n\n"

        service = proposal_json.get("service_calculation") or {}
        if service and service.get("total_service_cost", 0) > 0:
            service_details = escape_markdown(service.get('service_details', 'Детали не указаны.'))
            text += "*Расчет обслуживания:*\n"
            text += f"{service_details}\n"
            text += f"Итого за обслуживание: {service.get('total_service_cost', 0)} руб.\n\n"

        warnings = proposal_json.get("warnings") or []
        if warnings:
            text += "*Важные моменты:*\n"
            for warning in warnings:
                text += f"- {escape_markdown(warning)}\n"
        
        return text