import requests
import time
from typing import Dict, Any
from ..database import log_event

def publish_to_instagram(ig_account_id: str, access_token: str, public_image_url: str, caption: str) -> Dict[str, Any]:
    """
    Đăng ảnh lên Instagram Business Account:
    Bước 1: Tạo Media Container (POST /{ig-user-id}/media)
    Bước 2: Publish Container (POST /{ig-user-id}/media_publish)
    * Yêu cầu: public_image_url phải là URL công khai (vd qua Cloudflare Tunnel)
    """
    if not ig_account_id or not access_token:
        raise ValueError("Chưa cấu hình Instagram Account ID hoặc Access Token")

    base_url = "https://graph.facebook.com/v19.0"

    # Bước 1: Tạo Media Container
    container_url = f"{base_url}/{ig_account_id}/media"
    container_payload = {
        'image_url': public_image_url,
        'caption': caption,
        'access_token': access_token
    }

    res_container = requests.post(container_url, data=container_payload, timeout=30)
    data_container = res_container.json()

    if res_container.status_code != 200 or 'id' not in data_container:
        err = data_container.get('error', {}).get('message', res_container.text)
        log_event(f"Instagram tạo Container thất bại: {err}", "ERROR")
        raise Exception(f"Instagram Container Error: {err}")

    creation_id = data_container['id']
    time.sleep(3)  # Đợi Instagram xử lý ảnh

    # Bước 2: Xuất bản bài đăng
    publish_url = f"{base_url}/{ig_account_id}/media_publish"
    publish_payload = {
        'creation_id': creation_id,
        'access_token': access_token
    }

    res_pub = requests.post(publish_url, data=publish_payload, timeout=30)
    data_pub = res_pub.json()

    if res_pub.status_code != 200 or 'id' not in data_pub:
        err = data_pub.get('error', {}).get('message', res_pub.text)
        log_event(f"Instagram Publish thất bại: {err}", "ERROR")
        raise Exception(f"Instagram Publish Error: {err}")

    media_id = data_pub['id']
    log_event(f"Đăng bài Instagram thành công (Media ID: {media_id})", "INFO")
    return {"success": True, "media_id": media_id}
