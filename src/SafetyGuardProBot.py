import os
import logging
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CallbackContext,
    JobQueue
)

# Конфигурация бота
TOKEN = "7805454643:AAGFtOlONGwUVzazxS5tqGGbLrmSzDBdu1k"
BOT_USERNAME = "@SafetyGuardProBot"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# База данных вопросов по безопасности
SAFETY_QUIZ = [
    {
        "question": "Что нужно сделать перед началом работы с оборудованием?",
        "options": [
            "Проверить исправность оборудования",
            "Надеть средства индивидуальной защиты",
            "Оба варианта верны"
        ],
        "correct": 2,
        "explanation": "✅ Верно! Перед началом работы необходимо и проверить оборудование, и надеть СИЗ."
    },
    {
        "question": "При каком уровне шума требуется использовать защитные наушники?",
        "options": [
            "Выше 80 дБ",
            "Выше 85 дБ", 
            "Выше 90 дБ"
        ],
        "correct": 1,
        "explanation": "✅ Правильно! При уровне шума выше 85 децибел необходимо использовать средства защиты слуха."
    }
]

async def start(update: Update, context: CallbackContext) -> None:
    """Приветственное сообщение"""
    user = update.effective_user
    await update.message.reply_html(
        rf"""👋 <b>Добро пожаловать в SafetyGuardProBot!</b>

{user.mention_html()}, я ваш цифровой помощник по охране труда. 

Чем могу помочь?""",
        reply_markup=main_menu_keyboard()
    )

def main_menu_keyboard():
    """Клавиатура главного меню"""
    keyboard = [
        [InlineKeyboardButton("🧠 Тест по безопасности", callback_data='start_quiz')],
        [InlineKeyboardButton("⏰ Напоминания о СИЗ", callback_data='set_reminder')],
        [InlineKeyboardButton("ℹ️ О проекте", callback_data='about')],
        [InlineKeyboardButton("📞 Поддержка", callback_data='support')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def button_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик интерактивных кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'start_quiz':
        context.user_data['quiz_index'] = 0
        context.user_data['score'] = 0
        await send_question(update, context)
    elif query.data == 'set_reminder':
        await set_reminder(update, context)
    elif query.data == 'about':
        await about_project(update, context)
    elif query.data == 'support':
        await support(update, context)
    elif query.data.startswith('answer_'):
        await check_answer(update, context)

async def send_question(update: Update, context: CallbackContext) -> None:
    """Отправка вопроса викторины"""
    quiz_index = context.user_data.get('quiz_index', 0)
    
    if quiz_index < len(SAFETY_QUIZ):
        question = SAFETY_QUIZ[quiz_index]
        options = [
            InlineKeyboardButton(opt, callback_data=f'answer_{quiz_index}_{i}')
            for i, opt in enumerate(question["options"])
        ]
        reply_markup = InlineKeyboardMarkup([options])
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"📝 <b>Вопрос {quiz_index + 1}/{len(SAFETY_QUIZ)}</b>\n\n{question['question']}",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
    else:
        score = context.user_data.get('score', 0)
        message = (
            f"🏆 <b>Тест завершен!</b>\n\n"
            f"Ваш результат: <b>{score}/{len(SAFETY_QUIZ)}</b>\n\n"
        )
        
        if score == len(SAFETY_QUIZ):
            message += "🎉 Отличный результат! Вы настоящий эксперт по безопасности!"
        elif score >= len(SAFETY_QUIZ)/2:
            message += "👍 Хороший результат, но есть куда расти!"
        else:
            message += "📚 Рекомендуем изучить материалы по охране труда."
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='HTML',
            reply_markup=main_menu_keyboard()
        )

async def check_answer(update: Update, context: CallbackContext) -> None:
    """Проверка ответа пользователя"""
    query = update.callback_query
    _, quiz_index, answer_index = query.data.split('_')
    quiz_index = int(quiz_index)
    answer_index = int(answer_index)
    
    question = SAFETY_QUIZ[quiz_index]
    if answer_index == question["correct"]:
        context.user_data['score'] = context.user_data.get('score', 0) + 1
        await query.edit_message_text(
            text=f"✅ <b>Правильно!</b>\n\n{question['explanation']}",
            parse_mode='HTML'
        )
    else:
        correct_answer = question["options"][question["correct"]]
        await query.edit_message_text(
            text=f"❌ <b>Неверно.</b> Правильный ответ: <b>{correct_answer}</b>\n\n{question['explanation']}",
            parse_mode='HTML'
        )
    
    context.user_data['quiz_index'] = quiz_index + 1
    await send_question(update, context)

async def set_reminder(update: Update, context: CallbackContext) -> None:
    """Настройка ежедневных напоминаний"""
    job_queue = context.job_queue
    chat_id = update.effective_chat.id
    
    # Удаляем старые напоминания
    current_jobs = job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    # Устанавливаем новые напоминания
    job_queue.run_daily(
        safety_reminder,
        time=time(hour=9, minute=0),
        days=tuple(range(7)),
        chat_id=chat_id,
        name=str(chat_id)
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text="🔔 <b>Напоминание установлено!</b>\n\nЯ буду присылать вам ежедневные напоминания в 9:00 утра.",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def safety_reminder(context: CallbackContext) -> None:
    """Ежедневное напоминание о безопасности"""
    job = context.job
    reminder_text = (
        "⏰ <b>Ежедневная проверка безопасности</b>\n\n"
        "1. Проверьте исправность оборудования\n"
        "2. Убедитесь в наличии всех СИЗ\n"
        "3. Осмотрите рабочее место на предмет опасностей\n\n"
        "<i>Ваша безопасность - наш приоритет!</i>"
    )
    await context.bot.send_message(
        chat_id=job.chat_id,
        text=reminder_text,
        parse_mode='HTML'
    )

async def about_project(update: Update, context: CallbackContext) -> None:
    """Информация о проекте"""
    about_text = (
        "🛡️ <b>SafetyGuardProBot</b>\n\n"
        "Это официальный бот проекта по охране труда.\n\n"
        "Основные функции:\n"
        "• Тесты по технике безопасности\n"
        "• Персональные напоминания\n"
        "• Полезная информация о стандартах безопасности\n\n"
        "По всем вопросам обращайтесь к разработчику."
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=about_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def support(update: Update, context: CallbackContext) -> None:
    """Поддержка"""
    support_text = (
        "📞 <b>Техническая поддержка</b>\n\n"
        "По вопросам работы бота обращайтесь к разработчику:\n"
        "Кузнецов Данила Ростиславович\n"
        "Telegram: @xateri\n\n"
        "Ваш Chat ID: {update.effective_chat.id}"
    )
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=support_text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard()
    )

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Упрощенный обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")

def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", about_project))
    application.add_handler(CommandHandler("quiz", lambda u, c: button_handler(u, c, 'start_quiz')))
    application.add_handler(CommandHandler("reminder", lambda u, c: button_handler(u, c, 'set_reminder')))
    
    # Обработчики
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(error_handler)
    
    # Запуск
    application.run_polling()

if __name__ == '__main__':
    main()