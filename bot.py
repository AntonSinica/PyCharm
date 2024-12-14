from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
import mysql.connector
from datetime import datetime, timedelta
import json
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Загрузка конфигурации из файла
with open("config.json", "r") as config_file:
    config = json.load(config_file)

# Состояния для диалога
DESCRIPTION, DEADLINE = range(2)
SELECT_TASK, CHOOSE_UPDATE_OPTION, UPDATE_DESCRIPTION, UPDATE_DEADLINE = range(2, 6)

# Функция для подключения к базе данных
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=config["db"]["password"],
        database="task_manager"
    )

# Функция для регистрации пользователя
def register_user(user_id, username, first_name, last_name):
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE username=%s, first_name=%s, last_name=%s",
        (user_id, username, first_name, last_name, username, first_name, last_name)
    )
    db.commit()
    cursor.close()
    db.close()

# Добавленные функции для напоминаний
def send_reminders():
    try:
        db = connect_to_db()
        cursor = db.cursor()
        # Получить текущее время в UTC
        now = datetime.utcnow()
        # Вычислить время через 10 минут
        reminder_time = now + timedelta(minutes=10)
        # Получить задачи, где deadline между now и reminder_time и reminder_sent=False
        query = """
            SELECT task_id, user_id, description, deadline 
            FROM tasks 
            WHERE reminder_sent = FALSE 
              AND deadline >= %s 
              AND deadline <= %s
        """
        cursor.execute(query, (now, reminder_time))
        tasks = cursor.fetchall()
        for task in tasks:
            task_id, user_id, description, deadline = task
            # Отправить напоминание пользователю
            context = ContextTypes.from_error_update(None)
            app = ApplicationBuilder().token(config["telegram"]["token"]).build()
            app.bot.send_message(chat_id=user_id, text=f"Напоминание: {description} скоро到期, 截止日期: {deadline}")
            # Обновить флаг reminder_sent
            update_query = "UPDATE tasks SET reminder_sent = TRUE WHERE task_id = %s"
            cursor.execute(update_query, (task_id,))
            db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Ошибка при отправке напоминаний: {e}")

# Функция для команды /reminders
async def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    db = connect_to_db()
    cursor = db.cursor()
    # Получить задачи пользователя, где deadline в будущем и reminder_sent=False
    query = """
        SELECT task_id, description, deadline 
        FROM tasks 
        WHERE user_id = %s 
          AND deadline > %s 
          AND reminder_sent = FALSE
    """
    now = datetime.utcnow()
    cursor.execute(query, (user_id, now))
    tasks = cursor.fetchall()
    cursor.close()
    db.close()
    if not tasks:
        await update.message.reply_text("У вас нет предстоящих напоминаний.")
    else:
        response = "Предстоящие напоминания:\n"
        for task in tasks:
            task_id, description, deadline = task
            response += f"ID: {task_id}, Описание: {description}, Срок: {deadline}\n"
        await update.message.reply_text(response)

# Функция для добавления задачи
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите описание задачи:")
    return DESCRIPTION

# Функция для обработки описания задачи
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введите срок выполнения задачи (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    return DEADLINE

# Функция для обработки срока выполнения задачи
async def get_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Попробуйте снова (ГГГГ-ММ-ДД ЧЧ:ММ):")
        return DEADLINE

    user_id = update.message.from_user.id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name

    # Регистрация пользователя
    register_user(user_id, username, first_name, last_name)

    # Сохранение задачи в базе данных
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO tasks (user_id, description, deadline) VALUES (%s, %s, %s)",
        (user_id, context.user_data['description'], deadline)
    )
    db.commit()
    cursor.close()
    db.close()

    await update.message.reply_text("Задача успешно добавлена!")
    return ConversationHandler.END

# Функция для отмены диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Добавление задачи отменено.")
    return ConversationHandler.END

