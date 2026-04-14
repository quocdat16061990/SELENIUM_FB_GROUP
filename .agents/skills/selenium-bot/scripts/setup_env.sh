#!/bin/bash
# Kịch bản cài đặt môi trường cho dự án Selenium mới
PROJECT_DIR=$PWD

echo "Đang tạo môi trường ảo tại $PROJECT_DIR/venv..."
python3 -m venv venv

echo "Kích hoạt môi trường và cài đặt thư viện cơ bản..."
source venv/bin/activate

# Lấy resources requirements.txt từ thư mục skill
SKILL_REQ_PATH="$(dirname "$0")/../resources/requirements.txt"
if [ -f "$SKILL_REQ_PATH" ]; then
    pip install -r "$SKILL_REQ_PATH"
else
    # Cài đặt mặc định nếu không chia resources
    pip install selenium pandas gspread google-auth
fi

echo "Hoàn tất! Môi trường đã sẵn sàng."
