import mysql.connector

from .config import Config

class DatabaseConnection:
    def __init__(self, config: Config):
        self.config = config

    def __enter__(self):
        self.connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password=self.config.db_password,
            database="task_manager"
        )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection.is_connected():
            self.connection.close()
