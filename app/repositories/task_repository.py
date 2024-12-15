from .base_repository import BaseRepository
from datetime import datetime

class TaskRepository(BaseRepository):
    def add_task(self, user_id, description, deadline: datetime):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (user_id, description, deadline) VALUES (%s, %s, %s)",
                (user_id, description, deadline)
            )
            conn.commit()

    def get_tasks_for_user(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, description, deadline FROM tasks WHERE user_id = %s", (user_id,))
            return cursor.fetchall()

    def get_task_by_id(self, task_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT task_id, user_id, description, deadline FROM tasks WHERE task_id = %s", (task_id,))
            return cursor.fetchone()

    def update_description(self, task_id, new_description):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET description = %s WHERE task_id = %s", (new_description, task_id))
            conn.commit()

    def update_deadline(self, task_id, new_deadline: datetime):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE tasks SET deadline = %s WHERE task_id = %s", (new_deadline, task_id))
            conn.commit()
