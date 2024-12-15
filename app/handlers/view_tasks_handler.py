from telegram import Update
from telegram.ext import ContextTypes

class ViewTasksHandler:
    def __init__(self, task_service):
        self.task_service = task_service

    async def view_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.message.from_user.id
        tasks = self.task_service.get_tasks_for_user(user_id)
        if not tasks:
            await update.message.reply_text("У вас нет задач.")
        else:
            response = "Ваши задачи:\n"
            for t in tasks:
                task_id, description, deadline = t
                response += f"ID: {task_id}, Описание: {description}, Срок: {deadline}\n"
            await update.message.reply_text(response)
