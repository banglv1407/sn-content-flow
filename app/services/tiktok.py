import requests
from typing import Dict, Any, List
from ..database import log_event

def publish_to_tiktok_photo(access_token: str, photo_urls: List[str], title: str, description: str = "") -> Dict[str, Any]:
    """
    Đăng bộ ảnh (Photo Mode Carousel) lên TikTok qua Content Posting API v2:
    Endpoint: POST https://open.tiktokapis.com/v2/post/publish/content/init/
    """
    if not access_token:
        raise ValueError("Chưa cấu hình TikTok Access Token")

    url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8"
    }

    payload = {
        "post_info": {
            "title": title[:150],
            "description": description[:1000],
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_duet": False,
            "disable_comment": False,
            "disable_stitch": False,
            "video_cover_timestamp_ms": 1000
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 1,
            "photo_images": photo_urls
        },
        "post_mode": "MEDIA_UPLOAD"
    }

    res = requests.post(url, json=payload, headers=headers, timeout=30)
    data = res.json()

    if res.status_code != 200 or data.get('error', {}).get('code') != 'ok':
        err = data.get('error', {}).get('message', res.text)
        log_event(f"TikTok Publish Thất bại: {err}", "ERROR")
        raise Exception(f"TikTok API Error: {err}")

    publish_id = data.get('data', {}).get('publish_id')
    log_event(f"Đăng bài TikTok khởi tạo thành công (Publish ID: {publish_id})", "INFO")
    return {"success": True, "publish_id": publish_id}
