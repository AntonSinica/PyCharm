from .base_repository import BaseRepository

class UserRepository(BaseRepository):
    def register_user(self, user_id, username, first_name, last_name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name, last_name) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE username=%s, first_name=%s, last_name=%s",
                (user_id, username, first_name, last_name, username, first_name, last_name)
            )
            conn.commit()
