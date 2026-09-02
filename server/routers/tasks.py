import json
import os
import time
import uuid
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException
from middleware.firebase_auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "tasks.json")
_lock = Lock()

def _load_tasks() -> list:
    if not os.path.exists(DB_FILE):
        return []
    with _lock:
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

def _save_tasks(tasks: list):
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    with _lock, open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

class TaskSchema(BaseModel):
    id: str | None = None
    title: str
    description: str | None = ""
    status: str  # "todo", "inprogress", "done"
    client_email: str | None = ""
    company: str | None = ""

@router.get("")
@router.get("/")
async def get_tasks(user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    all_tasks = _load_tasks()
    user_tasks = [t for t in all_tasks if t.get("uid") == uid]
    return {"tasks": user_tasks}

@router.post("")
@router.post("/")
async def save_task(body: TaskSchema, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    email_addr = user.get("email") or ""
    all_tasks = _load_tasks()

    from services import log_service
    if body.id:
        # Update existing
        task_found = False
        for t in all_tasks:
            if t.get("id") == body.id and t.get("uid") == uid:
                t["title"] = body.title
                t["description"] = body.description
                t["status"] = body.status
                t["client_email"] = body.client_email or ""
                t["company"] = body.company or ""
                task_found = True
                break
        if not task_found:
            log_service.add_log(uid, email_addr, "EDIT_TASK", f"Failed to edit task {body.id}: Not found.", "ERROR")
            raise HTTPException(status_code=404, detail="Task not found")
        task_data = next(t for t in all_tasks if t.get("id") == body.id)
        log_service.add_log(uid, email_addr, "EDIT_TASK", f"Updated task ticket '{body.title}' details.", "SUCCESS")
    else:
        # Create new
        task_data = {
            "id": f"task_{uuid.uuid4().hex[:8]}",
            "uid": uid,
            "title": body.title,
            "description": body.description,
            "status": body.status,
            "client_email": body.client_email or "",
            "company": body.company or "",
            "created_at": time.time()
        }
        all_tasks.append(task_data)
        log_service.add_log(uid, email_addr, "CREATE_TASK", f"Created new task ticket '{body.title}' inside column '{body.status}'.", "SUCCESS")

    _save_tasks(all_tasks)
    return {"status": "success", "task": task_data}

@router.delete("/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    email_addr = user.get("email") or ""
    all_tasks = _load_tasks()
    new_tasks = [t for t in all_tasks if not (t.get("id") == task_id and t.get("uid") == uid)]
    
    from services import log_service
    if len(new_tasks) == len(all_tasks):
        log_service.add_log(uid, email_addr, "DELETE_TASK", f"Failed to delete task {task_id}: Not found.", "ERROR")
        raise HTTPException(status_code=404, detail="Task not found")
    
    _save_tasks(new_tasks)
    log_service.add_log(uid, email_addr, "DELETE_TASK", f"Deleted task ticket (ID: {task_id}) from Operations Kanban board.", "SUCCESS")
    return {"status": "deleted"}

@router.post("/clear")
async def clear_tasks(user: dict = Depends(get_current_user)):
    uid = user.get("uid", "")
    email_addr = user.get("email") or ""
    all_tasks = _load_tasks()
    remaining_tasks = [t for t in all_tasks if t.get("uid") != uid]
    _save_tasks(remaining_tasks)
    
    from services import log_service
    log_service.add_log(uid, email_addr, "PURGE_TASKS", "Wiped all user tasks and columns from the server operations board database.", "SUCCESS")
    return {"status": "success"}
