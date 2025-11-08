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
        total_count = len(self.products)
        return self.products[start_idx:end_idx], total_count
    
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
    
    def get_statistics_by_date(self, target_date=None):
        """Получение статистики по датам"""
        if not self.products:
            return None
        
        stats_by_date = defaultdict(lambda: {
            'count': 0,
            'total_cost': 0,
            'total_expenses': 0,
            'total_final': 0,
            'total_profit': 0,
            'products': []
        })
        
        for product in self.products:
            date = product['date']
            stats_by_date[date]['count'] += 1
            stats_by_date[date]['total_cost'] += product['cost']
            stats_by_date[date]['total_expenses'] += product['expenses']
            stats_by_date[date]['total_final'] += product['final_price']
            stats_by_date[date]['total_profit'] += product['profit']
            stats_by_date[date]['products'].append(product)
        
        result = dict(stats_by_date)
        
        # Если указана конкретная дата, возвращаем только ее
        if target_date:
            return {target_date: result[target_date]} if target_date in result else None
        
        return result

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
    SELECTING_DATE_FOR_STATS = 10

# Глобальные переменные для хранения временных данных
user_sessions = {}

def format_detailed_product_list(products):
    """Подробный список товаров в столбик"""
    if not products:
        return "📭 *Список товаров пуст*"
    
    message = "📦 *ПОДРОБНЫЙ СПИСОК ТОВАРОВ*\n"
    message += "═" * 35 + "\n\n"
    
    for product in products:
        message += (
            f"🆔 *ID:* {product['id']}\n"
            f"📦 *Название:* {product['name']}\n"
            f"💰 *Стоимость:* {product['cost']:.0f}₽\n"
            f"💸 *Расходы:* {product['expenses']:.0f}₽\n"
            f"🏷️ *Итоговая цена:* {product['final_price']:.0f}₽\n"
            f"🎯 *Прибыль:* {product['profit']:.0f}₽\n"
            f"📅 *Дата:* {product['date']}\n"
            f"─────────────────────\n\n"
        )
    
    total_profit = sum(p['profit'] for p in products)
    message += f"💰 *Всего товаров:* {len(products)}\n"
    message += f"🎯 *Общая прибыль:* {total_profit:.0f}₽"
    
    return message

def format_products_page(products, page, total_pages, total_products):
    """Форматирование страницы товаров"""
    if not products:
        return "📭 *Список товаров пуст*"
    
    return format_detailed_product_list(products)

def format_statistics_table(stats):
    """Статистика в виде таблички для мобильных"""
    if not stats:
        return "📊 *Нет данных для статистики*"
    
    table = (
        "📈 *ОБЩАЯ СТАТИСТИКА*\n"
        "┌────────────────┬──────────┐\n"
        f"│ 📦 Товаров     │ {stats['total_products']:>8} │\n"
        f"│ 💰 Стоимость   │ {stats['total_cost']:>8.0f}₽ │\n"
        f"│ 💸 Расходы     │ {stats['total_expenses']:>8.0f}₽ │\n"
        f"│ 🏷️ Итог        │ {stats['total_final']:>8.0f}₽ │\n"
        f"│ 🎯 Прибыль     │ {stats['total_profit']:>8.0f}₽ │\n"
        "└────────────────┴──────────┘\n"
    )
    
    profitability = (stats['total_profit'] / stats['total_final'] * 100) if stats['total_final'] > 0 else 0
    table += f"📊 *Рентабельность:* {profitability:.1f}%"
    
    return table

