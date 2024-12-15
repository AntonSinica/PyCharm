import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters
)
import mysql.connector
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from pytz import timezone
from pytz import UTC
import json
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

# Функция для отправки напоминания
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    user_id = job.context['user_id']
    task_description = job.context['description']
    deadline = job.context['deadline']

    message = f"Напоминание: Задача '{task_description}' заканчивается через 10 минут ({deadline}). Не забудьте выполнить её!"
    try:
        await context.bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Напоминание отправлено пользователю {user_id} для задачи '{task_description}'")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")

# Функция для добавления задачи
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите описание задачи:")
    return DESCRIPTION

# Функция для обработки описания задачи
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['description'] = update.message.text
    await update.message.reply_text("Введите срок выполнения задачи (в формате ГГГГ-ММ-ДД ЧЧ:ММ):")
    return DEADLINE

# Функция для обработки срока выполнения задачи и планирования напоминания
async def get_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE, scheduler: AsyncIOScheduler) -> int:
    try:
        deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        deadline = deadline.replace(tzinfo=timezone('UTC'))
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
        "INSERT INTO tasks (user_id, description, deadline, status, created_at) VALUES (%s, %s, %s, %s, NOW())",
        (user_id, context.user_data['description'], deadline, 'pending')
    )
    task_id = cursor.lastrowid
    db.commit()
    cursor.close()
    db.close()

    # Планирование напоминания за 10 минут до дедлайна
    reminder_time = deadline - timedelta(minutes=10)
    current_time = datetime.now(timezone('UTC'))
    if reminder_time > current_time:
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[],
            id=f"reminder_{task_id}",
            replace_existing=True,
            kwargs={
                'context': {
                    'user_id': user_id,
                    'description': context.user_data['description'],
                    'deadline': deadline.strftime('%Y-%m-%d %H:%M')
                }
            }
        )
        logger.info(f"Напоминание запланировано на {reminder_time} для задачи ID {task_id}")
    else:
        await update.message.reply_text("Внимание: Срок выполнения задачи менее 10 минут. Напоминание не будет установлено.")

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

# Функции для обновления задачи (упрощены для примера)
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

async def save_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE, scheduler: AsyncIOScheduler) -> int:
    try:
        new_deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        new_deadline = new_deadline.replace(tzinfo=timezone('UTC'))
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

    # Переназначение напоминания
    reminder_time = new_deadline - timedelta(minutes=10)
    current_time = datetime.now(timezone('UTC'))
    if reminder_time > current_time:
        scheduler.add_job(
            send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[],
            id=f"reminder_{task_id}",
            replace_existing=True,
            kwargs={
                'context': {
                    'user_id': update.message.from_user.id,
                    'description': context.user_data.get('description', 'без описания'),
                    'deadline': new_deadline.strftime('%Y-%m-%d %H:%M')
                }
            }
        )
        logger.info(f"Напоминание переназначено на {reminder_time} для задачи ID {task_id}")
    else:
        await update.message.reply_text("Внимание: Новый срок выполнения задачи менее 10 минут. Напоминание не будет установлено.")

    await update.message.reply_text("Срок выполнения задачи успешно обновлен!")
    return ConversationHandler.END

async def cancel_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Редактирование задачи отменено.")
    return ConversationHandler.END

# Функция для загрузки существующих напоминаний
def load_pending_reminders(scheduler: AsyncIOScheduler):
    db = connect_to_db()
    cursor = db.cursor(dictionary=True)
    current_time = datetime.now(UTC)  # Убедитесь, что current_time также в UTC

    cursor.execute(
        "SELECT task_id, user_id, description, deadline FROM tasks WHERE deadline > NOW() AND status = 'pending'"
    )
    tasks = cursor.fetchall()

    for task in tasks:
        task_id = task['task_id']
        user_id = task['user_id']
        description = task['description']
        deadline = task['deadline']

        # Локализуем deadline, если он naive
        if deadline.tzinfo is None:
            deadline = UTC.localize(deadline)

        reminder_time = deadline - timedelta(minutes=10)

        if reminder_time > current_time:
            scheduler.add_job(
                send_reminder,
                trigger=DateTrigger(run_date=reminder_time),
                args=[],  # Аргументы передаются через kwargs
                id=f"reminder_{task_id}",
                replace_existing=True,
                kwargs={
                    'context': {
                        'user_id': user_id,
                        'description': description,
                        'deadline': deadline.strftime('%Y-%m-%d %H:%M')
                    }
                }
            )
            logger.info(f"Напоминание запланировано на {reminder_time} для задачи ID {task_id}")

    cursor.close()
    db.close()

# Основная асинхронная функция
async def main():
    # Настройка планировщика с использованием SQLAlchemyJobStore для хранения заданий в базе данных
    jobstores = {
        'default': SQLAlchemyJobStore(url=f"mysql+mysqlconnector://root:{config['db']['password']}@localhost/task_manager")
    }
    scheduler = AsyncIOScheduler(jobstores=jobstores)
    scheduler.start()
    logger.info("Планировщик запущен.")

    # Загрузка существующих напоминаний
    load_pending_reminders(scheduler)

    # Инициализация приложения Telegram
    application = ApplicationBuilder().token(config["telegram"]["token"]).build()

    # Обработчик диалога для добавления задачи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addtask', add_task)],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: get_deadline(update, context, scheduler))]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    # Обработчик диалога для редактирования задачи
    update_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('updatetask', update_task)],
        states={
            SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task)],
            CHOOSE_UPDATE_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_update_option)],
            UPDATE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_description)],
            UPDATE_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, lambda update, context: save_deadline(update, context, scheduler))]
        },
        fallbacks=[CommandHandler('cancel', cancel_update)]
    )

    # Добавление обработчиков в приложение
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('viewtasks', view_tasks))
    application.add_handler(update_conv_handler)

    # Запуск бота
    await application.initialize()
    await application.start()
    logger.info("Бот запущен и начал прослушивание команд.")
    await application.updater.start_polling()
    # Запуск асинхронного режима работы бота
    await application.run_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")
