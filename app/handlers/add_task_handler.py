from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters
from datetime import datetime

DESCRIPTION, DEADLINE = range(2)

class AddTaskHandler:
    def __init__(self, user_service, task_service):
        self.user_service = user_service
        self.task_service = task_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Введите описание задачи:")
        return DESCRIPTION

    async def get_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        context.user_data['description'] = update.message.text
        await update.message.reply_text("Введите срок выполнения задачи (ГГГГ-ММ-ДД ЧЧ:ММ):")
        return DEADLINE

    async def get_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Повторите ввод:")
            return DEADLINE

        user = update.message.from_user
        self.user_service.register_user(user.id, user.username, user.first_name, user.last_name)

        self.task_service.add_task(user.id, context.user_data['description'], deadline)

        await update.message.reply_text("Задача успешно добавлена!")
        return ConversationHandler.END

    def get_conversation_handler(self):
        from .common import cancel
        return ConversationHandler(
            entry_points=[CommandHandler('addtask', self.start)],
            states={
                DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_description)],
                DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.get_deadline)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
