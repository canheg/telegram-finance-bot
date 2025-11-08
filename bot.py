import json
import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import datetime

# ВАЖНО: ЗАМЕНИТЕ ЭТОТ ТОКЕН НА СВОЙ!
BOT_TOKEN = "8443242516:AAGqbOkgQ2eJzQZB5OZev2ylWx94GXZ-apU"

class JSONFinanceBot:
    def __init__(self):
        self.data_file = 'finance_data.json'
        self.user_sessions = {}
        self.load_data()
    
    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {'records': []}
            self.save_data()
    
    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def add_record(self, product, input_price, expenses, final_price):
        profit = final_price - input_price - expenses
        record = {
            'date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'product': product,
            'input_price': input_price,
            'expenses': expenses,
            'final_price': final_price,
            'profit': profit
        }
        self.data['records'].append(record)
        self.save_data()
        return profit
    
    def get_statistics(self):
        records = self.data['records']
        if not records:
            return None
        
        total_profit = sum(r['profit'] for r in records)
        total_revenue = sum(r['final_price'] for r in records)
        total_expenses = sum(r['expenses'] for r in records)
        
        return {
            'total_records': len(records),
            'total_profit': total_profit,
            'total_revenue': total_revenue,
            'total_expenses': total_expenses
        }

# Создаем бота
bot = JSONFinanceBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['📊 Добавить запись', '📈 Статистика'], 
        ['💰 Быстрый расчет', '📋 Последние записи'],
        ['💾 Экспорт данных']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 **Финансовый менеджер**\n\n"
        "Учет доходов, расходов и прибыли\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    if text == '📊 Добавить запись':
        bot.user_sessions[user_id] = {'step': 'product'}
        await update.message.reply_text("📝 Введите название товара:")
    
    elif text == '📈 Статистика':
        stats = bot.get_statistics()
        if not stats:
            await update.message.reply_text("📊 Пока нет записей в базе")
        else:
            message = (
                "📊 **Общая статистика:**\n\n"
                f"📋 Всего записей: {stats['total_records']}\n"
                f"💰 Общая выручка: {stats['total_revenue']:.2f} руб\n"
                f"💸 Общие расходы: {stats['total_expenses']:.2f} руб\n"
                f"🎯 Общая прибыль: {stats['total_profit']:.2f} руб\n\n"
                f"📈 Рентабельность: {(stats['total_profit']/stats['total_revenue']*100 if stats['total_revenue'] > 0 else 0):.1f}%"
            )
            await update.message.reply_text(message, parse_mode='Markdown')
    
    elif text == '📋 Последние записи':
        records = bot.data['records'][-5:]
        if not records:
            await update.message.reply_text("📝 Записей пока нет")
        else:
            message = "📋 **Последние записи:**\n\n"
            for record in reversed(records):
                message += f"📦 {record['product']}: {record['final_price']} руб (прибыль: {record['profit']:.2f} руб)\n"
            await update.message.reply_text(message, parse_mode='Markdown')
    
    elif text == '💾 Экспорт данных':
        if bot.data['records']:
            report = "📊 ФИНАНСОВЫЙ ОТЧЕТ\n\n"
            for record in bot.data['records']:
                report += f"{record['date']} | {record['product']} | Прибыль: {record['profit']:.2f} руб\n"
            await update.message.reply_text(f"```\n{report}\n```", parse_mode='Markdown')
        else:
            await update.message.reply_text("Нет данных для экспорта")
    
    elif text == '💰 Быстрый расчет':
        await update.message.reply_text(
            "🧮 Введите 3 числа через пробел:\n"
            "Входная цена Расходы Итоговая цена\n\n"
            "Пример: 1000 200 1500"
        )
    
    elif user_id in bot.user_sessions:
        session = bot.user_sessions[user_id]
        
        if session['step'] == 'product':
            session['product'] = text
            session['step'] = 'input_price'
            await update.message.reply_text("💵 Введите входную цену:")
        
        elif session['step'] == 'input_price':
            try:
                session['input_price'] = float(text)
                session['step'] = 'expenses'
                await update.message.reply_text("💸 Введите расходы:")
            except ValueError:
                await update.message.reply_text("❌ Введите число:")
        
        elif session['step'] == 'expenses':
            try:
                session['expenses'] = float(text)
                session['step'] = 'final_price'
                await update.message.reply_text("🏷️ Введите итоговую цену:")
            except ValueError:
                await update.message.reply_text("❌ Введите число:")
        
        elif session['step'] == 'final_price':
            try:
                final_price = float(text)
                profit = bot.add_record(
                    session['product'],
                    session['input_price'],
                    session['expenses'],
                    final_price
                )
                
                message = (
                    "✅ **Запись добавлена!**\n\n"
                    f"📦 Товар: {session['product']}\n"
                    f"💵 Входная цена: {session['input_price']:.2f} руб\n"
                    f"💸 Расходы: {session['expenses']:.2f} руб\n"
                    f"🏷️ Итоговая цена: {final_price:.2f} руб\n"
                    f"🎯 **Прибыль: {profit:.2f} руб**\n"
                    f"📈 Рентабельность: {(profit/final_price*100):.1f}%"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
                del bot.user_sessions[user_id]
                
            except ValueError:
                await update.message.reply_text("❌ Введите число:")
    
    else:
        if all(part.replace('.', '').isdigit() for part in text.split()):
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
                except ValueError:
                    await update.message.reply_text("❌ Ошибка в формате чисел")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in bot.user_sessions:
        del bot.user_sessions[user_id]
    await update.message.reply_text("❌ Операция отменена")

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запускается...")
    application.run_polling()

if __name__ == '__main__':
    main()
