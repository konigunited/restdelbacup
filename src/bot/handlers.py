import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from ..gemini.expert import GeminiExpert
from ..sheets.generator import SheetsGenerator
from ..config import Config

logger = logging.getLogger(__name__)

# Словарь для перевода технических терминов на русский язык
TRANSLATIONS = {
    "event_type": "тип мероприятия",
    "guests_count": "количество гостей",
    "event_date": "дата мероприятия",
    "event_time": "время начала",
    "duration_hours": "продолжительность (в часах)",
    "need_service": "необходимость обслуживания",
    "need_equipment": "необходимость доп. оборудования",
    "budget_limit": "бюджет",
    "dietary_restrictions": "диет��ческие ограничения",
    "special_requests": "особые пожелания"
}

class QuoteStates(StatesGroup):
    waiting_for_request = State()
    waiting_for_details = State()
    waiting_for_budget = State()
    confirming_proposal = State()
    editing_proposal = State()

router = Router()

def get_proposal_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все верно, создаем смету!", callback_data="accept_proposal")],
        [InlineKeyboardButton(text="✏️ Внести правки в меню", callback_data="edit_proposal")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])

async def answer_with_fallback(message_or_callback, text, **kwargs):
    try:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, parse_mode="Markdown", **kwargs)
        elif isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.edit_text(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest:
        logger.warning("Markdown parsing failed. Sending as plain text.")
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, **kwargs)
        elif isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.message.answer(text, **kwargs)
            await message_or_callback.message.delete()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🎉 Добро пожаловать! Я ваш личный менеджер Rest Delivery. Опишите ваше мероприятие, и я подготовлю предложение по нашим правилам.")

@router.message(Command("new"))
async def cmd_new_quote(message: Message, state: FSMContext):
    await state.set_state(QuoteStates.waiting_for_request)
    await message.answer("📝 Опишите ваш запрос: количество гостей, дата, бюджет и особые пожелания.")

