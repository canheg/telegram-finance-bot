import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
BOT_TOKEN = os.environ.get('BOT_TOKEN')

def start(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    keyboard = [
        ['💰 Рассчитать прибыль'],
        ['ℹ️ Помощь']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    update.message.reply_text(
        "🤖 *Финансовый помощник*\n\n"
        "Введите 3 числа через пробел:\n"
        "`Закупка Расходы Продажа`\n\n"
        "Пример: `1000 200 1500`\n\n"
        "Я рассчитаю прибыль и рентабельность!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def calculate_profit(update: Update, context: CallbackContext):
    """Обработчик расчета прибыли"""
    text = update.message.text
    user = update.message.from_user
    
    logger.info(f"Сообщение от {user.first_name}: {text}")
    
    if text == '💰 Рассчитать прибыль':
        update.message.reply_text(
            "Введите 3 числа через пробел:\n"
            "`Закупочная_цена Расходы Цена_продажи`\n\n"
            "Пример: `1000 200 1500`",
            parse_mode='Markdown'
        )
        return
    
    if text == 'ℹ️ Помощь':
        update.message.reply_text(
            "*📋 Как пользоваться:*\n\n"
            "1. Введите 3 числа через пробел:\n"
            "   `Закупка Расходы Продажа`\n\n"
            "2. Пример: `5000 500 7000`\n\n"
            "3. Я посчитаю прибыль и рентабельность!",
            parse_mode='Markdown'
        )
        return
    
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
                "*📊 Результаты расчета:*\n\n"
                f"💰 Закупочная цена: {buy_price:.2f} руб\n"
                f"💸 Расходы: {expenses:.2f} руб\n"
                f"🏷️ Цена продажи: {sell_price:.2f} руб\n"
                f"🎯 *Прибыль: {profit:.2f} руб*\n"
                f"📈 *Рентабельность: {profitability:.1f}%*"
            )
            
            update.message.reply_text(message, parse_mode='Markdown')
            
        except ValueError:
            # Если не получилось распарсить числа
            update.message.reply_text(
                "❌ *Неверный формат!*\n\n"
                "Введите 3 числа через пробел:\n"
                "`Закупка Расходы Продажа`\n\n"
                "Пример: `1000 200 1500`",
                parse_mode='Markdown'
            )
    else:
        # Если не 3 числа
        update.message.reply_text(
            "🤖 Введите 3 числа для расчета прибыли\n\n"
            "Формат: `Закупка Расходы Продажа`\n"
            "Пример: `5000 500 7000`",
            parse_mode='Markdown'
        )

def error_handler(update: Update, context: CallbackContext):
    """Обработчик ошибок"""
    logger.error(f"Ошибка при обработке сообщения: {context.error}")

def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        logger.error("Добавьте BOT_TOKEN в Environment Variables на Render")
        return
    
    try:
        logger.info("🚀 Создаем updater бота...")
        
        # Создаем updater (старый способ для версии 13.x)
        updater = Updater(BOT_TOKEN, use_context=True)
        
        # Получаем dispatcher для регистрации обработчиков
        dispatcher = updater.dispatcher
        
        # Добавляем обработчики
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", calculate_profit))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, calculate_profit))
        dispatcher.add_error_handler(error_handler)
        
        # Запускаем бота
        logger.info("🔍 Запускаем бота в режиме polling...")
        updater.start_polling()
        
        # Запускаем бота до принудительной остановки
        logger.info("✅ Бот запущен и работает!")
        updater.idle()
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
