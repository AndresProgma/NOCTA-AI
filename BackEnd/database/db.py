accounts = []

def get_users():
    return accounts

def find_user_by_username(usuario: str):
    for user in accounts:
        if user["usuario"] == usuario:
            return user
    return None

def find_user_by_id(user_id: int):
    for user in accounts:
        if user["id"] == user_id:
            return user
    return None

def add_user(usuario: str, password: str):
    new_id = len(accounts) + 1
    user = {
        "id": new_id,
        "usuario": usuario,
        "password": password
    }
    accounts.append(user)
    return user