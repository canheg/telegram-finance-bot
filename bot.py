import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 **Финансовый помощник**\n\n"
        "Введите 3 числа через пробел:\n"
        "`Закупка Расходы Продажа`\n\n"
        "Пример: `1000 200 1500`\n\n"
        "Я рассчитаю прибыль и рентабельность!",
        parse_mode='Markdown'
    )

async def calculate_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик расчета прибыли"""
    text = update.message.text
    user = update.message.from_user
    
    logger.info(f"Сообщение от {user.first_name}: {text}")
    
    # Пробуем распарсить числа
    parts = text.split()
    
    if len(parts) == 3:
        try:
            # Преобразуем в числа
            buy_price = float(parts[0])
            expenses = float(parts[1])
            sell_price = float(parts[2])
            
            # Расчеты
            profit = sell_price - buy_price - expenses
            profitability = (profit / sell_price) * 100 if sell_price > 0 else 0
            
            # Формируем ответ
            message = (
                "📊 **Результаты расчета:**\n\n"
                f"💰 Закупочная цена: {buy_price:.2f} руб\n"
                f"💸 Расходы: {expenses:.2f} руб\n"
                f"🏷️ Цена продажи: {sell_price:.2f} руб\n"
                f"🎯 **Прибыль: {profit:.2f} руб**\n"
                f"📈 **Рентабельность: {profitability:.1f}%**"
            )
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except ValueError:
            # Если не получилось распарсить числа
            await update.message.reply_text(
                "❌ Неверный формат!\n\n"
                "Введите 3 числа через пробел:\n"
                "`Закупка Расходы Продажа`\n\n"
                "Пример: `1000 200 1500`",
                parse_mode='Markdown'
            )
    else:
        # Если не 3 числа
        await update.message.reply_text(
            "🤖 Введите 3 числа для расчета прибыли\n\n"
            "Формат: `Закупка Расходы Продажа`\n"
            "Пример: `5000 500 7000`",
            parse_mode='Markdown'
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке сообщения: {context.error}")

def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        logger.error("Добавьте BOT_TOKEN в Environment Variables на Render")
        return
    
    try:
        logger.info("🚀 Создаем приложение бота...")
        
        # Создаем приложение (правильный способ для версии 20.x)
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calculate_profit))
        application.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("🔍 Запускаем бота в режиме polling...")
        application.run_polling(
            drop_pending_updates=True,  # Игнорируем старые сообщения
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main(
