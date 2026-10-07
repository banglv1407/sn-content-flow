import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from .config import BASE_DIR, PORT
from .database import (
    init_db, get_db_connection, get_all_settings, 
    update_settings, get_recent_logs, log_event
)
from .scheduler import (
    start_scheduler, sync_drive_job, publish_next_post_job, scheduler
)

app = FastAPI(title="SN Content Low — Auto Social Publisher")

STATIC_DIR = BASE_DIR / "app" / "static"

# Models
class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

class PostUpdate(BaseModel):
    caption: Optional[str] = None
    platforms: Optional[List[str]] = None
    status: Optional[str] = None

@app.on_event("startup")
def on_startup():
    init_db()
    start_scheduler()
    log_event("SN-Content-Low khởi động thành công.", "INFO")

# API Endpoints
@app.get("/api/status")
def get_system_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as count FROM posts GROUP BY status")
    rows = cursor.fetchall()
    stats = {row["status"]: row["count"] for row in rows}
    
    cursor.execute("SELECT COUNT(*) as total FROM posts")
    total_posts = cursor.fetchone()["total"]
    conn.close()

    settings = get_all_settings()

    return {
        "status": "online",
        "scheduler_running": scheduler.running,
        "stats": {
            "total": total_posts,
            "pending": stats.get("pending", 0),
            "publishing": stats.get("publishing", 0),
            "published": stats.get("published", 0),
            "failed": stats.get("failed", 0)
        },
        "channels": {
            "facebook": bool(settings.get("fb_page_id") and settings.get("fb_access_token")),
            "instagram": bool(settings.get("ig_account_id") and settings.get("fb_access_token")),
            "tiktok": bool(settings.get("tiktok_access_token")),
            "google_drive": bool(settings.get("drive_folder_id"))
        }
    }

@app.get("/api/settings")
def get_settings():
    return {"settings": get_all_settings()}

@app.post("/api/settings")
def save_settings(data: SettingsUpdate):
    update_settings(data.settings)
    log_event("Cập nhật cài đặt hệ thống thành công.", "INFO")
    return {"success": True, "message": "Đã lưu cài đặt!"}

@app.get("/api/posts")
def list_posts(status: Optional[str] = None, limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM posts WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    else:
        cursor.execute("SELECT * FROM posts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    posts = []
    for r in rows:
        d = dict(r)
        try:
            d["platforms"] = json.loads(d.get("platforms") or "[]")
        except:
            d["platforms"] = []
        posts.append(d)
    return {"posts": posts}

@app.patch("/api/posts/{post_id}")
def edit_post(post_id: int, data: PostUpdate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fields = []
    values = []
    if data.caption is not None:
        fields.append("caption = ?")
        values.append(data.caption)
    if data.platforms is not None:
        fields.append("platforms = ?")
        values.append(json.dumps(data.platforms))
    if data.status is not None:
        fields.append("status = ?")
        values.append(data.status)
        
    if not fields:
        conn.close()
        return {"success": True}

    values.append(post_id)
    query = f"UPDATE posts SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Đã cập nhật bài đăng!"}

@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()
    log_event(f"Xóa bài viết #{post_id} khỏi hàng đợi.", "INFO")
    return {"success": True, "message": "Đã xóa bài đăng!"}

@app.post("/api/actions/sync-drive")
def trigger_drive_sync(background_tasks: BackgroundTasks):
    background_tasks.add_task(sync_drive_job)
    return {"success": True, "message": "Đang chạy tác vụ đồng bộ Google Drive ngầm..."}

@app.post("/api/actions/publish-now")
def trigger_publish_now(background_tasks: BackgroundTasks):
    background_tasks.add_task(publish_next_post_job)
    return {"success": True, "message": "Đã kích hoạt đăng bài viết tiếp theo!"}

@app.get("/api/logs")
def get_logs(limit: int = 50):
    return {"logs": get_recent_logs(limit)}

# Serve Static files (Dashboard)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.api_route("/", methods=["GET", "HEAD"])
def serve_dashboard():
    return FileResponse(STATIC_DIR / "index.html")
