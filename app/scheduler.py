import json
import logging
import os
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .database import (
    get_db_connection, get_setting, get_all_settings, 
    log_event
)
from .services.google_drive import fetch_files_from_drive
from .services.facebook import publish_to_facebook
from .services.instagram import publish_to_instagram
from .services.tiktok import publish_to_tiktok_photo

scheduler = BackgroundScheduler()

def sync_drive_job():
    """Tự động đồng bộ file mới từ Google Drive vào hàng đợi (Queue)"""
    folder_id = get_setting("drive_folder_id")
    if not folder_id:
        # Nếu chưa cấu hình folder ID, bỏ qua hoặc lấy mẫu
        return

    log_event(f"Bắt đầu đồng bộ Google Drive (Folder: {folder_id})...", "INFO")
    try:
        files = fetch_files_from_drive(folder_id)
        default_caption = get_setting("default_caption", "Ảnh mới từ bộ sưu tập ✨")
        
        platforms = []
        if get_setting("enable_facebook") == "true": platforms.append("facebook")
        if get_setting("enable_instagram") == "true": platforms.append("instagram")
        if get_setting("enable_tiktok") == "true": platforms.append("tiktok")
        platforms_json = json.dumps(platforms)

        conn = get_db_connection()
        cursor = conn.cursor()
        new_count = 0

        for f in files:
            file_id = f.get("id")
            name = f.get("name")
            thumb = f.get("thumbnailLink") or f.get("webContentLink")
            
            # Kiểm tra xem file đã có trong database chưa
            cursor.execute("SELECT id FROM posts WHERE drive_file_id = ?", (file_id,))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO posts (drive_file_id, file_name, thumbnail_url, caption, platforms, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """, (file_id, name, thumb, default_caption, platforms_json))
                new_count += 1

        conn.commit()
        conn.close()
        if new_count > 0:
            log_event(f"Đã thêm {new_count} bài viết mới vào hàng đợi chờ đăng.", "INFO")
    except Exception as e:
        log_event(f"Lỗi job đồng bộ Drive: {str(e)}", "ERROR")

def publish_next_post_job():
    """Lấy bài viết tiếp theo trong hàng đợi 'pending' và đăng lên các mạng xã hội"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM posts 
    WHERE status = 'pending' 
    ORDER BY id ASC LIMIT 1
    """)
    post = cursor.fetchone()

    if not post:
        log_event("Hàng đợi không có bài viết nào đang chờ đăng.", "INFO")
        conn.close()
        return

    post_id = post["id"]
    file_name = post["file_name"]
    img_url = post["thumbnail_url"]
    drive_file_id = post["drive_file_id"]
    file_path = post["file_path"]
    caption = post["caption"]
    platforms = json.loads(post["platforms"] or "[]")

    cursor.execute("UPDATE posts SET status = 'publishing' WHERE id = ?", (post_id,))
    conn.commit()
    conn.close()

    # Tải file ảnh gốc chất lượng cao về local nếu chưa có
    target_image = img_url
    if drive_file_id:
        try:
            from .services.google_drive import download_file_from_drive
            dl_path = download_file_from_drive(drive_file_id, file_name)
            if dl_path and os.path.exists(dl_path):
                target_image = dl_path
                conn_u = get_db_connection()
                conn_u.cursor().execute("UPDATE posts SET file_path = ? WHERE id = ?", (dl_path, post_id))
                conn_u.commit()
                conn_u.close()
        except Exception as e:
            log_event(f"Không thể tải ảnh gốc #{post_id}, dùng thumbnail: {str(e)}", "WARN")

    log_event(f"Bắt đầu xuất bản bài viết #{post_id} ({file_name}) lên {platforms}...", "INFO")

    errors = []
    settings = get_all_settings()

    # 1. Đăng Facebook
    if "facebook" in platforms and settings.get("enable_facebook") == "true":
        try:
            fb_page = settings.get("fb_page_id")
            fb_token = settings.get("fb_access_token")
            if fb_page and fb_token:
                publish_to_facebook(fb_page, fb_token, target_image, caption)
            else:
                errors.append("Facebook chưa nhập Page ID / Access Token")
        except Exception as e:
            errors.append(f"Facebook: {str(e)}")

    # 2. Đăng Instagram
    if "instagram" in platforms and settings.get("enable_instagram") == "true":
        try:
            ig_acc = settings.get("ig_account_id")
            fb_token = settings.get("fb_access_token")
            if ig_acc and fb_token:
                publish_to_instagram(ig_acc, fb_token, img_url, caption)
            else:
                errors.append("Instagram chưa nhập Account ID / Token")
        except Exception as e:
            errors.append(f"Instagram: {str(e)}")

    # 3. Đăng TikTok
    if "tiktok" in platforms and settings.get("enable_tiktok") == "true":
        try:
            tt_token = settings.get("tiktok_access_token")
            if tt_token:
                publish_to_tiktok_photo(tt_token, [img_url], caption[:100], caption)
            else:
                errors.append("TikTok chưa có Access Token")
        except Exception as e:
            errors.append(f"TikTok: {str(e)}")

    conn = get_db_connection()
    cursor = conn.cursor()
    if errors:
        err_text = "; ".join(errors)
        cursor.execute("""
        UPDATE posts 
        SET status = 'failed', error_message = ?, published_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        """, (err_text, post_id))
        log_event(f"Bài viết #{post_id} đăng gặp lỗi: {err_text}", "WARN")
    else:
        cursor.execute("""
        UPDATE posts 
        SET status = 'published', error_message = NULL, published_at = CURRENT_TIMESTAMP 
        WHERE id = ?
        """, (post_id,))
        log_event(f"Bài viết #{post_id} ({file_name}) đã xuất bản thành công!", "INFO")

    conn.commit()
    conn.close()

def start_scheduler():
    """Khởi động BackgroundScheduler"""
    if not scheduler.running:
        # Job đồng bộ Google Drive mỗi 30 phút
        scheduler.add_job(
            sync_drive_job,
            trigger=IntervalTrigger(minutes=30),
            id="sync_drive_task",
            replace_existing=True
        )

        # Job xuất bản tự động theo lịch (Ví dụ mặc định: mỗi 6 tiếng một bài)
        scheduler.add_job(
            publish_next_post_job,
            trigger=IntervalTrigger(hours=6),
            id="publish_post_task",
            replace_existing=True
        )

        scheduler.start()
        log_event("Scheduler đã kích hoạt thành công trên Raspberry Pi.", "INFO")
