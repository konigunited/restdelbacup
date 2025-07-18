import logging
import json
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from ..gemini.expert import GeminiExpert
from ..sheets.generator import SheetsGenerator
from ..config import Config

logger = logging.getLogger(__name__)

# --- Состояния FSM ---
class QuoteStates(StatesGroup):
    waiting_for_request = State()
    confirming_proposal = State()
    editing_proposal = State()

router = Router()

# --- Клавиатуры ---
def get_main_menu_keyboard():
    """Возвращает клавиатуру главного меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Создать смету", callback_data="start_new_quote")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="show_help")],
        [InlineKeyboardButton(text="📖 Посмотреть меню", url="https://restdelivery.ru/menu/")]
    ])

def get_proposal_keyboard():
    """Возвращает клавиатуру для взаимодействия с готовым предложением."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Все верно, создаем смету!", callback_data="accept_proposal")],
        [InlineKeyboardButton(text="✏️ Внести правки", callback_data="edit_proposal")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")]
    ])

# --- Вспомогательные функции ---
async def answer_with_fallback(message_or_callback, text, **kwargs):
    """Безопасно отправляет или редактирует сообщение, избегая падений."""
    try:
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, parse_mode="Markdown", **kwargs)
        elif isinstance(message_or_callback, CallbackQuery):
            await message_or_callback.answer()
            await message_or_callback.message.edit_text(text, parse_mode="Markdown", **kwargs)
    except TelegramBadRequest as e:
        logger.warning(f"Failed to send/edit message with Markdown: {e}. Sending as plain text.")
        current_message = message_or_callback.message if isinstance(message_or_callback, CallbackQuery) else message_or_callback
        await current_message.answer(text, **kwargs)
        if isinstance(message_or_callback, CallbackQuery):
            try:
                await message_or_callback.message.delete()
            except TelegramBadRequest:
                pass

# --- Главное меню и точка входа ---
async def show_main_menu(message: Message, state: FSMContext):
    """Отображает главное меню и сбрасывает состояние."""
    await state.clear()
    await message.answer(
        "🎉 Добро пожаловать! Я ваш личный менеджер Rest Delivery. Чем могу помочь?",
        reply_markup=get_main_menu_keyboard()
    )

@router.message(Command("start", "help", "new"))
async def cmd_start_new(message: Message, state: FSMContext):
    """Обрабатывает команды /start, /help, /new."""
    await show_main_menu(message, state)

@router.message(StateFilter(None))
async def any_message_handler(message: Message, state: FSMContext):
    """Перехватывает любые сообщения вне сценариев и показывает главное меню."""
    await show_main_menu(message, state)

@router.callback_query(F.data == "show_help")
async def show_help_callback(callback: CallbackQuery, state: FSMContext):
    """Показывает справочную информацию."""
    help_text = (
        "Я помогу вам составить смету для мероприятия.\n\n"
        "1. Нажмите **'Создать смету'**.\n"
        "2. Опишите ваше мероприятие в одном сообщении.\n"
        "3. Я проанализирую ваш ответ и предложу меню.\n"
        "4. Вы сможете внести правки или сразу создать PDF-документ.\n\n"
        "Чтобы вернуться в главное меню, нажмите /start."
    )
    await answer_with_fallback(callback, help_text, reply_markup=get_main_menu_keyboard())

# --- Основной флоу создания сметы ---
@router.callback_query(F.data == "start_new_quote")
async def start_new_quote(callback: CallbackQuery, state: FSMContext):
    """Запускает процесс создания сметы, запрашивая все данные в одном сообщении."""
    await state.set_state(QuoteStates.waiting_for_request)
    prompt_text = (
        "📝 **Опишите ваше мероприятие в одном сообщении.**\n\n"
        "Пожалуйста, укажите как можно больше деталей:\n"
        "- **Тип мероприятия** (фуршет, банкет, кофе-брейк)\n"
        "- **Количество гостей**\n"
        "- **Дата и время** начала\n"
        "- **Бюджет** (примерный)\n"
        "- **Особые пожелания** или диетические ограничения\n\n"
        "Я проанализирую ваш ответ и подготовлю предложение."
    )
    await answer_with_fallback(callback, prompt_text)

