from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])

# Simulación de base de datos (temporal)
fake_users_db = []

# 📌 REGISTRO
@router.post("/register")
def register(user: dict):
    fake_users_db.append(user)
    return {"message": "Usuario registrado correctamente"}

# 📌 LOGIN
@router.post("/login")
def login(user: dict):
    for u in fake_users_db:
        if u["email"] == user["email"] and u["password"] == user["password"]:
            return {"message": "Login exitoso"}
    
    return {"error": "Credenciales incorrectas"}