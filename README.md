# ⚡ SN Content Flow

**Hệ thống tự động đồng bộ ảnh từ Google Drive và xuất bản đa kênh mạng xã hội (Facebook Page, Instagram Business, TikTok) theo lịch trình tuỳ biến.**

Được thiết kế tinh gọn, tối ưu tài nguyên cho **Raspberry Pi 4**, tích hợp Web Dashboard trực quan và cơ chế chạy ngầm qua `systemd`.

---

## 🌟 Tính Năng Nổi Bật

- **Tự động đồng bộ Google Drive:** Quét folder ảnh theo chu kỳ (mặc định 30 phút), tự động nạp ảnh mới vào hàng đợi (Queue).
- **Lập lịch xuất bản thông minh:** Đăng bài tự động theo biểu thức Crontab hoặc khoảng cách giờ tùy biến (ví dụ: 09h, 15h, 20h mỗi ngày).
- **Hỗ trợ đa nền tảng:**
  - 📘 **Facebook Page:** Đăng ảnh kèm caption qua Graph API v19+.
  - 📸 **Instagram Business:** Đăng bài 2 bước chuẩn Meta Content Publishing API.
  - 🎵 **TikTok:** Hỗ trợ định dạng Photo Mode Carousel qua TikTok Content Posting API.
- **Web Dashboard Trực Quan:**
  - Giám sát trạng thái hàng đợi, xem trước ảnh, chỉnh sửa caption, bật/tắt kênh đăng từng bài.
  - Cấu hình API, ID kênh và lịch trình trực tiếp từ giao diện web.
  - Nhật ký hoạt động (Live Logs) theo dõi realtime.
  - Quick Actions: "Đồng bộ Drive ngay" và "Đăng ngay bài kế tiếp".

---

## 📁 Cấu Trúc Dự Án

```
sn-content-flow/
├── app/
│   ├── config.py           # Đọc biến môi trường & đường dẫn
│   ├── database.py         # SQLite database (settings, posts, logs)
│   ├── scheduler.py        # APScheduler quản lý job quét & đăng bài
│   ├── main.py             # FastAPI REST API & Web Server
│   ├── services/
│   │   ├── google_drive.py # Tích hợp Google Drive API (Service Account)
│   │   ├── facebook.py     # Đăng bài Facebook Page qua Meta Graph API
│   │   ├── instagram.py    # Đăng bài Instagram Business API
│   │   └── tiktok.py       # Đăng ảnh qua TikTok Posting API
│   └── static/             # Giao diện Web Dashboard (HTML/CSS/JS)
├── scripts/
│   └── sn-content.service  # File cấu hình chạy ngầm Systemd
├── .env.example            # Mẫu biến môi trường
├── requirements.txt        # Thư viện phụ thuộc Python
└── README.md
```

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Trên Raspberry Pi

### 1. Cài đặt môi trường ảo (Virtualenv)
```bash
cd /home/bang/project/sn-content-flow

# Khởi tạo venv qua uv hoặc python3
uv venv .venv
source .venv/bin/activate

# Cài đặt dependencies
uv pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường
Sao chép file `.env.example` thành `.env`:
```bash
cp .env.example .env
```
Điền các thông tin:
- `GOOGLE_DRIVE_FOLDER_ID`: ID thư mục Drive chứa ảnh.
- File `credentials.json`: Đặt file Service Account tải từ Google Cloud Console vào thư mục gốc dự án.
- Thông tin Meta (`FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `INSTAGRAM_ACCOUNT_ID`).
- Thông tin TikTok nếu có.

*(Lưu ý: Mọi thông tin trên cũng có thể nhập và lưu trực tiếp từ Web Dashboard)*

### 3. Khởi chạy thử nghiệm
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8082 --reload
```
Truy cập giao diện: `http://localhost:8082`

---

## 🛠 Vận Hành Chạy Ngầm Bằng Systemd

Cài đặt service vào hệ thống:
```bash
sudo cp scripts/sn-content.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sn-content.service
```

Kiểm tra trạng thái:
```bash
sudo systemctl status sn-content.service
```

---

## 🌐 Public Ra Ngoài Internet (Cloudflare Tunnel)

Thêm ingress rule vào `/etc/cloudflared/config.yml`:
```yaml
ingress:
  - hostname: sn.bepnhoso20.io.vn
    service: http://localhost:8082
```
Restart tunnel:
```bash
sudo systemctl restart cloudflared.service
```