def format_date_statistics(stats_by_date, target_date=None):
    """Статистика по дате с детализацией товаров"""
    if not stats_by_date:
        return "📊 *Нет данных за выбранную дату*"
    
    if target_date:
        # Статистика по конкретной дате
        if target_date not in stats_by_date:
            return f"📊 *Нет данных за {target_date}*"
        
        stats = stats_by_date[target_date]
        message = f"📅 *СТАТИСТИКА ЗА {target_date}*\n"
        message += "═" * 35 + "\n\n"
        
        message += (
            f"📦 *Товаров:* {stats['count']}\n"
            f"💰 *Общая стоимость:* {stats['total_cost']:.0f}₽\n"
            f"💸 *Общие расходы:* {stats['total_expenses']:.0f}₽\n"
            f"🏷️ *Общий итог:* {stats['total_final']:.0f}₽\n"
            f"🎯 *Общая прибыль:* {stats['total_profit']:.0f}₽\n\n"
        )
        
        # Детализация по товарам
        message += "📦 *ТОВАРЫ ЗА ДЕНЬ:*\n"
        message += "─" * 35 + "\n"
        
        for product in stats['products']:
            message += (
                f"🆔{product['id']} {product['name'][:15]}\n"
                f"   💰{product['cost']:.0f}₽ 💸{product['expenses']:.0f}₽\n"
                f"   🏷️{product['final_price']:.0f}₽ 🎯+{product['profit']:.0f}₽\n"
                f"   ───────────────────\n"
            )
        
        profitability = (stats['total_profit'] / stats['total_final'] * 100) if stats['total_final'] > 0 else 0
        message += f"\n📊 *Рентабельность дня:* {profitability:.1f}%"
        
        return message
    else:
        # Общая статистика по всем датам
        message = "📅 *СТАТИСТИКА ПО ДАТАМ*\n"
        message += "═" * 35 + "\n\n"
        
        for date, stats in sorted(stats_by_date.items())[-10:]:
            message += (
                f"📅 *{date}*\n"
                f"   📦 {stats['count']} тов. | "
                f"🎯 {stats['total_profit']:.0f}₽\n"
                f"   ───────────────────\n"
            )
        
        return message

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start - главное меню"""
    keyboard = [
        ['📦 Добавить товар', '📋 Список товаров'],
        ['📈 Общая статистика', '📅 Статистика по дате'],
        ['✏️ Редактировать', '🗑️ Удалить товар']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    stats = product_manager.get_statistics()
    total_products = stats['total_products'] if stats else 0
    
    await update.message.reply_text(
        f"🤖 *Управление товарами*\n"
        f"📊 Всего товаров: {total_products}\n\n"
        f"*Используйте кнопки для управления:*\n"
        f"• Добавить - новый товар\n"
        f"• Список - подробный просмотр\n"
        f"• Статистика - аналитика и отчеты\n"
        f"• Редактировать - изменить товар\n"
        f"• Удалить - удалить товар",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления товара"""
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.WAITING_NAME}
    
    keyboard = [['🔙 Отмена']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📝 *Добавление нового товара*\n\n"
        "Введите название товара:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать подробный список товаров"""
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
    keyboard = []
    if total_pages > 1:
        keyboard.append(['➡️ Следующая страница'])
    keyboard.append(['🔙 Главное меню'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

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
            keyboard = []
            if next_page > 1:
                keyboard.append(['⬅️ Предыдущая страница'])
            if next_page < total_pages:
                keyboard.append(['➡️ Следующая страница'])
            keyboard.append(['🔙 Главное меню'])
            
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
            keyboard = []
            if prev_page > 1:
                keyboard.append(['⬅️ Предыдущая страница'])
            if prev_page < session['total_pages']:
                keyboard.append(['➡️ Следующая страница'])
            keyboard.append(['🔙 Главное меню'])
            
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text("📄 *Это первая страница*", parse_mode='Markdown')
    else:
        await handle_list_products(update, context)

async def handle_general_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать общую статистику в виде таблички"""
    stats = product_manager.get_statistics()
    message = format_statistics_table(stats) if stats else "📊 *Нет данных для статистики*"
    
    keyboard = [
        ['📅 Статистика по дате'],
        ['🔙 Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_date_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню статистики по дате"""
    stats_by_date = product_manager.get_statistics_by_date()
    
    if not stats_by_date:
        await update.message.reply_text("📊 *Нет данных по датам*", parse_mode='Markdown')
        return
    
    # Показываем доступные даты
    available_dates = sorted(stats_by_date.keys())[-10:]  # Последние 10 дат
    
    message = "📅 *ВЫБОР ДАТЫ ДЛЯ СТАТИСТИКИ*\n\n"
    message += "*Доступные даты:*\n"
    
    for i, date in enumerate(available_dates, 1):
        profit = stats_by_date[date]['total_profit']
        message += f"{i}. {date} - {profit:.0f}₽\n"
    
    message += "\n*Введите дату в формате ГГГГ-ММ-ДД*\n"
    message += "Пример: 2024-01-15"
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.SELECTING_DATE_FOR_STATS}
    
    keyboard = [['🔙 Главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования товара"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров для редактирования*", parse_mode='Markdown')
        return
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.EDITING_SELECT_PRODUCT}
    
    # Показываем краткий список для выбора
    message = "✏️ *РЕДАКТИРОВАНИЕ ТОВАРА*\n\n"
    message += "*Доступные товары:*\n"
    
    for product in products[-15:]:  # Последние 15 товаров
        message += f"🆔{product['id']} - {product['name'][:20]} (+{product['profit']:.0f}₽)\n"
    
    message += "\n📝 *Введите ID товара для редактирования:*"
    
    keyboard = [['🔙 Главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления товара"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров для удаления*", parse_mode='Markdown')
        return
    
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.DELETING_SELECT_PRODUCT}
    
    message = (
        "🗑️ *УДАЛЕНИЕ ТОВАРА*\n\n"
        "*Доступные товары:*\n"
    )
    
    for product in products[-15:]:  # Последние 15 товаров
        message += f"🆔{product['id']} - {product['name'][:20]} (+{product['profit']:.0f}₽)\n"
    
    message += "\n⚠️ *Введите ID товара для удаления:*"
    
    keyboard = [['🔙 Главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_edit_fields_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Показать меню выбора поля для редактирования"""
    product = product_manager.get_product(product_id)
    
    if not product:
        await update.message.reply_text("❌ *Товар не найден*", parse_mode='Markdown')
        return
    
    message = (
        f"✏️ *РЕДАКТИРОВАНИЕ ТОВАРА* 🆔{product_id}\n\n"
        f"🆔 *ID:* {product['id']}\n"
        f"📦 *Название:* {product['name']}\n"
        f"💰 *Стоимость:* {product['cost']:.0f}₽\n"
        f"💸 *Расходы:* {product['expenses']:.0f}₽\n"
        f"🏷️ *Итоговая цена:* {product['final_price']:.0f}₽\n"
        f"🎯 *Прибыль:* {product['profit']:.0f}₽\n"
        f"📅 *Дата:* {product['date']}\n\n"
        "*Выберите поле для изменения:*\n"
        "1 📝 Название\n"
        "2 💰 Стоимость\n" 
        "3 💸 Расходы\n"
        "4 🏷️ Итоговая цена\n"
        "0 ❌ Отмена"
    )
    
    keyboard = [['🔙 Главное меню']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех сообщений"""
    user_id = update.message.from_user.id
    text = update.message.text
    
    # Основное меню
    if text == '📦 Добавить товар':
        await handle_add_product(update, context)
        return
    elif text == '📋 Список товаров':
        await handle_list_products(update, context)
        return
    elif text == '➡️ Следующая страница':
        await handle_next_page(update, context)
        return
    elif text == '⬅️ Предыдущая страница':
        await handle_prev_page(update, context)
        return
    elif text == '📈 Общая статистика':
        await handle_general_statistics(update, context)
        return
    elif text == '📅 Статистика по дате':
        await handle_date_statistics(update, context)
        return
    elif text == '✏️ Редактировать':
        await handle_edit_product(update, context)
        return
    elif text == '🗑️ Удалить товар':
        await handle_delete_product(update, context)
        return
    elif text in ['🔙 Главное меню', '🔙 Отмена']:
        await start(update, context)
        return
    
    # Обработка состояний диалога
    if user_id in user_sessions:
        session = user_sessions[user_id]
        state = session['state']
        
        # Добавление товара (остается без изменений)
        if state == States.WAITING_NAME:
            user_sessions[user_id]['name'] = text
            user_sessions[user_id]['state'] = States.WAITING_COST
            
            keyboard = [['🔙 Отмена']]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                "💰 Введите стоимость товара:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif state == States.WAITING_COST:
            try:
                user_sessions[user_id]['cost'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_EXPENSES
                
                keyboard = [['🔙 Отмена']]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    "💸 Введите расходы:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для стоимости")
        
        elif state == States.WAITING_EXPENSES:
            try:
                user_sessions[user_id]['expenses'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_FINAL_PRICE
                
                keyboard = [['🔙 Отмена']]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(
                    "🏷️ Введите итоговую цену:",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для расходов")
        
        elif state == States.WAITING_FINAL_PRICE:
            try:
                final_price = float(text)
                session_data = user_sessions[user_id]
                
                # Добавляем товар
                product = product_manager.add_product(
                    session_data['name'],
                    session_data['cost'],
                    session_data['expenses'],
                    final_price
                )
                
                # Показываем результат
                message = (
                    "✅ *Товар успешно добавлен!*\n\n"
                    f"📦 Название: *{product['name']}*\n"
                    f"💰 Стоимость: *{product['cost']:.0f}₽*\n"
                    f"💸 Расходы: *{product['expenses']:.0f}₽*\n"
                    f"🏷️ Итоговая цена: *{product['final_price']:.0f}₽*\n"
                    f"🎯 Прибыль: *{product['profit']:.0f}₽*\n"
                    f"📅 Дата добавления: *{product['date']}*\n\n"
                    f"📈 Рентабельность: *{(product['profit']/product['final_price']*100):.1f}%*"
                )
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Очищаем сессию и возвращаем в главное меню
                del user_sessions[user_id]
                await start(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для итоговой цены")
        
        # Статистика по дате - ввод даты
        elif state == States.SELECTING_DATE_FOR_STATS:
            # Проверяем формат даты (ГГГГ-ММ-ДД)
            try:
                datetime.strptime(text, '%Y-%m-%d')
                stats_by_date = product_manager.get_statistics_by_date(text)
                message = format_date_statistics(stats_by_date, text)
                
                keyboard = [
                    ['📅 Статистика по дате'],
                    ['🔙 Главное меню']
                ]
                reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                
                await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                del user_sessions[user_id]
                
            except ValueError:
                await update.message.reply_text(
                    "❌ *Неверный формат даты!*\n\n"
                    "Введите дату в формате *ГГГГ-ММ-ДД*\n"
                    "Пример: *2024-01-15*",
                    parse_mode='Markdown'
                )
        
        # Редактирование - выбор товара
        elif state == States.EDITING_SELECT_PRODUCT:
            if text.isdigit():
                product_id = int(text)
                product = product_manager.get_product(product_id)
                
                if product:
                    user_sessions[user_id] = {
                        'state': States.EDITING_SELECT_FIELD,
                        'product_id': product_id
                    }
                    await show_edit_fields_menu(update, context, product_id)
                else:
                    await update.message.reply_text("❌ Товар с таким ID не найден")
            else:
                await update.message.reply_text("❌ Введите корректный ID товара (число)")
        
        # Редактирование - выбор поля
        elif state == States.EDITING_SELECT_FIELD:
            if text.isdigit():
                choice = int(text)
                field_map = {
                    1: 'name',
                    2: 'cost', 
                    3: 'expenses',
                    4: 'final_price'
                }
                
                if choice == 0:
                    del user_sessions[user_id]
                    await start(update, context)
                    return
                
                if choice in field_map:
                    field = field_map[choice]
                    user_sessions[user_id] = {
                        'state': States.EDITING_INPUT_VALUE,
                        'product_id': session['product_id'],
                        'field': field
                    }
                    
                    field_names = {
                        'name': 'название',
                        'cost': 'стоимость',
                        'expenses': 'расходы',
                        'final_price': 'итоговую цену'
                    }
                    
                    keyboard = [['🔙 Отмена']]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(
                        f"✏️ Введите новое значение для {field_names[field]}:",
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Неверный выбор. Введите цифру от 1 до 4")
            else:
                await update.message.reply_text("❌ Введите цифру от 1 до 4")
        
        # Редактирование - ввод значения
        elif state == States.EDITING_INPUT_VALUE:
            product_id = session['product_id']
            field = session['field']
            
            try:
                # Валидация числовых полей
                if field in ['cost', 'expenses', 'final_price']:
                    value = float(text)
                else:
                    value = text
                
                updated_product = product_manager.update_product_field(product_id, field, value)
                
                if updated_product:
                    field_names = {
                        'name': 'название',
                        'cost': 'стоимость', 
                        'expenses': 'расходы',
                        'final_price': 'итоговую цену'
                    }
                    
                    message = (
                        f"✅ *{field_names[field].title()} успешно обновлено!*\n\n"
                        f"📦 Товар ID: {product_id}\n"
                        f"📝 Новое значение: *{value}*\n\n"
                        f"💰 Стоимость: *{updated_product['cost']:.0f}₽*\n"
                        f"💸 Расходы: *{updated_product['expenses']:.0f}₽*\n" 
                        f"🏷️ Итоговая цена: *{updated_product['final_price']:.0f}₽*\n"
                        f"🎯 Прибыль: *{updated_product['profit']:.0f}₽*"
                    )
                    
                    await update.message.reply_text(message, parse_mode='Markdown')
                    del user_sessions[user_id]
                    await start(update, context)
                else:
                    await update.message.reply_text("❌ Ошибка при обновлении товара")
                    
            except ValueError:
                await update.message.reply_text("❌ Введите корректное числовое значение")
        
        # Удаление - выбор товара
        elif state == States.DELETING_SELECT_PRODUCT:
            if text.isdigit():
                product_id = int(text)
                product = product_manager.get_product(product_id)
                
                if product:
                    # Подтверждение удаления
                    message = (
                        f"⚠️ *ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ*\n\n"
                        f"📦 Товар ID: {product_id}\n"
                        f"📝 Название: *{product['name']}*\n"
                        f"💰 Стоимость: *{product['cost']:.0f}₽*\n"
                        f"🎯 Прибыль: *{product['profit']:.0f}₽*\n\n"
                        "Для подтверждения введите:\n"
                        "✅ *ДА* - удалить товар\n"
                        "❌ *НЕТ* - отменить удаление"
                    )
                    
                    user_sessions[user_id] = {
                        'state': 'DELETE_CONFIRMATION',
                        'product_id': product_id
                    }
                    
                    keyboard = [['🔙 Главное меню']]
                    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
                    
                    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await update.message.reply_text("❌ Товар с таким ID не найден")
            else:
                await update.message.reply_text("❌ Введите корректный ID товара (число)")
        
        # Подтверждение удаления
        elif state == 'DELETE_CONFIRMATION':
            if text.upper() in ['ДА', 'YES', 'Y', 'УДАЛИТЬ']:
                product_id = session['product_id']
                if product_manager.delete_product(product_id):
                    await update.message.reply_text(
                        f"✅ *Товар ID: {product_id} успешно удален!*",
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text("❌ Ошибка при удалении товара")
            else:
                await update.message.reply_text("❌ Удаление отменено")
            
            del user_sessions[user_id]
            await start(update, context)
    
    else:
        # Если сообщение не распознано
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
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")

if __name__ == '__main__':
    main()
