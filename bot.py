import os
import logging
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
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
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date': datetime.now().strftime("%Y-%m-%d")  # Добавляем дату для группировки
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
        """Удаление товара - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
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
    EDITING_PRODUCT_SELECT_FIELD = 5
    EDITING_PRODUCT_INPUT_VALUE = 6

# Глобальные переменные для хранения временных данных
user_sessions = {}

def format_product_table(products):
    """Красивое форматирование таблицы товаров"""
    if not products:
        return "📭 *Список товаров пуст*"
    
    table = "📊 *СПИСОК ТОВАРОВ*\n"
    table += "═" * 70 + "\n"
    
    # Заголовок таблицы
    table += "┌─────┬──────────────────┬──────────┬─────────┬──────────┬──────────┬────────────┐\n"
    table += "│ {:3} │ {:16} │ {:8} │ {:7} │ {:8} │ {:8} │ {:10} │\n".format(
        "ID", "Название", "Стоимость", "Расходы", "Итог", "Прибыль", "Дата"
    )
    table += "├─────┼──────────────────┼──────────┼─────────┼──────────┼──────────┼────────────┤\n"
    
    # Данные товаров
    for product in products:
        table += "│ {:3} │ {:16} │ {:8.2f} │ {:7.2f} │ {:8.2f} │ {:8.2f} │ {:10} │\n".format(
            product['id'],
            product['name'][:16],
            product['cost'],
            product['expenses'],
            product['final_price'],
            product['profit'],
            product['date']
        )
    
    table += "└─────┴──────────────────┴──────────┴─────────┴──────────┴──────────┴────────────┘\n"
    
    # Итоги
    total_profit = sum(p['profit'] for p in products)
    table += f"\n💰 *Общая прибыль: {total_profit:.2f} руб*"
    
    return table

def format_statistics_by_date(stats_by_date):
    """Форматирование статистики по датам"""
    if not stats_by_date:
        return "📊 *Нет данных для статистики по датам*"
    
    table = "📅 *СТАТИСТИКА ПО ДАТАМ*\n"
    table += "═" * 80 + "\n"
    
    # Заголовок таблицы
    table += "┌────────────┬───────┬──────────┬─────────┬──────────┬──────────┐\n"
    table += "│ {:10} │ {:5} │ {:8} │ {:7} │ {:8} │ {:8} │\n".format(
        "Дата", "Тов.", "Стоимость", "Расходы", "Итог", "Прибыль"
    )
    table += "├────────────┼───────┼──────────┼─────────┼──────────┼──────────┤\n"
    
    # Данные по датам
    for date, stats in sorted(stats_by_date.items()):
        table += "│ {:10} │ {:5} │ {:8.2f} │ {:7.2f} │ {:8.2f} │ {:8.2f} │\n".format(
            date,
            stats['count'],
            stats['total_cost'],
            stats['total_expenses'],
            stats['total_final'],
            stats['total_profit']
        )
    
    table += "└────────────┴───────┴──────────┴─────────┴──────────┴──────────┘"
    
    return table

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        ['📦 Добавить товар', '📊 Список товаров'],
        ['📈 Общая статистика', '📅 Статистика по датам'],
        ['✏️ Редактировать товар', '🗑️ Удалить товар']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🤖 *Продвинутый менеджер товаров*\n\n"
        "📊 Учет прибыли • 📅 Статистика по датам • ✏️ Гибкое редактирование\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления товара"""
    user_id = update.message.from_user.id
    user_sessions[user_id] = {'state': States.WAITING_NAME}
    
    await update.message.reply_text(
        "📝 *Добавление нового товара*\n\n"
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

async def handle_general_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать общую статистику"""
    stats = product_manager.get_statistics()
    
    if not stats:
        await update.message.reply_text("📊 *Статистика недоступна - нет товаров*", parse_mode='Markdown')
        return
    
    message = (
        "📈 *ОБЩАЯ СТАТИСТИКА*\n\n"
        f"📦 Всего товаров: *{stats['total_products']}*\n"
        f"💰 Общая стоимость: *{stats['total_cost']:.2f} руб*\n"
        f"💸 Общие расходы: *{stats['total_expenses']:.2f} руб*\n"
        f"🏷️ Общая итоговая сумма: *{stats['total_final']:.2f} руб*\n"
        f"🎯 Общая прибыль: *{stats['total_profit']:.2f} руб*\n\n"
        f"📊 Средняя рентабельность: *{(stats['total_profit']/stats['total_final']*100 if stats['total_final'] > 0 else 0):.1f}%*"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_statistics_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику по датам"""
    stats_by_date = product_manager.get_statistics_by_date()
    table = format_statistics_by_date(stats_by_date)
    
    await update.message.reply_text(
        table,
        parse_mode='Markdown'
    )

async def handle_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования товара"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров для редактирования*", parse_mode='Markdown')
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

