from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.session import engine, get_db
from app.models.base import Base
from app.models import User, Todo
from app.api.v1.endpoints.users import router as users_router
from app.api.v1.endpoints.todos import router as todos_router
from app.api.v1.endpoints.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Loads model metadata; creates missing tables only.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="Todo API",
    description="FastAPI with Supabase PostgreSQL",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(users_router)
app.include_router(todos_router)
app.include_router(auth_router)

@app.get("/welcome")
def welcome():
    return {"message": "Welcome to Todo API"}

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
