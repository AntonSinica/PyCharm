from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters
import mysql.connector
from datetime import datetime

# Состояния для диалога
DESCRIPTION, DEADLINE = range(2)

# Функция для подключения к базе данных
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",  # Замените на ваш пароль
        database="task_manager"
    )

# Функция для регистрации пользователя
def register_user(user_id, username, first_name, last_name):
    db = connect_to_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO users (user_id, username, first_name, last_name) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE username=%s, first_name=%s, last_name=%s",
                   (user_id, username, first_name, last_name, username, first_name, last_name))
    db.commit()
    cursor.close()
    db.close()

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
    cursor.execute("INSERT INTO tasks (user_id, description, deadline) VALUES (%s, %s, %s)",
                   (user_id, context.user_data['description'], deadline))
    db.commit()
    cursor.close()
    db.close()

    await update.message.reply_text("Задача успешно добавлена!")
    return ConversationHandler.END

# Функция для отмены диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Добавление задачи отменено.")
    return ConversationHandler.END

# Основная функция
if __name__ == '__main__':
    application = ApplicationBuilder().token('YOUR_BOT_TOKEN').build()

    # Обработчик диалога для добавления задачи
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('addtask', add_task)],
        states={
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_deadline)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)
    application.run_polling()