@router.message(QuoteStates.waiting_for_request)
async def process_request_and_generate_proposal(message: Message, state: FSMContext, menu_json: str):
    """Принимает описание от пользователя, анализирует и генерирует предложение."""
    processing_msg = await message.answer("🤖 Анализирую ваш запрос и подбираю лучшее предложение. Это может занять до минуты...")
    try:
        gemini_expert = GeminiExpert(Config.GEMINI_API_KEY)
        
        # Шаг 1: Анализ запроса для извлечения структурированных данных
        event_details = await gemini_expert.analyze_request(message.text)
        if not event_details or event_details.get("error"):
            await processing_msg.edit_text("❌ Не удалось распознать детали вашего мероприятия. Пожалуйста, попробуйте описать его более подробно, указав все ключевые параметры.", reply_markup=get_main_menu_keyboard())
            await state.clear()
            return
            
        await state.update_data(event_details=event_details)

        # Шаг 2: Генерация предложения на основе извлеченных данных
        proposal_json = await gemini_expert.generate_proposal(event_details, menu_json)
        if not proposal_json or proposal_json.get("error"):
            error_text = proposal_json.get("error", "ответ был пустым") if proposal_json else "ответ был пустым"
            await processing_msg.edit_text(f"❌ Не удалось составить предложение ({error_text}). Попробуйте еще раз, начав с /start.")
            await state.clear()
            return

        await state.update_data(proposal_json=proposal_json)
        formatted_text = gemini_expert.format_proposal_for_telegram(proposal_json)
        
        await processing_msg.delete()
        await message.answer(formatted_text, reply_markup=get_proposal_keyboard(), parse_mode="Markdown")
        await state.set_state(QuoteStates.confirming_proposal)

    except Exception as e:
        logger.error(f"Critical error in process_request_and_generate_proposal: {e}", exc_info=True)
        await processing_msg.edit_text("❌ Произошла критическая ошибка. Пожалуйста, попробуйте позже, начав с /start.")
        await state.clear()

# --- Флоу редактирования и подтверждения ---
@router.callback_query(F.data == "edit_proposal", QuoteStates.confirming_proposal)
async def edit_proposal_prompt(callback: CallbackQuery, state: FSMContext):
    """Предлагает пользователю внести правки."""
    await answer_with_fallback(callback, "✏️ Напишите, что бы вы хотели изменить (например: «замените рыбу на курицу»).")
    await state.set_state(QuoteStates.editing_proposal)

@router.message(QuoteStates.editing_proposal)
async def process_proposal_edits(message: Message, state: FSMContext, menu_json: str):
    """Обрабатывает правки пользователя и генерирует новое предложение."""
    processing_msg = await message.answer("🔄 Вношу правки...")
    try:
        fsm_data = await state.get_data()
        gemini_expert = GeminiExpert(Config.GEMINI_API_KEY)
        
        new_proposal_json = await gemini_expert.generate_proposal(
            event_details=fsm_data.get('event_details'),
            menu_json=menu_json,
            previous_menu=json.dumps(fsm_data.get('proposal_json'), ensure_ascii=False),
            user_edits=message.text
        )

        if not new_proposal_json or new_proposal_json.get("error"):
            await processing_msg.edit_text("❌ Не удалось обновить предложение. Попробуйте сформулировать правки иначе.")
            # Возвращаем пользователя к подтверждению предыдущего варианта
            await state.set_state(QuoteStates.confirming_proposal)
            return

        await state.update_data(proposal_json=new_proposal_json)
        formatted_text = gemini_expert.format_proposal_for_telegram(new_proposal_json)
        
        await processing_msg.delete()
        await message.answer(formatted_text, reply_markup=get_proposal_keyboard(), parse_mode="Markdown")
        await state.set_state(QuoteStates.confirming_proposal)

    except Exception as e:
        logger.error(f"Error in process_proposal_edits: {e}", exc_info=True)
        await processing_msg.edit_text("❌ Ошибка при обновлении предложения.")
        await state.set_state(QuoteStates.confirming_proposal)

@router.callback_query(F.data == "accept_proposal", QuoteStates.confirming_proposal)
async def accept_proposal_and_create_quote(callback: CallbackQuery, state: FSMContext):
    """Принимает предложение и создает PDF-смету."""
    await answer_with_fallback(callback, "✅ Отлично! Создаю финальную смету в Google Sheets...")
    try:
        fsm_data = await state.get_data()
        final_details = fsm_data.get('event_details', {})
        
        sheets_generator = SheetsGenerator(Config.GOOGLE_CREDENTIALS_PATH)
        pdf_link = await sheets_generator.create_quote_from_template(Config.SIMPLE_TEMPLATE_ID, final_details)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔗 Открыть КП (PDF)", url=pdf_link)],
            [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
        ])
        await callback.message.answer("🎉 Ваше коммерческое предложение готово!", reply_markup=keyboard)
        await state.clear()
    except Exception as e:
        logger.error(f"Error in accept_proposal_and_create_quote: {e}", exc_info=True)
        await callback.message.edit_text("❌ Произошла ошибка при создании PDF-сметы.")

# --- Обработчики отмены и возврата в меню ---
@router.callback_query(F.data == "cancel")
async def cancel_handler(callback: CallbackQuery, state: FSMContext):
    """Отменяет текущую операцию и возвращает в главное меню."""
    await answer_with_fallback(callback, "❌ Операция отменена.")
    await show_main_menu(callback.message, state)

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Возвращает в главное меню из других состояний."""
    await answer_with_fallback(callback, "Чем еще могу помочь?")
    await show_main_menu(callback.message, state)
