from fastapi import APIRouter
from models.user import UserAuth
from database.db import (
    find_user_by_username,
    add_user,
    find_user_by_id,
    get_users
)

router = APIRouter()


@router.post("/auth/register")
def register(user: UserAuth):
    if find_user_by_username(user.usuario):
        return {"error": "El usuario ya existe"}

    add_user(user.usuario, user.password)
    return {"message": "Usuario registrado correctamente"}


@router.post("/auth/login")
def login(user: UserAuth):
    existing_user = find_user_by_username(user.usuario)

    if existing_user and existing_user["password"] == user.password:
        return {"message": "Login exitoso"}

    return {"error": "Credenciales incorrectas"}


@router.get("/users")
def mostrar_usuarios():
    return {"usuarios": get_users()}


@router.get("/users/{user_id}")
def buscar_usuario_id(user_id: int):
    user = find_user_by_id(user_id)

    if user:
        return {"usuario": user}

    return {"error": "Usuario no encontrado"}