from datetime import datetime, timezone
import pytest
import jwt
from app.core.config import JWT_SECRET_KEY
from app.core.security import ALGORITHM


def register_and_login(client, email="alice@example.com", password="DemoPass123!"):
    response = client.post("/auth/register", json={
        "email": email,
        "password": password,
    })
    assert response.status_code == 201, response.text

    response = client.post("/auth/login", data={
        "username": email,
        "password": password,
    })
    assert response.status_code == 200, response.text

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------------
# 1. Health & Welcome
# -------------------------------------------------------------

def test_health_check_with_db(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


# -------------------------------------------------------------
# 2. Authentication & Registration Edge Cases
# -------------------------------------------------------------

def test_register_and_login(client):
    headers = register_and_login(client, "alice@example.com")
    assert headers["Authorization"].startswith("Bearer ")


def test_duplicate_email_registration_fails(client):
    email = "duplicate@example.com"
    password = "DemoPass123!"

    first = client.post("/auth/register", json={"email": email, "password": password})
    assert first.status_code == 201

    second = client.post("/auth/register", json={"email": email, "password": password})
    assert second.status_code == 409


def test_register_email_case_insensitivity(client):
    first = client.post("/auth/register", json={
        "email": "CaseSensitive@Example.Com",
        "password": "DemoPass123!",
    })
    assert first.status_code == 201

    # Attempting lowercased version should fail as duplicate
    second = client.post("/auth/register", json={
        "email": "casesensitive@example.com",
        "password": "DemoPass123!",
    })
    assert second.status_code == 409


def test_register_missing_password(client):
    response = client.post("/auth/register", json={"email": "missing@example.com"})
    assert response.status_code == 422


def test_register_invalid_email(client):
    response = client.post("/auth/register", json={
        "email": "not-an-email",
        "password": "DemoPass123!",
    })
    assert response.status_code == 422


def test_login_wrong_password_fails(client):
    email = "testuser@example.com"
    register_and_login(client, email, "CorrectPass123!")

    # Attempt login with wrong password
    response = client.post("/auth/login", data={
        "username": email,
        "password": "WrongPassword999!",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_login_unregistered_email_fails(client):
    response = client.post("/auth/login", data={
        "username": "ghost@example.com",
        "password": "DemoPass123!",
    })
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


def test_token_for_nonexistent_user_rejected(client):
    # Valid signed JWT, but user_id 999999 does not exist in DB
    ghost_token = jwt.encode(
        {"sub": "999999", "exp": datetime.now(timezone.utc).timestamp() + 3600},
        JWT_SECRET_KEY,
        algorithm=ALGORITHM,
    )
    response = client.get(
        "/todos",
        headers={"Authorization": f"Bearer {ghost_token}"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired access token"


# -------------------------------------------------------------
# 3. Todo CRUD & Edge Cases
# -------------------------------------------------------------

def test_authenticated_user_can_create_todo(client):
    headers = register_and_login(client, "bob@example.com")

    response = client.post("/todos", headers=headers, json={
        "title": "Need to buy a milk",
        "description": "Organic 2% milk",
        "completed": False,
        "due_date": None,
    })

    assert response.status_code == 201
    data = response.json()
    assert data["todo"]["title"] == "Need to buy a milk"
    assert data["todo"]["completed"] is False


def test_create_todo_missing_title(client):
    headers = register_and_login(client, "val@example.com")
    response = client.post("/todos", json={"description": "No title"}, headers=headers)
    assert response.status_code == 422


def test_create_todo_title_too_long(client):
    headers = register_and_login(client, "longtitle@example.com")
    long_title = "A" * 256  # Max allowed is 255
    response = client.post("/todos", json={"title": long_title}, headers=headers)
    assert response.status_code == 422


def test_get_single_todo(client):
    headers = register_and_login(client, "single@example.com")
    created = client.post("/todos", json={"title": "Get single test"}, headers=headers)
    todo_id = created.json()["todo"]["id"]

    response = client.get(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["todo"]["title"] == "Get single test"


def test_get_nonexistent_todo_returns_404(client):
    headers = register_and_login(client, "missingtodo@example.com")
    response = client.get("/todos/99999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Todo not found"


def test_get_todo_invalid_id_type_returns_422(client):
    headers = register_and_login(client, "invalidid@example.com")
    response = client.get("/todos/not-a-number", headers=headers)
    assert response.status_code == 422


def test_filter_todos_by_completed_status(client):
    headers = register_and_login(client, "filter@example.com")

    # Create 1 completed and 1 incomplete task
    client.post("/todos", headers=headers, json={"title": "Task 1", "completed": False})
    client.post("/todos", headers=headers, json={"title": "Task 2", "completed": True})

    # Fetch all
    all_res = client.get("/todos", headers=headers)
    assert len(all_res.json()["todos"]) == 2

    # Fetch completed only
    completed_res = client.get("/todos?completed=true", headers=headers)
    assert len(completed_res.json()["todos"]) == 1
    assert completed_res.json()["todos"][0]["title"] == "Task 2"

    # Fetch pending only
    pending_res = client.get("/todos?completed=false", headers=headers)
    assert len(pending_res.json()["todos"]) == 1
    assert pending_res.json()["todos"][0]["title"] == "Task 1"


def test_authenticated_user_can_update_todo(client):
    headers = register_and_login(client, "update@example.com")
    created = client.post("/todos", json={"title": "Original task"}, headers=headers)
    todo_id = created.json()["todo"]["id"]

    updated = client.put(
        f"/todos/{todo_id}",
        json={"title": "Updated task", "completed": True},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["todo"]["title"] == "Updated task"
    assert updated.json()["todo"]["completed"] is True


def test_update_nonexistent_todo_returns_404(client):
    headers = register_and_login(client, "updatenone@example.com")
    response = client.put(
        "/todos/99999",
        json={"title": "Ghost", "completed": True},
        headers=headers,
    )
    assert response.status_code == 404


def test_update_todo_missing_required_completed_field(client):
    headers = register_and_login(client, "updatemissing@example.com")
    created = client.post("/todos", json={"title": "Task"}, headers=headers)
    todo_id = created.json()["todo"]["id"]

    # TodoUpdate requires "completed: bool"
    response = client.put(
        f"/todos/{todo_id}",
        json={"title": "Only title provided"},
        headers=headers,
    )
    assert response.status_code == 422


def test_authenticated_user_can_delete_todo(client):
    headers = register_and_login(client, "delete@example.com")
    created = client.post("/todos", json={"title": "Temporary task"}, headers=headers)
    todo_id = created.json()["todo"]["id"]

    del_res = client.delete(f"/todos/{todo_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure it's gone
    get_res = client.get(f"/todos/{todo_id}", headers=headers)
    assert get_res.status_code == 404


def test_delete_nonexistent_todo_returns_404(client):
    headers = register_and_login(client, "deletenone@example.com")
    response = client.delete("/todos/99999", headers=headers)
    assert response.status_code == 404


def test_double_delete_returns_404(client):
    headers = register_and_login(client, "doubledelete@example.com")
    created = client.post("/todos", json={"title": "Once deleted"}, headers=headers)
    todo_id = created.json()["todo"]["id"]

    first_delete = client.delete(f"/todos/{todo_id}", headers=headers)
    assert first_delete.status_code == 200

    second_delete = client.delete(f"/todos/{todo_id}", headers=headers)
    assert second_delete.status_code == 404


# -------------------------------------------------------------
# 4. Multi-Tenant Security & Isolation
# -------------------------------------------------------------

def test_users_cannot_see_each_others_todos(client):
    alice = register_and_login(client, "alice_private@example.com")
    bob = register_and_login(client, "bob_private@example.com")

    client.post("/todos", headers=alice, json={"title": "Alice task"})

    response = client.get("/todos", headers=bob)
    assert response.status_code == 200
    assert response.json()["todos"] == []


def test_user_cannot_update_another_users_todo(client):
    alice = register_and_login(client, "alice_lock@example.com")
    bob = register_and_login(client, "bob_lock@example.com")

    created = client.post("/todos", headers=alice, json={"title": "Alice task"})
    todo_id = created.json()["todo"]["id"]

    response = client.put(
        f"/todos/{todo_id}",
        json={"title": "Tampered", "completed": True},
        headers=bob,
    )
    assert response.status_code == 404


def test_user_cannot_delete_another_users_todo(client):
    alice = register_and_login(client, "alice_del@example.com")
    bob = register_and_login(client, "bob_del@example.com")

    created = client.post("/todos", headers=alice, json={"title": "Alice task"})
    todo_id = created.json()["todo"]["id"]

    response = client.delete(f"/todos/{todo_id}", headers=bob)
    assert response.status_code == 404


# -------------------------------------------------------------
# 5. Database Isolation Verification Between Tests
# -------------------------------------------------------------

def test_db_isolation_step_a(client):
    # Create a user and verify DB is clean when starting
    headers = register_and_login(client, "isolation_canary@example.com")
    client.post("/todos", headers=headers, json={"title": "Canary task"})

    res = client.get("/todos", headers=headers)
    assert len(res.json()["todos"]) == 1


def test_db_isolation_step_b(client):
    # In a separate test, the canary user should NOT exist at all in the database!
    login_response = client.post("/auth/login", data={
        "username": "isolation_canary@example.com",
        "password": "DemoPass123!",
    })
    # If isolation works, login must fail because user was wiped with the previous test
    assert login_response.status_code == 401
