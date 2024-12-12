from telegram import Update  # Импортируем класс Update для работы с сообщениями
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes  # Импортируем необходимые классы для работы с ботом

# Определяем асинхронную функцию start, которая будет вызываться при команде /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Отправляем сообщение пользователю
    await update.message.reply_text('Добро пожаловать в задачный бот!')

# Основная функция, которая запускает бота
if __name__ == '__main__':
    # Создаём объект ApplicationBuilder с указанием токена бота
    application = ApplicationBuilder().token('5720251842:AAFW1KxNlpQzHE4GStaiM5OynsObj3abvZI').build()

    # Добавляем обработчик команды /start
    application.add_handler(CommandHandler('start', start))

    # Запускаем бота
    application.run_polling()