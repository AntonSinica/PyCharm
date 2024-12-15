from telegram.ext import ApplicationBuilder, CommandHandler
from .config import Config
from .repositories.user_repository import UserRepository
from .repositories.task_repository import TaskRepository
from .services.user_service import UserService
from .services.task_service import TaskService
from .handlers.add_task_handler import AddTaskHandler
from .handlers.update_task_handler import UpdateTaskHandler
from .handlers.view_tasks_handler import ViewTasksHandler

class BotApp:
    def __init__(self):
        self.config = Config()
        # Инициализируем репозитории
        user_repo = UserRepository(self.config)
        task_repo = TaskRepository(self.config)

        # Инициализируем сервисы
        self.user_service = UserService(user_repo)
        self.task_service = TaskService(task_repo)

        self.application = ApplicationBuilder().token(self.config.telegram_token).build()

        # Добавляем хэндлеры
        add_task_conv = AddTaskHandler(self.user_service, self.task_service).get_conversation_handler()
        update_task_conv = UpdateTaskHandler(self.task_service).get_conversation_handler()
        view_tasks_handler = ViewTasksHandler(self.task_service)

        self.application.add_handler(add_task_conv)
        self.application.add_handler(CommandHandler('viewtasks', view_tasks_handler.view_tasks))
        self.application.add_handler(update_task_conv)

    def run(self):
        self.application.run_polling()
