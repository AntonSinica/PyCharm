from .base_repository import BaseRepository

class ReminderRepository(BaseRepository):
    def add_reminder(self, task_id, remind_at):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reminders (task_id, remind_at) VALUES (%s, %s)",
                (task_id, remind_at)
            )
            conn.commit()
