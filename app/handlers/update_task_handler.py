from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CommandHandler, filters
from datetime import datetime

SELECT_TASK, CHOOSE_UPDATE_OPTION, UPDATE_DESCRIPTION, UPDATE_DEADLINE = range(4)

class UpdateTaskHandler:
    def __init__(self, task_service):
        self.task_service = task_service

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user_id = update.message.from_user.id
        tasks = self.task_service.get_tasks_for_user(user_id)

        if not tasks:
            await update.message.reply_text("У вас нет задач.")
            return ConversationHandler.END

        response = "Выберите задачу для редактирования (введите ID):\n"
        for t in tasks:
            task_id, description, deadline = t
            response += f"ID: {task_id}, Описание: {description}, Срок: {deadline}\n"
        await update.message.reply_text(response)
        return SELECT_TASK

    async def select_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        task_id_str = update.message.text
        if not task_id_str.isdigit():
            await update.message.reply_text("Неверный формат ID.")
            return SELECT_TASK

        task_id = int(task_id_str)
        task = self.task_service.get_task_by_id(task_id)
        if not task:
            await update.message.reply_text("Задача не найдена. Попробуйте снова.")
            return SELECT_TASK

        context.user_data['task_id'] = task_id
        await update.message.reply_text("Что изменить?\n1. Описание\n2. Срок")
        return CHOOSE_UPDATE_OPTION

    async def choose_update_option(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        option = update.message.text
        if option == "1":
            await update.message.reply_text("Введите новое описание:")
            return UPDATE_DESCRIPTION
        elif option == "2":
            await update.message.reply_text("Введите новый срок (ГГГГ-ММ-ДД ЧЧ:ММ):")
            return UPDATE_DEADLINE
        else:
            await update.message.reply_text("Неверный ввод. Попробуйте снова.")
            return CHOOSE_UPDATE_OPTION

    async def save_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        new_desc = update.message.text
        task_id = context.user_data['task_id']
        self.task_service.update_description(task_id, new_desc)
        await update.message.reply_text("Описание успешно обновлено!")
        return ConversationHandler.END

    async def save_deadline(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            new_deadline = datetime.strptime(update.message.text, '%Y-%m-%d %H:%M')
        except ValueError:
            await update.message.reply_text("Неверный формат даты. Повторите ввод:")
            return UPDATE_DEADLINE
        task_id = context.user_data['task_id']
        self.task_service.update_deadline(task_id, new_deadline)
        await update.message.reply_text("Срок успешно обновлен!")
        return ConversationHandler.END

    def get_conversation_handler(self):
        from .common import cancel
        return ConversationHandler(
            entry_points=[CommandHandler('updatetask', self.start)],
            states={
                SELECT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.select_task)],
                CHOOSE_UPDATE_OPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.choose_update_option)],
                UPDATE_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_description)],
                UPDATE_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.save_deadline)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
