import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ПРАВИЛЬНОЕ получение токена
BOT_TOKEN = os.environ.get('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['💰 Рассчитать прибыль']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 **Финансовый помощник**\n\n"
        "Введите 3 числа:\n`Закупка Расходы Продажа`\n\n"
        "Пример: `1000 200 1500`",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '💰 Рассчитать прибыль':
        await update.message.reply_text("Введите 3 числа: Закупка Расходы Продажа")
        return
    
    parts = text.split()
    if len(parts) == 3:
        try:
            buy = float(parts[0])
            exp = float(parts[1])
            sell = float(parts[2])
            profit = sell - buy - exp
            
            message = f"💰 Прибыль: {profit:.2f} руб\n📈 Рентабельность: {(profit/sell*100):.1f}%"
            await update.message.reply_text(message)
        except:
            await update.message.reply_text("❌ Ошибка! Введите 3 числа")

def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        logger.error("Добавьте BOT_TOKEN в Environment Variables")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    logger.info("🚀 Бот запущен!")
    app.run_polling()

if __name__ == '__main__':
    main()
