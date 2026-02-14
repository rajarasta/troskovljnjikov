from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import CORS_ORIGINS, DATA_DIR
from .api.router import router

app = FastAPI(title="Troskovljnjikov API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    from .db.database import init_db
    await init_db()
