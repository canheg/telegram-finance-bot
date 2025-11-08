import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота
BOT_TOKEN = os.environ.get('8443242516:AAGqbOkgQ2eJzQZB5OZev2ylWx94GXZ-apU')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        ['💰 Рассчитать прибыль'],
        ['ℹ️ Помощь']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 **Финансовый калькулятор**\n\n"
        "Я помогу рассчитать прибыль!\n\n"
        "Введите 3 числа:\n"
        "`Закупка Расходы Продажа`\n\n"
        "Пример: `1000 200 1500`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда помощи"""
    await update.message.reply_text(
        "📋 **Инструкция:**\n\n"
        "1. Введите 3 числа через пробел:\n"
        "   `Закупка Расходы Продажа`\n\n"
        "2. Пример: `5000 500 7000`\n\n"
        "3. Я посчитаю прибыль!",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщений"""
    text = update.message.text
    
    logger.info(f"Получено сообщение: {text}")
    
    if text == '💰 Рассчитать прибыль':
        await update.message.reply_text(
            "Введите 3 числа через пробел:\n"
            "`Закупка Расходы Продажа`\n\n"
            "Пример: `1000 200 1500`",
            parse_mode='Markdown'
        )
        return
    
    if text == 'ℹ️ Помощь':
        await help_command(update, context)
        return
    
    # Пробуем распарсить числа
    parts = text.split()
    
    if len(parts) == 3:
        try:
            buy_price = float(parts[0])
            expenses = float(parts[1])
            sell_price = float(parts[2])
            
            profit = sell_price - buy_price - expenses
            profitability = (profit / sell_price) * 100 if sell_price > 0 else 0
            
            message = (
                "📊 **Результаты:**\n\n"
                f"💰 Закупка: {buy_price:.2f} руб\n"
                f"💸 Расходы: {expenses:.2f} руб\n"
                f"🏷️ Продажа: {sell_price:.2f} руб\n"
                f"🎯 **Прибыль: {profit:.2f} руб**\n"
                f"📈 **Рентабельность: {profitability:.1f}%**"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except ValueError:
            await update.message.reply_text(
                "❌ Ошибка! Введите 3 числа:\n`Закупка Расходы Продажа`",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "🤖 Введите 3 числа для расчета\n\nПример: `1000 200 1500`",
            parse_mode='Markdown'
        )

async def webhook_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для вебхука"""
    # Эта функция будет вызываться при получении обновлений через вебхук
    if update.message:
        await handle_message(update, context)

def main():
    """Запуск бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    logger.info("🚀 Создаем приложение бота...")
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Проверяем, запущено ли на Railway
        if 'RAILWAY_STATIC_URL' in os.environ:
            # ЗАПУСК С ВЕБХУКОМ
            domain = os.environ.get('RAILWAY_STATIC_URL')
            port = int(os.environ.get('PORT', 8000))
            
            logger.info(f"🌐 Запуск с вебхуком на: {domain}")
            logger.info(f"📡 Порт: {port}")
            
            # Запускаем вебхук
            application.run_webhook(
                listen="0.0.0.0",
                port=port,
                url_path=BOT_TOKEN,  # Важно: URL путь должен быть токен
                webhook_url=f"https://{domain}/{BOT_TOKEN}"
            )
        else:
            # ЛОКАЛЬНЫЙ ЗАПУСК
            logger.info("🔧 Локальный запуск (polling)")
            application.run_polling()
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    main()
