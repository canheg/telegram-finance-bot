import os
import logging
import json
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import datetime
from collections import defaultdict

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class ProductManager:
    def __init__(self):
        self.data_file = 'products.json'
        self.load_data()
    
    def load_data(self):
        """Загрузка данных из JSON файла"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.products = json.load(f)
            else:
                self.products = []
        except Exception as e:
            logger.error(f"Ошибка загрузки данных: {e}")
            self.products = []
    
    def save_data(self):
        """Сохранение данных в JSON файла"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
    
    def add_product(self, name, cost, expenses, final_price):
        """Добавление нового товара"""
        profit = final_price - cost - expenses
        product = {
            'id': len(self.products) + 1,
            'name': name,
            'cost': float(cost),
            'expenses': float(expenses),
            'final_price': float(final_price),
            'profit': float(profit),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date': datetime.now().strftime("%Y-%m-%d")
        }
        self.products.append(product)
        self.save_data()
        return product
    
    def get_all_products(self):
        """Получение всех товаров"""
        return self.products
    
    def get_products_page(self, page=1, page_size=10):
        """Получение товаров с пагинацией"""
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        total_count = len(self.products)
        return self.products[start_idx:end_idx], total_count
    
    def get_product(self, product_id):
        """Получение товара по ID"""
        for product in self.products:
            if product['id'] == product_id:
                return product
        return None

# Создаем менеджер продуктов
product_manager = ProductManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    from telegram import ReplyKeyboardMarkup
    
    keyboard = [
        ['📦 Добавить', '📋 Список'],
        ['📈 Статистика']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    stats = product_manager.get_statistics() if hasattr(product_manager, 'get_statistics') else None
    total_products = len(product_manager.products)
    
    await update.message.reply_text(
        f"🤖 *Управление товарами*\n"
        f"📊 {total_products} товаров\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления товара"""
    await update.message.reply_text(
        "📝 Для добавления товара используйте команду:\n"
        "`/add Название Стоимость Расходы Итог`\n\n"
        "Пример:\n"
        "`/add iPhone 80000 5000 95000`",
        parse_mode='Markdown'
    )

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда добавления товара"""
    if not context.args or len(context.args) < 4:
        await update.message.reply_text(
            "❌ *Неверный формат!*\n\n"
            "Используйте:\n"
            "`/add Название Стоимость Расходы Итог`\n\n"
            "Пример:\n"
            "`/add iPhone 80000 5000 95000`",
            parse_mode='Markdown'
        )
        return
    
    try:
        name = context.args[0]
        cost = float(context.args[1])
        expenses = float(context.args[2])
        final_price = float(context.args[3])
        
        product = product_manager.add_product(name, cost, expenses, final_price)
        
        message = (
            "✅ *Товар добавлен!*\n\n"
            f"📦 {product['name']}\n"
            f"💰 {product['cost']:.0f}₽ | 💸 {product['expenses']:.0f}₽\n"
            f"🏷️ {product['final_price']:.0f}₽ | 🎯 {product['profit']:.0f}₽\n"
            f"📅 {product['date']}"
        )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Ошибка в числах!*\n"
            "Убедитесь, что стоимость, расходы и итог - это числа",
            parse_mode='Markdown'
        )

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда списка товаров"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("📭 *Список товаров пуст*", parse_mode='Markdown')
        return
    
    # Показываем только последние 10 товаров
    recent_products = products[-10:]
    
    message = "📋 *ПОСЛЕДНИЕ ТОВАРЫ*\n" + "─" * 32 + "\n\n"
    
    for product in recent_products:
        message += (
            f"🆔{product['id']} 📦{product['name'][:15]}\n"
            f"   💰{product['cost']:.0f}₽ 💸{product['expenses']:.0f}₽\n"
            f"   🏷️{product['final_price']:.0f}₽ 🎯+{product['profit']:.0f}₽\n"
            f"   ────────────────────\n"
        )
    
    total_profit = sum(p['profit'] for p in products)
    message += f"\n💰 *Всего товаров: {len(products)}*\n"
    message += f"🎯 *Общая прибыль: {total_profit:.0f}₽*"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда статистики"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("📊 *Нет данных*", parse_mode='Markdown')
        return
    
    total_cost = sum(p['cost'] for p in products)
    total_expenses = sum(p['expenses'] for p in products)
    total_final = sum(p['final_price'] for p in products)
    total_profit = sum(p['profit'] for p in products)
    
    message = (
        "📈 *СТАТИСТИКА*\n"
        "─" * 32 + "\n"
        f"📦 Товаров: *{len(products)}*\n"
        f"💰 Стоимость: *{total_cost:.0f}₽*\n"
        f"💸 Расходы: *{total_expenses:.0f}₽*\n"
        f"🏷️ Итог: *{total_final:.0f}₽*\n"
        f"🎯 Прибыль: *{total_profit:.0f}₽*\n"
        "─" * 32 + "\n"
        f"📊 Рентабельность: *{(total_profit/total_final*100 if total_final > 0 else 0):.1f}%*"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    if text == '📦 Добавить':
        await handle_add_product(update, context)
    elif text == '📋 Список':
        await list_command(update, context)
    elif text == '📈 Статистика':
        await stats_command(update, context)
    else:
        await update.message.reply_text(
            "🤖 Используйте кнопки меню или команды:\n"
            "• /add - добавить товар\n"
            "• /list - список товаров\n" 
            "• /stats - статистика",
            parse_mode='Markdown'
        )

def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    try:
        logger.info("🚀 Создаем приложение бота...")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Запускаем бота с настройками против конфликтов
        logger.info("🔍 Запускаем бота...")
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
        
    except telegram.error.Conflict:
        logger.error("❌ ОШИБКА: Другой экземпляр бота уже запущен!")
        logger.error("💡 Решение: Подождите 2-3 минуты или проверьте настройки Render")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
