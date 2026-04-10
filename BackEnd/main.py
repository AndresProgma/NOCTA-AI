from fastapi import FastAPI
from BackEnd.api.routes.auth import router as auth_router

# 👇 ESTA LÍNEA ES CLAVE
app = FastAPI()

# 👇 luego usas app
app.include_router(auth_router)

@app.get("/")
def home():
    return {"message": "Nocta AI funcionando 🚀"}