async def handle_edit_select_field(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Выбор поля для редактирования"""
    product = product_manager.get_product(product_id)
    
    if not product:
        await update.message.reply_text("❌ *Товар не найден*", parse_mode='Markdown')
        return
    
    keyboard = [
        ['📝 Название', '💰 Стоимость'],
        ['💸 Расходы', '🏷️ Итоговая цена'],
        ['🔙 Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    message = (
        f"✏️ *Редактирование товара ID: {product_id}*\n\n"
        f"Текущие данные:\n"
        f"📝 Название: *{product['name']}*\n"
        f"💰 Стоимость: *{product['cost']:.2f} руб*\n"
        f"💸 Расходы: *{product['expenses']:.2f} руб*\n"
        f"🏷️ Итоговая цена: *{product['final_price']:.2f} руб*\n"
        f"🎯 Прибыль: *{product['profit']:.2f} руб*\n"
        f"📅 Дата добавления: *{product['date']}*\n\n"
        "Выберите поле для изменения:"
    )
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало удаления товара - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    products = product_manager.get_all_products()
    
    if not products:
        await update.message.reply_text("❌ *Нет товаров для удаления*", parse_mode='Markdown')
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
    elif text == '📈 Общая статистика':
        await handle_general_statistics(update, context)
        return
    elif text == '📅 Статистика по датам':
        await handle_statistics_by_date(update, context)
        return
    elif text == '✏️ Редактировать товар':
        await handle_edit_product(update, context)
        return
    elif text == '🗑️ Удалить товар':
        await handle_delete_product(update, context)
        return
    elif text == '🔙 Назад':
        await start(update, context)
        return
    
    # Обработка редактирования полей
    if user_id in user_sessions:
        session = user_sessions[user_id]
        
        if session['state'] == States.WAITING_NAME:
            user_sessions[user_id]['name'] = text
            user_sessions[user_id]['state'] = States.WAITING_COST
            await update.message.reply_text("💰 Введите стоимость товара:")
        
        elif session['state'] == States.WAITING_COST:
            try:
                user_sessions[user_id]['cost'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_EXPENSES
                await update.message.reply_text("💸 Введите расходы:")
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для стоимости")
        
        elif session['state'] == States.WAITING_EXPENSES:
            try:
                user_sessions[user_id]['expenses'] = float(text)
                user_sessions[user_id]['state'] = States.WAITING_FINAL_PRICE
                await update.message.reply_text("🏷️ Введите итоговую цену:")
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для расходов")
        
        elif session['state'] == States.WAITING_FINAL_PRICE:
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
                    f"💰 Стоимость: *{product['cost']:.2f} руб*\n"
                    f"💸 Расходы: *{product['expenses']:.2f} руб*\n"
                    f"🏷️ Итоговая цена: *{product['final_price']:.2f} руб*\n"
                    f"🎯 Прибыль: *{product['profit']:.2f} руб*\n"
                    f"📅 Дата добавления: *{product['date']}*\n\n"
                    f"📈 Рентабельность: *{(product['profit']/product['final_price']*100):.1f}%*"
                )
                
                await update.message.reply_text(message, parse_mode='Markdown')
                
                # Очищаем сессию
                del user_sessions[user_id]
                await start(update, context)
                
            except ValueError:
                await update.message.reply_text("❌ Введите корректное число для итоговой цены")
        
        elif session['state'] == States.EDITING_PRODUCT_INPUT_VALUE:
            # Обработка ввода нового значения для поля
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
                        f"💰 Стоимость: *{updated_product['cost']:.2f} руб*\n"
                        f"💸 Расходы: *{updated_product['expenses']:.2f} руб*\n" 
                        f"🏷️ Итоговая цена: *{updated_product['final_price']:.2f} руб*\n"
                        f"🎯 Прибыль: *{updated_product['profit']:.2f} руб*"
                    )
                    
                    await update.message.reply_text(message, parse_mode='Markdown')
                    del user_sessions[user_id]
                    await start(update, context)
                else:
                    await update.message.reply_text("❌ Ошибка при обновлении товара")
                    
            except ValueError:
                await update.message.reply_text("❌ Введите корректное числовое значение")
    
    # Обработка выбора товара для редактирования/удаления
    elif text.isdigit():
        product_id = int(text)
        product = product_manager.get_product(product_id)
        
        if product:
            # Определяем контекст по предыдущему сообщению
            if update.message.reply_to_message:
                reply_text = update.message.reply_to_message.text
                
                if 'редактирования' in reply_text:
                    # Переходим к выбору поля для редактирования
                    await handle_edit_select_field(update, context, product_id)
                    return
                
                elif 'удаления' in reply_text:
                    # Удаляем товар - ИСПРАВЛЕННАЯ ВЕРСИЯ
                    if product_manager.delete_product(product_id):
                        await update.message.reply_text(
                            f"✅ *Товар ID: {product_id} успешно удален!*",
                            parse_mode='Markdown'
                        )
                        await start(update, context)
                    else:
                        await update.message.reply_text("❌ Ошибка при удалении товара")
                    return
        
        else:
            await update.message.reply_text("❌ Товар с таким ID не найден")
    
    # Обработка выбора поля для редактирования
    elif text in ['📝 Название', '💰 Стоимость', '💸 Расходы', '🏷️ Итоговая цена']:
        if update.message.reply_to_message and 'Выберите поле для изменения' in update.message.reply_to_message.text:
            # Извлекаем ID товара из предыдущего сообщения
            reply_text = update.message.reply_to_message.text
            product_id = int(reply_text.split('ID: ')[1].split('\n')[0])
            
            field_map = {
                '📝 Название': 'name',
                '💰 Стоимость': 'cost', 
                '💸 Расходы': 'expenses',
                '🏷️ Итоговая цена': 'final_price'
            }
            
            field = field_map[text]
            field_names = {
                'name': 'название',
                'cost': 'стоимость',
                'expenses': 'расходы', 
                'final_price': 'итоговую цену'
            }
            
            # Сохраняем в сессию
            user_sessions[user_id] = {
                'state': States.EDITING_PRODUCT_INPUT_VALUE,
                'product_id': product_id,
                'field': field
            }
            
            await update.message.reply_text(
                f"✏️ Введите новое значение для {field_names[field]}:",
                parse_mode='Markdown'
            )
    
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
