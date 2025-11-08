import os
import logging
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from datetime import datetime

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
        """Сохранение данных в JSON файл"""
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
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.products.append(product)
        self.save_data()
        return product
    
    def get_all_products(self):
        """Получение всех товаров"""
        return self.products
    
    def get_product(self, product_id):
        """Получение товара по ID"""
        for product in self.products:
            if product['id'] == product_id:
                return product
        return None
    
    def update_product(self, product_id, name, cost, expenses, final_price):
        """Обновление товара"""
        for product in self.products:
            if product['id'] == product_id:
                product['name'] = name
                product['cost'] = float(cost)
                product['expenses'] = float(expenses)
                product['final_price'] = float(final_price)
                product['profit'] = float(final_price) - float(cost) - float(expenses)
                product['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_data()
                return product
        return None
    
    def delete_product(self, product_id):
        """Удаление товара"""
        self.products = [p for p in self.products if p['id'] != product_id]
        # Пересчитываем ID
        for i, product in enumerate(self.products, 1):
            product['id'] = i
        self.save_data()
        return True
    
    def get_statistics(self):
        """Получение статистики"""
        if not self.products:
            return None
        
        total_products = len(self.products)
        total_cost = sum(p['cost'] for p in self.products)
        total_expenses = sum(p['expenses'] for p in self.products)
        total_final = sum(p['final_price'] for p in self.products)
        total_profit = sum(p['profit'] for p in self.products)
        
        return {
            'total_products': total_products,
            'total_cost': total_cost,
            'total_expenses': total_expenses,
            'total_final': total_final,
            'total_profit': total_profit
        }

# Создаем менеджер продуктов
product_manager = ProductManager()

# Состояния для диалога
class States:
    WAITING_NAME = 1
    WAITING_COST = 2
    WAITING_EXPENSES = 3
    WAITING_FINAL_PRICE = 4
    EDITING_PRODUCT = 5

# Глобальные переменные для хранения временных данных
user_sessions = {}

def format_product_table(products):
    """Форматирование таблицы товаров"""
    if not products:
        return "📭 Список товаров пуст"
    
    table = "📊 *СПИСОК ТОВАРОВ:*\n\n"
    table += "┌─────┬──────────────────┬──────────┬─────────┬──────────┬──────────┐\n"
    table += "│ ID  │ Название         │ Стоимость│ Расходы │ Итоговая │ Прибыль  │\n"
    table += "├─────┼──────────────────┼──────────┼─────────┼──────────┼──────────┤\n"
    
    for product in products:
        table += f"│ {product['id']:3d} │ {product['name'][:15]:15} │ {product['cost']:8.2f} │ {product['expenses']:7.2f} │ {product['final_price']:8.2f} │ {product['profit']:8.2f} │\n"
    
    table += "└─────┴──────────────────┴──────────┴─────────┴──────────┴──────────┘"
    return table

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        ['📦 Добавить товар', '📊 Список товаров'],
        ['📈 Статистика', '✏️ Редактировать'],
        ['🗑️ Удалить товар']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 *Менеджер товаров*\n\n"
        "Управление стоимостью, расходами и прибылью\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления товара"""
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.WAITING_NAME}
    
    await update.message.reply_text(
        "📝 *Добавление товара*\n\n"
        "Введите название товара:",
        parse_mode='Markdown'
    )