# Функция для просмотра задач
async def view_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Подключение к базе данных
    db = connect_to_db()
    cursor = db.cursor()

    # Получение задач пользователя
    cursor.execute("SELECT task_id, description, deadline FROM tasks WHERE user_id = %s", (user_id,))
    tasks = cursor.fetchall()

    # Закрытие соединения
    cursor.close()
    db.close()

    if not tasks:
        await update.message.reply_text("У вас нет задач.")
    else:
        response = "Ваши задачи:\n"
        for task in tasks:
            task_id, description, deadline = task
            response += f"ID: {task_id}, Описание: {description}, Срок: {deadline}\n"
        await update.message.reply_text(response)

# Функция для начала диалога обновления задачи
async def update_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    # Подключение к базе данных
    db = connect_to_db()
    cursor = db.cursor()

    # Получение задач пользователя
    cursor.execute("SELECT task_id, description, deadline FROM tasks WHERE user_id = %s", (user_id,))
    tasks = cursor.fetchall()

    # Закрытие соединения
    cursor.close()
    db.close()

    if not tasks:
        await update.message.reply_text("У вас нет задач.")
        return ConversationHandler.END

    response = "Выберите задачу для редактирования (введите ID задачи):\n"
    for task in tasks:
        task_id, description, deadline = task
        response += f"ID: {task_id}, Описание: {description}, Срок: {deadline}\n"
    await update.message.reply_text(response)
    return SELECT_TASK

# Функция для выбора задачи
async def select_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task_id = update.message.text

    # Проверка, существует ли задача
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
    task = cursor.fetchone()
    cursor.close()
    db.close()

    if not task:
        await update.message.reply_text("Задача с таким ID не найдена. Попробуйте снова.")
        return SELECT_TASK

    context.user_data['task_id'] = task_id
    await update.message.reply_text("Что вы хотите изменить?\n1. Описание\n2. Срок выполнения\nВведите номер:")
    return CHOOSE_UPDATE_OPTION

# Функция для выбора поля для редактирования
async def choose_update_option(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    option = update.message.text

    if option == "1":
        await update.message.reply_text("Введите новое описание задачи:")
        return UPDATE_DESCRIPTION
    elif option == "2":
        await update.message.reply_text("Введите новый срок выполнения задачи (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
        return UPDATE_DEADLINE
    else:
        await update.message.reply_text("Неверный ввод. Попробуйте снова.")
        return CHOOSE_UPDATE_OPTION

# Функция для сохранения нового описания
async def save_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_description = update.message.text
    task_id = context.user_data['task_id']

    # Обновление описания в базе данных
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tasks SET description = %s WHERE task_id = %s", (new_description, task_id))
    db.commit()
    cursor.close()
    db.close()

    await update.message.reply_text("Описание задачи успешно обновлено!")
    return ConversationHandler.END

# Функция для сохранения нового срока выполнения
async def save_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        new_deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Попробуйте снова (ГГГГ-ММ-ДД ЧЧ:ММ):")
        return UPDATE_DEADLINE

    task_id = context.user_data['task_id']

    # Обновление срока выполнения в базе данных
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute("UPDATE tasks SET deadline = %s WHERE task_id = %s", (new_deadline, task_id))
    db.commit()
    cursor.close()
    db.close()

    await update.message.reply_text("Срок выполнения задачи успешно обновлен!")
    return ConversationHandler.END

# Функция для отмены диалога обновления
async def cancel_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование задачи отменено.")
    return ConversationHandler.END

# Основная функция
if __name__ == '__main__':
    application = ApplicationBuilder().token(config["telegram"]["token"]).build()

    # Добавить обработчик для /reminders
    application.add_handler(CommandHandler('reminders', show_reminders))

    # Инициализировать и запустить scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_reminders, 'interval', minutes=1)
    scheduler.start()

    # Добавить обработчики для диалогов
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addtask', add_task)],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deadline)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    update_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('updatetask', update_task)],
        states={
            SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task)],
            CHOOSE_UPDATE_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_update_option)],
            UPDATE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_description)],
            UPDATE_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_deadline)]
        },
        fallbacks=[CommandHandler('cancel', cancel_update)]
    )

    application.add_handler(conv_handler)
    application.add_handler(update_conv_handler)

    # Зарегистрировать функцию для завершения scheduler при выключении бота
    atexit.register(lambda: scheduler.shutdown())

    application.run_polling()