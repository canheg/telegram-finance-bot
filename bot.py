import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime

# Токен берется из переменных окружения
BOT_TOKEN = os.environ.get('8443242516:AAGqbOkgQ2eJzQZB5OZev2ylWx94GXZ-apU')

class FinanceBot:
    def __init__(self):
        self.user_sessions = {}
    
    def add_record(self, product, input_price, expenses, final_price):
        profit = final_price - input_price - expenses
        return profit

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['?? Добавить запись', '?? Статистика'], 
        ['?? Быстрый расчет']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "?? **Облачный финансовый менеджер**\n\n"
        "Бот работает в облаке! ??\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == '?? Добавить запись':
        await update.message.reply_text("?? Введите данные в формате:\n`Товар Цена Расходы Итог`\n\nПример: `iPhone 50000 1000 60000`")
    
    elif text == '?? Статистика':
        await update.message.reply_text("?? Статистика будет доступна после добавления функций базы данных")
    
    elif text == '?? Быстрый расчет':
        await update.message.reply_text("?? Введите 3 числа:\n`ВходнаяЦена Расходы ИтоговаяЦена`\n\nПример: `1000 200 1500`")
    
    else:
        # Обработка быстрого расчета
        parts = text.split()
        if len(parts) >= 3 and all(part.replace('.', '').isdigit() for part in parts[:3]):
            try:
                input_price = float(parts[0])
                expenses = float(parts[1])
                final_price = float(parts[2])
                profit = final_price - input_price - expenses
                
                message = (
                    "?? **Результат расчета:**\n\n"
                    f"?? Входная цена: {input_price:.2f} руб\n"
                    f"?? Расходы: {expenses:.2f} руб\n"
                    f"??? Итоговая цена: {final_price:.2f} руб\n"
                    f"?? **Прибыль: {profit:.2f} руб**\n"
                    f"?? Рентабельность: {(profit/final_price*100):.1f}%"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
            except ValueError:
                await update.message.reply_text("? Ошибка в числах")
        
        # Обработка добавления записи
        elif len(parts) >= 4:
            try:
                product = parts[0]
                input_price = float(parts[1])
                expenses = float(parts[2])
                final_price = float(parts[3])
                profit = final_price - input_price - expenses
                
                message = (
                    "? **Запись добавлена!**\n\n"
                    f"?? Товар: {product}\n"
                    f"?? Входная цена: {input_price:.2f} руб\n"
                    f"?? Расходы: {expenses:.2f} руб\n"
                    f"??? Итоговая цена: {final_price:.2f} руб\n"
                    f"?? **Прибыль: {profit:.2f} руб**"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
            except ValueError:
                await update.message.reply_text("? Ошибка в формате")

def main():
    if not BOT_TOKEN:
        print("? Ошибка: BOT_TOKEN не установлен!")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    port = int(os.environ.get('PORT', 8443))
    
    # Для локального тестирования
    if os.environ.get('RAILWAY_STATIC_URL'):
        print("?? Запуск на Railway...")
        application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{os.environ.get('RAILWAY_STATIC_URL')}/{BOT_TOKEN}"
        )
    else:
        print("?? Локальный запуск...")
        application.run_polling()

if __name__ == '__main__':
    main()