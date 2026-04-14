---
name: selenium-bot
description: Kỹ năng và công cụ toàn tập xử lý Selenium Bot trên VPS Linux (từ lúc tạo môi trường, chuẩn code, xử lý crash, đến lập lịch Crontab).
---

# Kỹ năng Toàn tập: Quy trình Selenium Bot & Crontab

Tuân thủ chặt chẽ các giai đoạn sau khi làm việc trên bất kỳ tính năng tự động hóa (Facebook, Zalo) nào của dự án này.

## Giai đoạn 1: Khởi tạo & Định chuẩn Môi trường
- **Không tự dán thư viện thủ công**. Luôn kiểm tra và cài đặt qua file danh sách: `resources/requirements.txt`
- Sử dụng công cụ tự động hóa khởi tạo venv nếu cần thiết: `scripts/setup_env.sh`
- **Tình trạng Credentials**: Bắt buộc phải có file Google Service Account JSON trong thư mục gốc để đọc/ghi Google Sheet.
  - Tên file hiện tại: `gen-lang-client-0450618162-54ea7d476a02.json`
  - *Lưu ý*: Không được xóa file này vì nó chứa quyền truy cập API.

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

## Giai đoạn 5: Upload Ảnh vào Bài Đăng Facebook Group

### ❌ BUG: 2 Modal Chồng Nhau Khi Click Nút "Ảnh/Video"

**Triệu chứng:** Script mở 2 modal cùng lúc — Modal 1 (Create Post) + Modal 2 (Photo Picker) → bot bị kẹt, ảnh không attach, bài đăng thất bại.

**Nguyên nhân:** Click vào nút **"Ảnh/Video"** bên trong Create Post dialog khiến Facebook mở thêm một Photo Picker dialog mới đè lên.

```python
# ❌ ĐỪNG LÀM NÀY — gây ra modal thứ 2
photo_btn = driver.find_element(By.XPATH, "//div[@role='dialog']//*[@aria-label='Ảnh/video']")
photo_btn.click()  # → mở Modal 2 đè lên Modal 1
```

### ✅ Cách Fix Đúng: send_keys Trực Tiếp Vào Hidden File Input

Facebook **luôn nhúng sẵn** `input[type='file']` ẩn bên trong Create Post dialog.  
Chỉ cần **unhide** nó bằng JS rồi **send_keys** đường dẫn file — **không cần click nút "Ảnh/Video"**.

```python
def upload_image_direct(driver, img_path):
    # Bước 1: Tìm file input TRONG dialog (không toàn trang để tránh nhầm)
    dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
    file_inputs = dialog.find_elements(By.CSS_SELECTOR, "input[type='file']")

    if not file_inputs:  # Fallback toàn trang
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

    # Bước 2: Unhide rồi send_keys (KHÔNG click → KHÔNG mở modal mới)
    for fi in reversed(file_inputs):
        try:
            driver.execute_script("""
                var el = arguments[0];
                el.style.display = 'block';
                el.style.visibility = 'visible';
                el.style.opacity = '1';
                el.style.position = 'fixed';
                el.style.top = '0'; el.style.left = '0';
                el.style.width = '1px'; el.style.height = '1px';
                el.style.zIndex = '-1';
            """, fi)
            fi.send_keys(img_path)  # Đường dẫn tuyệt đối
            break
        except:
            continue

    # Bước 3: Poll xác nhận ảnh đã attach (thumbnail blob: hoặc nút "Gỡ" xuất hiện)
    for _ in range(30):
        time.sleep(1.5)
        indicators = driver.find_elements(
            By.XPATH,
            "//div[@role='dialog']//img[contains(@src,'blob:') or contains(@src,'scontent')]"
            " | //div[@role='dialog']//*[@aria-label='Gỡ' or @aria-label='Remove']"
        )
        if indicators:
            print("✅ Ảnh đã attach thành công!")
            break
```

### Quy Trình Flow Chuẩn Đăng Group Có Ảnh

```
1. driver.get("https://www.facebook.com/groups/feed/#")
2. Tìm kiếm nhóm → Enter → click tab "Nhóm" → click "Truy cập"
3. Click "Bạn viết gì đi..." → Modal 1 mở (DUY NHẤT)
4. Gõ text: send_keys() + JS execCommand('insertText') để giữ React state & emoji
5. Upload ảnh: unhide hidden input[type=file] → send_keys(img_path)  ← KHÔNG click nút Ảnh/Video
6. Poll xác nhận ảnh attach (blob: src hoặc nút "Gỡ")
7. Click nút Đăng (aria-label='Đăng', not aria-disabled='true')
```

### Bảng Lưu Ý Nhanh

| Vấn đề | Giải pháp |
|--------|-----------|
| Click "Ảnh/Video" mở modal thứ 2 | ❌ KHÔNG click — send_keys vào hidden input |
| `input[type='file']` bị hidden | JS unhide trước khi send_keys |
| React không nhận text từ JS thuần | Kết hợp send_keys → JS execCommand('insertText') |
| Emoji bị lỗi ChromeDriver (non-BMP) | Lọc emoji khi send_keys, dùng JS cho full content kèm emoji |
| Ảnh chưa load xong đã bấm Đăng | Poll blob:/scontent src hoặc nút "Gỡ" (tối đa 45s) |
| Tìm nhầm input[type=file] ngoài dialog | Luôn tìm trong scope `//div[@role='dialog']` trước |
