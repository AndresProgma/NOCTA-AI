from pydantic import BaseModel

class UserAuth(BaseModel):
    usuario: str
    password: str