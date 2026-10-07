import requests
import os
from typing import Dict, Any
from ..database import log_event

def publish_to_facebook(page_id: str, access_token: str, image_path_or_url: str, caption: str) -> Dict[str, Any]:
    """
    Đăng ảnh lên Facebook Page bằng Graph API v19.0
    Endpoint: POST /{page-id}/photos
    """
    if not page_id or not access_token:
        raise ValueError("Chưa cấu hình Facebook Page ID hoặc Page Access Token")

    url = f"https://graph.facebook.com/v19.0/{page_id}/photos"

    # Nếu là file local
    if os.path.exists(image_path_or_url):
        with open(image_path_or_url, 'rb') as f:
            files = {'source': f}
            data = {
                'caption': caption,
                'access_token': access_token
            }
            res = requests.post(url, files=files, data=data, timeout=30)
    else:
        # Nếu là URL công khai
        data = {
            'url': image_path_or_url,
            'caption': caption,
            'access_token': access_token
        }
        res = requests.post(url, data=data, timeout=30)

    result = res.json()
    if res.status_code != 200 or 'error' in result:
        err_msg = result.get('error', {}).get('message', res.text)
        log_event(f"Facebook Publish Failed: {err_msg}", "ERROR")
        raise Exception(f"Facebook API Error: {err_msg}")

    post_id = result.get('id') or result.get('post_id')
    log_event(f"Đăng bài Facebook thành công (Post ID: {post_id})", "INFO")
    return {"success": True, "post_id": post_id}
