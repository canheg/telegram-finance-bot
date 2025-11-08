import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен из переменных окружения
BOT_TOKEN = os.environ.get('8443242516:AAGqbOkgQ2eJzQZB5OZev2ylWx94GXZ-apU')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        ['💰 Рассчитать прибыль'],
        ['📊 Добавить запись']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 **Финансовый помощник**\n\n"
        "Я помогу рассчитать прибыль!\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    user_id = update.message.from_user.id
    
    logging.info(f"Получено сообщение от {user_id}: {text}")
    
    if text == '💰 Рассчитать прибыль':
        await update.message.reply_text(
            "🧮 Введите данные для расчета:\n"
            "`Входная цена Расходы Итоговая цена`\n\n"
            "Пример: `1000 200 1500`",
            parse_mode='Markdown'
        )
    
    elif text == '📊 Добавить запись':
        await update.message.reply_text("📝 Функция добавления записей скоро будет доступна!")
    
    else:
        # Пробуем распарсить числа для расчета
        parts = text.split()
        if len(parts) == 3:
            try:
                input_price = float(parts[0])
                expenses = float(parts[1])
                final_price = float(parts[2])
                profit = final_price - input_price - expenses
                
                message = (
                    "🧮 **Результат расчета:**\n\n"
                    f"💵 Входная цена: {input_price:.2f} руб\n"
                    f"💸 Расходы: {expenses:.2f} руб\n"
                    f"🏷️ Итоговая цена: {final_price:.2f} руб\n"
                    f"🎯 **Прибыль: {profit:.2f} руб**\n"
                    f"📈 Рентабельность: {(profit/final_price*100):.1f}%"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                return
            except ValueError:
                pass  # Не числа, продолжаем
        
        # Если не распарсилось как расчет
        await update.message.reply_text(
            "🤖 Используйте кнопки меню или введите 3 числа для расчета прибыли\n\n"
            "Пример: `1000 200 1500`",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logging.error(f"Ошибка: {context.error}")

def main():
    """Основная функция"""
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN не установлен!")
        logging.error("Добавьте переменную BOT_TOKEN в настройки Railway")
        return
    
    logging.info("🤖 Создаем приложение бота...")
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        # Проверяем, на каком хостинге запускаемся
        if os.environ.get('RAILWAY_STATIC_URL'):
            # Запуск на Railway с вебхуком
            domain = os.environ.get('RAILWAY_STATIC_URL')
            port = int(os.environ.get('PORT', 8000))
            
            logging.info(f"🚀 Запуск на Railway: {domain}")
            logging.info(f"📡 Порт: {port}")
            
            # Устанавливаем вебхук
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                secret_token='WEBHOOK_SECRET',
                webhook_url=f"https://{domain}/{BOT_TOKEN}"
            )
        else:
            # Локальный запуск (поллинг)
            logging.info("🔧 Локальный запуск (polling)")
            application.run_polling()
            
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main()
