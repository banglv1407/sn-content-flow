import os
import io
from pathlib import Path
from typing import List, Dict, Any
from ..config import GOOGLE_CREDENTIALS_PATH, DOWNLOADS_DIR
from ..database import log_event

def is_drive_configured() -> bool:
    return os.path.exists(GOOGLE_CREDENTIALS_PATH)

def fetch_files_from_drive(folder_id: str) -> List[Dict[str, Any]]:
    """
    Quét danh sách file ảnh trong folder Google Drive.
    Nếu chưa có credentials.json, trả về danh sách ảnh mẫu để test UI.
    """
    if not is_drive_configured():
        log_event("Google Drive chưa cấu hình credentials.json. Chế độ mô phỏng (Demo Mode).", "WARN")
        return [
            {
                "id": "demo_img_1",
                "name": "bo_suu_tap_go_01.jpg",
                "thumbnailLink": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=400&q=80",
                "webContentLink": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=1200&q=80",
                "mimeType": "image/jpeg"
            },
            {
                "id": "demo_img_2",
                "name": "noi_that_phong_khach_02.jpg",
                "thumbnailLink": "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?w=400&q=80",
                "webContentLink": "https://images.unsplash.com/photo-1615066390971-03e4e1c36ddf?w=1200&q=80",
                "mimeType": "image/jpeg"
            },
            {
                "id": "demo_img_3",
                "name": "chi_tiet_dieu_khac_03.jpg",
                "thumbnailLink": "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=400&q=80",
                "webContentLink": "https://images.unsplash.com/photo-1538688525198-9b88f6f53126?w=1200&q=80",
                "mimeType": "image/jpeg"
            }
        ]

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)

        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="nextPageToken, files(id, name, mimeType, thumbnailLink, webContentLink)"
        ).execute()

        files = results.get('files', [])
        log_event(f"Tìm thấy {len(files)} ảnh trong Google Drive folder: {folder_id}", "INFO")
        return files
    except Exception as e:
        log_event(f"Lỗi khi quét Google Drive: {str(e)}", "ERROR")
        return []

def download_file_from_drive(file_id: str, file_name: str) -> str:
    """Tải file từ Drive về thư mục downloads/ trên Pi"""
    dest_path = DOWNLOADS_DIR / file_name
    if dest_path.exists():
        return str(dest_path)

    if not is_drive_configured():
        # Tạo file placeholder cho demo
        with open(dest_path, "wb") as f:
            f.write(b"DEMO_IMAGE_CONTENT")
        return str(dest_path)

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
        creds = service_account.Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)

        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(dest_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.close()
        return str(dest_path)
    except Exception as e:
        log_event(f"Lỗi khi tải file {file_name} từ Drive: {str(e)}", "ERROR")
        raise e
