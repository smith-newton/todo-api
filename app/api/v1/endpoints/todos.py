from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.todo import Todo
from app.schemas.todo import TodoCreate, TodoUpdate

router = APIRouter(tags=["Todos"])


def serialize(todo: Todo):
    return {
        "id": todo.id,
        "user_id": todo.user_id,
        "title": todo.title,
        "description": todo.description,
        "completed": todo.completed,
        "due_date": todo.due_date,
        "created_at": todo.created_at,
    }


@router.post("/todos", status_code=201)
def create_todo(
    data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = Todo(user_id=current_user.id, **data.model_dump())
    db.add(todo)
    db.commit()
    db.refresh(todo)
    return {"message": "Todo created", "todo": serialize(todo)}


@router.get("/todos")
def get_todos(
    completed: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Todo).where(Todo.user_id == current_user.id)
    if completed is not None:
        query = query.where(Todo.completed == completed)
    todos = db.scalars(query.order_by(Todo.id)).all()
    return {"todos": [serialize(todo) for todo in todos]}


@router.get("/todos/{todo_id}")
def get_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )
    if todo is None:
        raise HTTPException(404, "Todo not found")
    return {"todo": serialize(todo)}


@router.put("/todos/{todo_id}")
def update_todo(
    todo_id: int,
    data: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )
    if todo is None:
        raise HTTPException(404, "Todo not found")

    for field, value in data.model_dump().items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)
    return {"message": "Todo updated", "todo": serialize(todo)}


@router.delete("/todos/{todo_id}")
def delete_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = db.scalar(
        select(Todo).where(
            Todo.id == todo_id,
            Todo.user_id == current_user.id,
        )
    )
    if todo is None:
        raise HTTPException(404, "Todo not found")

    db.delete(todo)
    db.commit()
    return {"message": "Todo deleted successfully"}
