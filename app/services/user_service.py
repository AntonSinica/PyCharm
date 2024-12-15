from ..repositories.user_repository import UserRepository

class UserService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register_user(self, user_id, username, first_name, last_name):
        self.user_repository.register_user(user_id, username, first_name, last_name)
