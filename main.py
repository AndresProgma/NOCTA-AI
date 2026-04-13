from fastapi import FastAPI
from routes.auth import router as auth_router

app = FastAPI(title="Nocta AI")


@app.get("/")
def home():
    return {"message": "Nocta AI funcionando"}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)