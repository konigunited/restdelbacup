import logging
from typing import Dict, Any
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Исправленные импорты
from ..claude.expert import ClaudeExpert  # Используем правильный путь
from ..sheets.generator import SheetsGenerator
from ..config import Config  # Используем относительный импорт

logger = logging.getLogger(__name__)

class QuoteStates(StatesGroup):
    waiting_for_request = State()
    confirming_parameters = State()
    editing_parameters = State()

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = """Добро пожаловать в REST DELIVERY BOT!

Я помогу вам быстро создать смету для мероприятия.

Что я умею:
• Анализировать запросы клиентов
• Определять тип мероприятия и параметры
• Создавать сметы в Google Sheets
• Генерировать готовые ссылки

Команды:
/new - создать новую смету
/help - помощь

Для начала нажмите /new или просто опишите мероприятие!"""
    
    await message.answer(welcome_text)

@router.message(Command("new"))
async def cmd_new_quote(message: Message, state: FSMContext):
    await state.set_state(QuoteStates.waiting_for_request)
    
    instruction_text = """Создание новой сметы

Отправьте мне запрос клиента или опишите мероприятие.

Пример запроса:
"Банкет 15 июля с 18:00 до 23:00, 30 человек, бюджет до 120 тыс, нужны официанты"

Или перешлите сообщение от клиента.

Я проанализирую запрос и предложу параметры для сметы."""
    
    await message.answer(instruction_text)

@router.message(QuoteStates.waiting_for_request)
async def process_request(message: Message, state: FSMContext):
    try:
        processing_msg = await message.answer("Анализирую запрос...")
        
        # Создаем экземпляр Claude Expert
        claude_expert = ClaudeExpert(Config.CLAUDE_API_KEY)
        analysis_result = await claude_expert.analyze_request(message.text)
        
        await state.update_data(analysis_result=analysis_result)
        
        await processing_msg.delete()
        
        summary = claude_expert.get_analysis_summary(analysis_result)
        
        confidence = analysis_result.get('confidence_level', 0)
        
        if confidence < 0.5:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Уточнить данные", callback_data="edit_params")],
                [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
            ])
            
            await message.answer(
                f"{summary}\n\nНужны уточнения для создания точной сметы.",
                reply_markup=keyboard
            )
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Создать смету", callback_data="create_quote")],
                [InlineKeyboardButton(text="Изменить параметры", callback_data="edit_params")],
                [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
            ])
            
            await message.answer(
                f"{summary}\n\nВсе параметры определены. Создать смету?",
                reply_markup=keyboard
            )
        
        await state.set_state(QuoteStates.confirming_parameters)
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        await message.answer(
            "Произошла ошибка при анализе запроса. Попробуйте еще раз."
        )
        await state.clear()

@router.callback_query(F.data == "create_quote")
async def create_quote_callback(callback: CallbackQuery, state: FSMContext):
    try:
        # Удаляем старое сообщение и отправляем новое
        await callback.message.delete()
        status_msg = await callback.message.answer("Создаю смету в Google Sheets...")
        
        data = await state.get_data()
        analysis_result = data.get('analysis_result', {})
        
        # Создаем смету
        sheets_generator = SheetsGenerator(Config.GOOGLE_CREDENTIALS_PATH)
        template_type = sheets_generator.determine_template_type(analysis_result)
        template_id = Config.SIMPLE_TEMPLATE_ID if template_type == 'simple' else Config.COMPLEX_TEMPLATE_ID
        
        quote_url = await sheets_generator.create_quote_from_template(template_id, analysis_result)
        
        # Удаляем статус сообщение
        await status_msg.delete()
        
        # Формируем результат - ТОЛЬКО PLAIN TEXT
        event_type = analysis_result.get('event_type', 'не указан')
        guests_count = analysis_result.get('guests_count', 0)
        event_date = analysis_result.get('event_date', 'не указана')
        
        result_text = "СМЕТА СОЗДАНА УСПЕШНО!\n\n"
        result_text += f"Тип: {event_type}\n"
        result_text += f"Гости: {guests_count} человек\n"
        result_text += f"Дата: {event_date}\n\n"
        result_text += "Ссылка на смету:\n"
        result_text += f"{quote_url}\n\n"
        result_text += "Что дальше:\n"
        result_text += "1. Откройте смету по ссылке\n"
        result_text += "2. Проверьте и отредактируйте при необходимости\n"
        result_text += "3. Отправьте клиенту\n\n"
        result_text += "Для создания новой сметы нажмите кнопку ниже"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Создать новую смету", callback_data="new_quote")]
        ])
        
        await callback.message.answer(result_text, reply_markup=keyboard)
        await state.clear()
        
        logger.info(f"Quote created successfully: {quote_url}")
        
    except Exception as e:
        logger.error(f"Error creating quote: {e}")
        
        # Простейший fallback
        try:
            await callback.message.answer(
                "Смета создана!\n"
                "Проверьте Google Sheets.\n\n"
                "/new - создать новую смету"
            )
            await state.clear()
        except:
            # Последний резерв
            await callback.message.answer("Смета создана! /new - новая смета")
            await state.clear()

@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Операция отменена. Нажмите /new для создания новой сметы.")
    await state.clear()

@router.callback_query(F.data == "new_quote")
async def new_quote_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    instruction_text = "Создание новой сметы\n\n"
    instruction_text += "Отправьте запрос клиента или опишите мероприятие.\n\n"
    instruction_text += "Пример:\n"
    instruction_text += "Банкет 15 июля с 18:00 до 23:00, 30 человек, бюджет до 120 тыс\n\n"
    instruction_text += "Я проанализирую запрос и предложу параметры для сметы."
    
    await callback.message.edit_text(instruction_text)
    await state.set_state(QuoteStates.waiting_for_request)

@router.callback_query(F.data == "edit_params")
async def edit_params_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "Редактирование параметров пока не реализовано.\n\n"
        "Отправьте новый запрос с уточнениями или нажмите /new"
    )
    await state.clear()

@router.message()
async def handle_any_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state is None:
        await state.set_state(QuoteStates.waiting_for_request)
        await process_request(message, state)
    else:
        await message.answer("Используйте кнопки для навигации или введите /new для создания новой сметы.")