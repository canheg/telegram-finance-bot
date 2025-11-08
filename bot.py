import os
import logging
import json
from telegram import Update, ReplyKeyboardMarkup
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
        return self.products[start_idx:end_idx], len(self.products)
    
    def get_product(self, product_id):
        """Получение товара по ID"""
        for product in self.products:
            if product['id'] == product_id:
                return product
        return None
    
    def update_product_field(self, product_id, field, value):
        """Обновление конкретного поля товара"""
        for product in self.products:
            if product['id'] == product_id:
                if field == 'cost':
                    product['cost'] = float(value)
                elif field == 'expenses':
                    product['expenses'] = float(value)
                elif field == 'final_price':
                    product['final_price'] = float(value)
                elif field == 'name':
                    product['name'] = value
                
                # Пересчитываем прибыль при изменении числовых полей
                if field in ['cost', 'expenses', 'final_price']:
                    product['profit'] = product['final_price'] - product['cost'] - product['expenses']
                
                product['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_data()
                return product
        return None
    
    def delete_product(self, product_id):
        """Удаление товара"""
        product_to_delete = None
        for product in self.products:
            if product['id'] == product_id:
                product_to_delete = product
                break
        
        if product_to_delete:
            self.products.remove(product_to_delete)
            # Пересчитываем ID
            for i, product in enumerate(self.products, 1):
                product['id'] = i
            self.save_data()
            return True
        return False
    
    def get_statistics(self):
        """Получение общей статистики"""
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
    
    def get_statistics_by_date(self):
        """Получение статистики по датам"""
        if not self.products:
            return None
        
        stats_by_date = defaultdict(lambda: {
            'count': 0,
            'total_cost': 0,
            'total_expenses': 0,
            'total_final': 0,
            'total_profit': 0
        })
        
        for product in self.products:
            date = product['date']
            stats_by_date[date]['count'] += 1
            stats_by_date[date]['total_cost'] += product['cost']
            stats_by_date[date]['total_expenses'] += product['expenses']
            stats_by_date[date]['total_final'] += product['final_price']
            stats_by_date[date]['total_profit'] += product['profit']
        
        return dict(stats_by_date)

# Создаем менеджер продуктов
product_manager = ProductManager()

# Состояния для диалога
class States:
    WAITING_NAME = 1
    WAITING_COST = 2
    WAITING_EXPENSES = 3
    WAITING_FINAL_PRICE = 4
    EDITING_SELECT_PRODUCT = 5
    EDITING_SELECT_FIELD = 6
    EDITING_INPUT_VALUE = 7
    DELETING_SELECT_PRODUCT = 8
    VIEWING_PRODUCTS_PAGE = 9

# Глобальные переменные для хранения временных данных
user_sessions = {}

def format_product_card(product):
    """Форматирование карточки товара для мобильных"""
    return (
        f"🆔 {product['id']}\n"
        f"📦 {product['name']}\n"
        f"💰 {product['cost']:.0f}₽ | 💸 {product['expenses']:.0f}₽\n"
        f"🏷️ {product['final_price']:.0f}₽ | 🎯 {product['profit']:.0f}₽\n"
        f"📅 {product['date']}\n"
        f"➖➖➖➖➖➖➖➖➖"
    )

def format_products_page(products, page, total_pages, total_products):
    """Форматирование страницы товаров для мобильных"""
    if not products:
        return "📭 *Список товаров пуст*"
    
    header = f"📋 *ТОВАРЫ* ({total_products} шт.) • Страница {page}/{total_pages}\n\n"
    
    products_text = ""
    for product in products:
        products_text += format_product_card(product) + "\n"
    
    footer = f"\n📊 *Прибыль страницы:* {sum(p['profit'] for p in products):.0f}₽"
    
    if total_pages > 1:
        footer += f"\n\n⬅️ *{page-1}* | *{page}* | *{page+1}* ➡️" if page < total_pages else f"\n\n⬅️ *{page-1}* | *{page}* ◀️"
    
    return header + products_text + footer

def format_product_table_mobile(products):
    """Компактная таблица для мобильных"""
    if not products:
        return "📭 *Список товаров пуст*"
    
    table = "📊 *ОБЗОР ТОВАРОВ*\n"
    table += "─" * 32 + "\n"
    
    for product in products[:15]:  # Ограничиваем для мобильных
        table += (
            f"🆔{product['id']:3} │ "
            f"{product['name'][:12]:12} │ "
            f"+{product['profit']:.0f}₽\n"
        )
    
    if len(products) > 15:
        table += f"... и ещё {len(products) - 15} товаров\n"
    
    total_profit = sum(p['profit'] for p in products)
    table += f"─" * 32 + f"\n💰 *Итого: {total_profit:.0f}₽*"
    
    return table

def format_statistics_mobile(stats):
    """Статистика для мобильных"""
    if not stats:
        return "📊 *Нет данных для статистики*"
    
    return (
        "📈 *СТАТИСТИКА*\n"
        "─" * 32 + "\n"
        f"📦 Товаров: *{stats['total_products']}*\n"
        f"💰 Стоимость: *{stats['total_cost']:.0f}₽*\n"
        f"💸 Расходы: *{stats['total_expenses']:.0f}₽*\n"
        f"🏷️ Итог: *{stats['total_final']:.0f}₽*\n"
        f"🎯 Прибыль: *{stats['total_profit']:.0f}₽*\n"
        "─" * 32 + "\n"
        f"📊 Рентабельность: *{(stats['total_profit']/stats['total_final']*100 if stats['total_final'] > 0 else 0):.1f}%*"
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        ['📦 Добавить', '📋 Список'],
        ['📈 Статистика', '📅 По датам'],
        ['✏️ Редакт.', '🗑️ Удалить']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    stats = product_manager.get_statistics()
    total_products = stats['total_products'] if stats else 0
    
    await update.message.reply_text(
        f"🤖 *Управление товарами*\n"
        f"📊 {total_products} товаров в базе\n\n"
        f"*Быстрые команды:*\n"
        f"• /add - добавить товар\n"
        f"• /list - список товаров\n"
        f"• /stats - статистика\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления товара"""
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.WAITING_NAME}
    
    await update.message.reply_text(
        "📝 *Новый товар*\n\n"
        "Введите название:",
        parse_mode='Markdown'
    )

async def handle_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список товаров с пагинацией"""
    products, total_count = product_manager.get_products_page(1, 10)
    total_pages = (total_count + 9) // 10
    
    if not products:
        await update.message.reply_text("📭 *Список товаров пуст*", parse_mode='Markdown')
        return
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {
        'state': States.VIEWING_PRODUCTS_PAGE,
        'page': 1,
        'total_pages': total_pages
    }
    
    message = format_products_page(products, 1, total_pages, total_count)
    
    # Клавиатура для навигации
    keyboard = [['📋 Краткий вид']]
    if total_pages > 1:
        keyboard.append(['➡️ След. страница'])
    keyboard.append(['🔙 Назад'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_quick_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Краткий вид товаров"""
    products = product_manager.get_all_products()
    message = format_product_table_mobile(products)
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_next_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Следующая страница товаров"""
    user_id = update.message.from_user.id
    
    if user_id in user_sessions and user_sessions[user_id]['state'] == States.VIEWING_PRODUCTS_PAGE:
        session = user_sessions[user_id]
        current_page = session['page']
        total_pages = session['total_pages']
        
        if current_page < total_pages:
            next_page = current_page + 1
            products, total_count = product_manager.get_products_page(next_page, 10)
            
            user_sessions[user_id]['page'] = next_page
            
            message = format_products_page(products, next_page, total_pages, total_count)
            
            # Клавиатура для навигации
            keyboard = [['📋 Краткий вид']]
            if next_page > 1:
                keyboard.append(['⬅️ Пред. страница'])
            if next_page < total_pages:
                keyboard.append(['➡️ След. страница'])
            keyboard.append(['🔙 Назад'])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("📄 *Это последняя страница*", parse_mode='Markdown')
    else:
        await handle_list_products(update, context)

async def handle_prev_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Предыдущая страница товаров"""
    user_id = update.message.from_user.id
    
    if user_id in user_sessions and user_sessions[user_id]['state'] == States.VIEWING_PRODUCTS_PAGE:
        session = user_sessions[user_id]
        current_page = session['page']
        
        if current_page > 1:
            prev_page = current_page - 1
            products, total_count = product_manager.get_products_page(prev_page, 10)
            
            user_sessions[user_id]['page'] = prev_page
            
            message = format_products_page(products, prev_page, session['total_pages'], total_count)
            
            # Клавиатура для навигации
            keyboard = [['📋 Краткий вид']]
            if prev_page > 1:
                keyboard.append(['⬅️ Пред. страница'])
            if prev_page < session['total_pages']:
                keyboard.append(['➡️ След. страница'])
            keyboard.append(['🔙 Назад'])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("📄 *Это первая страница*", parse_mode='Markdown')
    else:
        await handle_list_products(update, context)

async def handle_general_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    stats = product_manager.get_statistics()
    message = format_statistics_mobile(stats) if stats else "📊 *Нет данных для статистики*"
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_statistics_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику по датам"""
    stats_by_date = product_manager.get_statistics_by_date()
    
    if not stats_by_date:
        await update.message.reply_text("📊 *Нет данных по датам*", parse_mode='Markdown')
        return
    
    message = "📅 *СТАТИСТИКА ПО ДАТАМ*\n" + "─" * 32 + "\n"
    
    for date, stats in sorted(stats_by_date.items())[-10:]:  # Последние 10 дат
        message += (
            f"📅 {date}\n"
            f"   📦 {stats['count']} тов. | "
            f"🎯 {stats['total_profit']:.0f}₽\n"
            f"   ────────────────────\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования товара"""
    products, total_count = product_manager.get_products_page(1, 15)
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров*", parse_mode='Markdown')
        return
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.EDITING_SELECT_PRODUCT}
    
    message = (
        "✏️ *РЕДАКТИРОВАНИЕ*\n\n"
        f"{format_product_table_mobile(products)}\n\n"
        "📝 *Введите ID товара:*"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления товара"""
    products, total_count = product_manager.get_products_page(1, 15)
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров*", parse_mode='Markdown')
        return
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.DELETING_SELECT_PRODUCT}
    
    message = (
        "🗑️ *УДАЛЕНИЕ*\n\n"
        f"{format_product_table_mobile(products)}\n\n"
        "⚠️ *Введите ID товара:*"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def show_edit_fields_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Показать меню выбора поля для редактирования"""
    product = product_manager.get_product(product_id)
    
    if not product:
        await update.message.reply_text("❌ *Товар не найден*", parse_mode='Markdown')
        return
    
    message = (
        f"✏️ *РЕДАКТИРОВАНИЕ* 🆔{product_id}\n\n"
        f"{format_product_card(product)}\n\n"
        "*Выберите поле:*\n"
        "1 📝 Название\n"
        "2 💰 Стоимость\n" 
        "3 💸 Расходы\n"
        "4 🏷️ Итог цена\n"
        "0 ❌ Отмена"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

# Обработчики команд
async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_add_product(update, context)

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_list_products(update, context)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_general_statistics(update, context)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Основное меню
    if text == '📦 Добавить':
        await handle_add_product(update, context)
        return
    elif text == '📋 Список':
        await handle_list_products(update, context)
        return
    elif text == '📋 Краткий вид':
        await handle_quick_view(update, context)
        return
    elif text == '➡️ След. страница':
        await handle_next_page(update, context)
        return
    elif text == '⬅️ Пред. страница':
        await handle_prev_page(update, context)
        return
    elif text == '📈 Статистика':
        await handle_general_statistics(update, context)
        return
    elif text == '📅 По датам':
        await handle_statistics_by_date(update, context)
        return
    elif text == '✏️ Редакт.':
        await handle_edit_product(update, context)
        return
    elif text == '🗑️ Удалить':
        await handle_delete_product(update, context)
        return
    elif text == '🔙 Назад':
        await start(update, context)
        return
    
    # Обработка состояний диалога (остальной код остается таким же как в предыдущей версии)
    # ... (код обработки состояний из предыдущего примера)

def main():
    """Основная функция запуска бота"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    try:
        logger.info("🚀 Создаем приложение бота...")
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Запускаем бота
        logger.info("🔍 Запускаем бота...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