async def generate_proposal_flow(message: Message, state: FSMContext, menu_json: str):
    processing_msg = await message.answer("🤖 Анализирую запрос и подбираю лучшее предложение...")
    try:
        fsm_data = await state.get_data()
        event_details = fsm_data.get('event_details', {})

        gemini_expert = GeminiExpert(Config.GEMINI_API_KEY)
        proposal_json = await gemini_expert.generate_proposal(event_details, menu_json)

        # Проверяем, что ответ от Gemini не пустой
        if not proposal_json:
            logger.error("Received None from generate_proposal. Aborting flow.")
            await processing_msg.edit_text("❌ Не удалось получить ответ от AI. Пожалуйста, попробуйте еще раз.")
            await state.clear()
            return

        if proposal_json.get("error"):
            await processing_msg.edit_text("❌ Не удалось составить предложение. Возможно, ваш запрос слишком сложный. Попробуйте еще раз.")
            await state.clear()
            return

        await state.update_data(proposal_json=proposal_json)
        formatted_text = gemini_expert.format_proposal_for_telegram(proposal_json)
        
        await processing_msg.delete()
        await answer_with_fallback(message, formatted_text, reply_markup=get_proposal_keyboard())
        await state.set_state(QuoteStates.confirming_proposal)
    except Exception as e:
        logger.error(f"Critical error in generate_proposal_flow: {e}")
        await processing_msg.edit_text("❌ Произошла критическая ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()

@router.message(QuoteStates.waiting_for_request)
async def process_initial_request(message: Message, state: FSMContext, menu_json: str):
    await state.update_data(initial_request=message.text)
    await process_details_flow(message, state, menu_json)

@router.message(QuoteStates.waiting_for_details)
async def process_details(message: Message, state: FSMContext, menu_json: str):
    fsm_data = await state.get_data()
    updated_request = fsm_data.get('initial_request', '') + ". " + message.text
    await state.update_data(initial_request=updated_request)
    await process_details_flow(message, state, menu_json)

async def process_details_flow(message: Message, state: FSMContext, menu_json: str):
    analysis_msg = await message.answer("Анализирую информацию...")
    try:
        fsm_data = await state.get_data()
        request_text = fsm_data.get('initial_request', '')

        gemini_expert = GeminiExpert(Config.GEMINI_API_KEY)
        event_details = await gemini_expert.analyze_request(request_text)
        
        await analysis_msg.delete()

        if event_details.get("error"):
            await message.answer("❌ Не удалось проанализировать ваш запрос. Попробуйте описать его подробнее.")
            return

        await state.update_data(event_details=event_details)

        missing_info = event_details.get('missing_info', [])
        if missing_info:
            # Переводим технические термины на русский
            translated_missing_info = [TRANSLATIONS.get(term, term) for term in missing_info]
            await message.answer(f"Уточните, пожалуйста: {', '.join(translated_missing_info)}?")
            await state.set_state(QuoteStates.waiting_for_details)
            return

        if not event_details.get('budget_limit') or event_details.get('budget_limit') == 0:
            await message.answer("✅ Все основные параметры понятны. Подскажите, пожалуйста, какой у вас ориентировочный бюджет?")
            await state.set_state(QuoteStates.waiting_for_budget)
        else:
            await generate_proposal_flow(message, state, menu_json)

    except Exception as e:
        logger.error(f"Critical error in process_details_flow: {e}")
        await analysis_msg.edit_text("❌ Произошла критическая ошибка. Пожалуйста, попробуйте позже.")
        await state.clear()

@router.message(QuoteStates.waiting_for_budget)
async def process_budget(message: Message, state: FSMContext, menu_json: str):
    budget_text = message.text
    try:
        cleaned_text = ''.join(filter(str.isdigit, budget_text))
        budget = int(cleaned_text)
        
        fsm_data = await state.get_data()
        event_details = fsm_data.get('event_details', {})
        event_details['budget_limit'] = budget
        
        await state.update_data(event_details=event_details)
        await generate_proposal_flow(message, state, menu_json)

    except (ValueError, TypeError):
        await message.answer("Пожалуйста, укажите бюджет цифрами. Например: 35000")
        return

@router.callback_query(F.data == "edit_proposal", QuoteStates.confirming_proposal)
async def edit_proposal_prompt(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✏️ Напишите, что бы вы хотели изменить. Например: «Замените рыбу на курицу и добавьте больше вегетарианских закусок».")
    await state.set_state(QuoteStates.editing_proposal)

@router.message(QuoteStates.editing_proposal)
async def process_proposal_edits(message: Message, state: FSMContext, menu_json: str):
    await message.answer("🔄 Вношу правки и пересчиты��аю предложение...")
    try:
        fsm_data = await state.get_data()
        event_details = fsm_data.get('event_details')
        previous_proposal_json = fsm_data.get('proposal_json')
        user_edits = message.text

        gemini_expert = GeminiExpert(Config.GEMINI_API_KEY)
        
        new_proposal_json = await gemini_expert.generate_proposal(
            event_details=event_details,
            menu_json=menu_json,
            previous_menu=json.dumps(previous_proposal_json, ensure_ascii=False),
            user_edits=user_edits
        )

        if new_proposal_json.get("error"):
            await message.answer("❌ Не удалось обновить предложение. Пожалуйста, попробуйте сформулировать правки иначе.")
            return

        await state.update_data(proposal_json=new_proposal_json)
        formatted_text = gemini_expert.format_proposal_for_telegram(new_proposal_json)
        
        await answer_with_fallback(message, formatted_text, reply_markup=get_proposal_keyboard())
        await state.set_state(QuoteStates.confirming_proposal)

    except Exception as e:
        logger.error(f"Error in process_proposal_edits: {e}")
        await message.answer("❌ Ошибка при обновлении предложения.")

@router.callback_query(F.data == "accept_proposal", QuoteStates.confirming_proposal)
async def accept_proposal_and_create_quote(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✅ Отлично! Фиксируем договоренности и создаю финальную смету в Google Sheets...")
    try:
        fsm_data = await state.get_data()
        analysis_result = fsm_data.get('event_details', {})
        
        sheets_generator = SheetsGenerator(Config.GOOGLE_CREDENTIALS_PATH)
        template_type = sheets_generator.determine_template_type(analysis_result)
        template_id = Config.SIMPLE_TEMPLATE_ID if template_type == 'simple' else Config.COMPLEX_TEMPLATE_ID
        
        pdf_link = await sheets_generator.create_quote_from_template(template_id, analysis_result)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть КП (PDF)", url=pdf_link)],
            [InlineKeyboardButton(text="📊 Создать новую смету", callback_data="new_quote_final")]
        ])
        await callback.message.answer("🎉 Ваше ��оммерческое предложение готово!", reply_markup=keyboard)
        await state.clear()
    except Exception as e:
        logger.error(f"Error in accept_proposal_and_create_quote: {e}")
        await callback.message.edit_text("❌ Произошла ошибка при создании PDF-сметы.")

@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("❌ Операция отменена.")
    await state.clear()

@router.callback_query(F.data == "new_quote_final")
async def new_quote_final_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await cmd_new_quote(callback.message, state)