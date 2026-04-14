---
name: selenium-bot
description: Kỹ năng và công cụ toàn tập xử lý Selenium Bot trên VPS Linux (từ lúc tạo môi trường, chuẩn code, xử lý crash, đến lập lịch Crontab).
---

# Kỹ năng Toàn tập: Quy trình Selenium Bot & Crontab

Tuân thủ chặt chẽ các giai đoạn sau khi làm việc trên bất kỳ tính năng tự động hóa (Facebook, Zalo) nào của dự án này.

## Giai đoạn 1: Khởi tạo & Định chuẩn Môi trường
- **Không tự dán thư viện thủ công**. Luôn kiểm tra và cài đặt qua file danh sách: `resources/requirements.txt`
- Sử dụng công cụ tự động hóa khởi tạo venv nếu cần thiết: `scripts/setup_env.sh`

## Giai đoạn 2: Quy tắc Lập trình (Coding Standards)
Khi viết mã Selenium, bắt buộc phải tuân thủ và tham khảo tệp gốc `examples/sample_bot.py`:
1. **Tránh time.sleep():** Chỉ dùng để đợi Animation (React DOM của FB/Zalo). Các yếu tố chờ tải bình thường dùng `WebDriverWait`.
2. **Dự phòng sự cố Click:** Luôn bọc hàm click bằng khối lỗi chuẩn (normal click + JS click fallback).
3. **Hiển thị & Profile:**
   - Luôn sử dụng lại profile cũ (ví dụ: `facebook-chrome-profile`).
   - Cần ép môi trường Remote Desktop: `os.environ["DISPLAY"] = ":10.0"`.
   - Bắt buộc gắn cờ `--no-sandbox` và `--disable-dev-shm-usage` cho webdriver trên Linux.
4. **Nhập Tương Tác Text (Gõ phím):**
   - Sự khác biệt về Editor: Trang cá nhân dùng *Lexical Editor (`contenteditable`)* nên ưu tiên tiêm nội dung bằng Script (*Clipboard Event*). Ở Group có thể gặp thẻ `<textarea>` thì dùng `send_keys()` thuần túy.
   - Luôn nhớ nhấn phím trống (`send_keys(" ")`) sau khi điền nội dung để ép framework React của Facebook bỏ chặn `aria-disabled` trên nút Gửi/Đăng bài.

## Giai đoạn 3: Xử lý Lỗi Cơ Bản
- Nếu xuất hiện sự cố **Chrome instance exited** (session not created) hay màn đỏ/đen: 
   - Kiểm tra xem có 2 kịch bản cronjob hoặc 2 tiến trình khởi chạy *cùng ngắm vào một gốc Profile* (VD: `facebook-chrome-profile`) trong cùng một thời điểm hay không. Chorme khóa chặt file lưu trữ, hãy COPY thư mục profile ra cho mỗi chức năng thay vì dùng chung 1 chỗ trên máy.
   - Bác sĩ khuyên dùng lệnh `pkill -f chrome` để dọn đường và kiểm tra quyền X11 nếu tiến trình treo.
- Nếu click dính lỗi ElementClickIntercepted do Pop-up, tự động chuyển về JS Execute click ngay.

## Giai đoạn 4: Cài đặt lệnh Crontab
Không viết lệnh tay trực tiếp. Vì trên môi trường CRON không có giao diện ảo, bắt buộc phải móc hàm `export DISPLAY` lẫn `export XAUTHORITY` vào câu lệnh.
- Sử dụng script tự động để nạp: `scripts/setup_cron.sh <số-phút> <file.py>`
- Câu lệnh cron viết chuẩn ví dụ: `*/10 * * * * export DISPLAY=:10.0 && export XAUTHORITY=/home/ubuntu/.Xauthority && cd /home/ubuntu/SELENIUM_FB_GROUP && /home/ubuntu/SELENIUM_FB_GROUP/venv/bin/python FileBot.py >> cron.log 2>&1`