async def handle_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список товаров"""
    products = product_manager.get_all_products()
    table = format_product_table(products)
    
    await update.message.reply_text(
        table,
        parse_mode='Markdown'
    )

async def handle_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    stats = product_manager.get_statistics()
    
    if not stats:
        await update.message.reply_text("📊 Статистика недоступна - нет товаров")
        return
    
    message = (
        "📈 *ОБЩАЯ СТАТИСТИКА:*\n\n"
        f"📦 Всего товаров: {stats['total_products']}\n"
        f"💰 Общая стоимость: {stats['total_cost']:.2f} руб\n"
        f"💸 Общие расходы: {stats['total_expenses']:.2f} руб\n"
        f"🏷️ Общая итоговая сумма: {stats['total_final']:.2f} руб\n"
        f"🎯 Общая прибыль: {stats['total_profit']:.2f} руб\n\n"
        f"📊 Средняя рентабельность: {(stats['total_profit']/stats['total_final']*100 if stats['total_final'] > 0 else 0):.1f}%"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования товара"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ Нет товаров для редактирования")
        return
    
    # Создаем клавиатуру с ID товаров
    keyboard = [[str(product['id'])] for product in products]
    keyboard.append(['🔙 Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✏️ *Редактирование товара*\n\n"
        "Введите ID товара для редактирования:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления товара"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ Нет товаров для удаления")
        return
    
    # Создаем клавиатуру с ID товаров
    keyboard = [[str(product['id'])] for product in products]
    keyboard.append(['🔙 Назад'])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🗑️ *Удаление товара*\n\n"
        "Введите ID товара для удаления:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Основное меню
    if text == '📦 Добавить товар':
        await handle_add_product(update, context)
        return
    elif text == '📊 Список товаров':
        await handle_list_products(update, context)
        return
    elif text == '📈 Статистика':
        await handle_statistics(update, context)
        return
    elif text == '✏️ Редактировать':
        await handle_edit_product(update, context)
        return
    elif text == '🗑️ Удалить товар':
        await handle_delete_product(update, context)
        return
    elif text == '🔙 Назад':
        await start(update, context)
        return
    
    # Обработка состояний диалога
    if user_id in user_sessions:
        state = user_sessions[user_id]['state']
        
        if state == States.WAITING_NAME:
            user_sessions[user_id]['name'] = text
            user_sessions[user_id]['state'] = States.WAITING_COST
            await update.message.reply_text(
                "💰 Введите стоимость товара:",
                parse_mode='Markdown'
            )
        
        elif state == States.WAITING_COST:
            try:
                user_sessions[user_id]['cost'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_EXPENSES
                await update.message.reply_text(
                    "💸 Введите расходы:",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для стоимости")
        
        elif state == States.WAITING_EXPENSES:
            try:
                user_sessions[user_id]['expenses'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_FINAL_PRICE
                await update.message.reply_text(
                    "🏷️ Введите итоговую цену:",
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для расходов")
        
        elif state == States.WAITING_FINAL_PRICE:
            try:
                final_price = float(text)
                session = user_sessions[user_id]
                
                # Добавляем товар
                product = product_manager.add_product(
                    session['name'],
                    session['cost'],
                    session['expenses'],
                    final_price
                )
                
                # Показываем результат
                message = (
                    "✅ *Товар добавлен!*\n\n"
                    f"📦 Название: {product['name']}\n"
                    f"💰 Стоимость: {product['cost']:.2f} руб\n"
                    f"💸 Расходы: {product['expenses']:.2f} руб\n"
                    f"🏷️ Итоговая цена: {product['final_price']:.2f} руб\n"
                    f"🎯 Прибыль: {product['profit']:.2f} руб\n\n"
                    f"📈 Рентабельность: {(product['profit']/product['final_price']*100):.1f}%"
                )
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Очищаем сессию
                del user_sessions[user_id]
                await start(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для итоговой цены")
    
    # Обработка редактирования/удаления по ID
    elif text.isdigit():
        product_id = int(text)
        product = product_manager.get_product(product_id)
        
        if product:
            # Определяем контекст по предыдущему сообщению
            if 'редактирования' in update.message.reply_to_message.text if update.message.reply_to_message else '':
                # Режим редактирования
                user_sessions[user_id] = {
                    'state': States.EDITING_PRODUCT,
                    'product_id': product_id,
                    'current_field': 'name'
                }
                
                message = (
                    f"✏️ *Редактирование товара ID: {product_id}*\n\n"
                    f"Текущие данные:\n"
                    f"Название: {product['name']}\n"
                    f"Стоимость: {product['cost']:.2f}\n"
                    f"Расходы: {product['expenses']:.2f}\n"
                    f"Итоговая цена: {product['final_price']:.2f}\n\n"
                    "Введите новое название:"
                )
                await update.message.reply_text(message, parse_mode='Markdown')
            
            elif 'удаления' in update.message.reply_to_message.text if update.message.reply_to_message else '':
                # Режим удаления
                product_manager.delete_product(product_id)
                await update.message.reply_text(
                    f"✅ Товар ID: {product_id} удален!",
                    parse_mode='Markdown'
                )
                await start(update, context)
        
        else:
            await update.message.reply_text("❌ Товар с таким ID не найден")
    
    else:
        await update.message.reply_text(
            "🤖 Используйте кнопки меню для навигации",
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
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Запускаем бота
        logger.info("🔍 Запускаем бота...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
