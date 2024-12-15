from datetime import datetime
from ..repositories.task_repository import TaskRepository

class TaskService:
    def __init__(self, task_repository: TaskRepository):
        self.task_repository = task_repository

    def add_task(self, user_id: int, description: str, deadline: datetime):
        self.task_repository.add_task(user_id, description, deadline)

    def get_tasks_for_user(self, user_id: int):
        return self.task_repository.get_tasks_for_user(user_id)

    def get_task_by_id(self, task_id: int):
        return self.task_repository.get_task_by_id(task_id)

    def update_description(self, task_id: int, new_description: str):
        self.task_repository.update_description(task_id, new_description)

    def update_deadline(self, task_id: int, new_deadline: datetime):
        self.task_repository.update_deadline(task_id, new_deadline)
