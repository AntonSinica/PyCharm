class BaseRepository:
    def __init__(self, db_config):
        self.db_config = db_config

    def get_connection(self):
        from ..database import DatabaseConnection
        return DatabaseConnection(self.db_config)
