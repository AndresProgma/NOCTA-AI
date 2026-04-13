# NOCTA-AI

## Estructura inicial simple

Por ahora el backend queda intencionalmente simple:

```text
BackEnd/
  main.py
```

Todo vive en `BackEnd/main.py`:
- crear la app de FastAPI
- ruta principal `/`
- ruta `/health`
- registro `/auth/register`
- login `/auth/login`

La idea es arrancar con una sola pieza facil de entender y despues, cuando el proyecto crezca, separar en rutas, servicios, esquemas y base de datos.
