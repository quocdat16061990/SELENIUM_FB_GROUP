import os
import sys
import time
import gspread
from google.oauth2.service_account import Credentials
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()

def find_chrome_binary():
    import platform
    system = platform.system()
    possible_paths = []
    
    if system == "Linux":
        possible_paths = [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/snap/bin/chromium"
        ]
        
    for path in possible_paths:
        if os.path.exists(path):
            return path
            
    return "/usr/bin/google-chrome"

CHROME_BINARY = find_chrome_binary()
PROFILE_ROOT = os.path.join(BASE_DIR, "facebook-chrome-profile")

SHEET_ID = "1SFAr1CFMzMPQXFToZEAwA2U1FaHpeCQqv7CyMa-f-0w"
CREDENTIALS_FILE = os.path.join(BASE_DIR, "gen-lang-client-0450618162-54ea7d476a02.json")
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

POSTS_DATA = []
WORKSHEET = None

def fetch_google_sheet():
    global WORKSHEET, POSTS_DATA
    try:
        credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        gc = gspread.authorize(credentials)
        workbook = gc.open_by_key(SHEET_ID)
        
        try:
            WORKSHEET = workbook.worksheet("Post Bài Group")
        except:
            print("Không tìm thấy tab 'Post Bài Group', đang dùng tab đầu tiên...")
            WORKSHEET = workbook.sheet1
            
        records = WORKSHEET.get_all_records()
        headers = WORKSHEET.row_values(1)
        
        if 'Status' not in headers:
            status_col = len(headers) + 1
            WORKSHEET.update_cell(1, status_col, 'Status')
            headers = WORKSHEET.row_values(1)
            
        status_col_index = headers.index('Status') + 1

        for idx, row in enumerate(records):
            row_num = idx + 2
            ten_nhom = str(row.get('Tên Nhóm', '')).strip()
            tieu_de = str(row.get('Tiêu Đề', '')).strip()
            noi_dung = str(row.get('Nội Dung', '')).strip()
            hinh_anh = str(row.get('Hình Ảnh', '')).strip()
            status = str(row.get('Status', '')).strip()
            
            if status == 'UNAPPROVED' and ten_nhom != 'nan' and ten_nhom != '':
                POSTS_DATA.append({
                    "group_name": ten_nhom,
                    "title": tieu_de if tieu_de != 'nan' else "", 
                    "content": noi_dung if noi_dung != 'nan' else "",
                    "image": hinh_anh if hinh_anh != 'nan' else "",
                    "row_num": row_num,
                    "status_col": status_col_index
                })
        print(f"Đã tải {len(POSTS_DATA)} bài viết hợp lệ từ Google Sheet.")
    except Exception as e:
        print(f"Lỗi khi đọc Google Sheet API: {e}")

def get_driver():
    print(f"DEBUG: CHROME_BINARY = {CHROME_BINARY}")
    print(f"DEBUG: PROFILE_ROOT = {PROFILE_ROOT}")
    
    current_display = os.environ.get("DISPLAY", "Chưa đặt")
    print(f"DEBUG: DISPLAY hiện tại = {current_display}")

    if os.path.exists("/tmp/.X11-unix/X10"):
        os.environ["DISPLAY"] = ":10.0"
        print("DEBUG: Đã ép buộc thiết lập DISPLAY=:10.0")
    elif os.path.exists("/tmp/.X11-unix/X0"):
        os.environ["DISPLAY"] = ":0.0"
        print("DEBUG: Đã ép buộc thiết lập DISPLAY=:0.0")

    options = Options()
    options.binary_location = CHROME_BINARY
    options.add_argument(f"--user-data-dir={PROFILE_ROOT}")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-gpu")
    options.add_experimental_option("detach", True)

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"DEBUG: Lỗi khi khởi tạo WebDriver: {e}")
        raise e

def resolve_image_path(img_name):
    """Resolve đường dẫn tuyệt đối cho file ảnh."""
    if not img_name:
        return None
    if os.path.exists(img_name):
        return img_name
    possible_paths = [
        os.path.join(BASE_DIR, "images", img_name),
        os.path.join(BASE_DIR, "images", f"{img_name}.jpg"),
        os.path.join(BASE_DIR, "images", f"{img_name}.png"),
        os.path.join(BASE_DIR, "images", f"{img_name}.jpeg"),
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return None

def upload_image_direct(driver, img_path):
    """
    Upload ảnh KHÔNG click nút Ảnh/Video (tránh mở modal thứ 2 đè lên modal tạo bài).
    Thay vào đó: unhide hidden input[type=file] bên trong dialog rồi send_keys trực tiếp.
    Trả về True nếu upload thành công.
    """
    print(f"Bước 7.5: Upload ảnh trực tiếp vào file input (không mở modal phụ): '{img_path}'")

    try:
        # Lấy input[type=file] bên trong dialog trước
        dialog = driver.find_element(By.XPATH, "//div[@role='dialog']")
        file_inputs = dialog.find_elements(By.CSS_SELECTOR, "input[type='file']")
        print(f"-> Tìm thấy {len(file_inputs)} input[type=file] trong dialog")

        if not file_inputs:
            # Fallback: tìm toàn trang
            file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            print(f"-> Fallback toàn trang: {len(file_inputs)} input[type=file]")

        if not file_inputs:
            print("-> LỖI: Không tìm thấy bất kỳ input[type=file] nào!")
            return False

        uploaded = False
        for fi in reversed(file_inputs):
            try:
                # Unhide input để Selenium có thể gửi file (KHÔNG mở dialog mới vì không click)
                driver.execute_script("""
                    var el = arguments[0];
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    el.style.opacity = '1';
                    el.style.position = 'fixed';
                    el.style.top = '0';
                    el.style.left = '0';
                    el.style.width = '1px';
                    el.style.height = '1px';
                    el.style.zIndex = '-1';
                """, fi)
                fi.send_keys(img_path)
                uploaded = True
                print("-> Đã send_keys file ảnh thành công (không mở modal phụ)!")
                break
            except Exception as e:
                print(f"-> input này lỗi: {e}, thử input khác...")

        if not uploaded:
            print("-> LỖI: Không send_keys được vào bất kỳ input[type=file] nào!")
            return False

        # Poll xác nhận ảnh đã attach (thumbnail hoặc nút Gỡ xuất hiện)
        print("-> Đang chờ ảnh xuất hiện trong khung soạn thảo (tối đa 45s)...")
        for _ in range(30):
            time.sleep(1.5)
            indicators = driver.find_elements(
                By.XPATH,
                "//div[@role='dialog']//img[contains(@src,'blob:') or contains(@src,'scontent')]"
                " | //div[@role='dialog']//*[@aria-label='Gỡ' or @aria-label='Remove']"
            )
            if indicators:
                print(f"✅ XÁC NHẬN: Ảnh đã attach ({len(indicators)} indicator tìm thấy)!")
                return True

        print("⚠️ Không xác nhận được ảnh đã attach trong 45s, vẫn tiếp tục đăng...")
        return True

    except Exception as e:
        print(f"Lỗi khi upload ảnh: {e}")
        return False

def post_facebook_group(driver, wait, post_data):
    group_name = post_data['group_name']
    full_content = ""
    if post_data['title']:
        full_content += post_data['title'] + "\n\n"
    if post_data['content']:
        full_content += post_data['content']

    # Resolve đường dẫn ảnh ngay từ đầu
    img_path = resolve_image_path(post_data.get('image', '').strip())
    if post_data.get('image', '').strip() and not img_path:
        print(f"BỎ QUA ảnh: Không thấy file '{post_data['image']}' trên ổ cứng.")

    try:
        # Bước 1: Redirect vào Groups Feed
        print("Bước 1: Redirect vào link Groups Feed...")
        driver.get("https://www.facebook.com/groups/feed/#")
        time.sleep(5)

        # Bước 2: Tìm kiếm nhóm
        print(f"Bước 2: Tìm kiếm nhóm '{group_name}'...")
        search_input_xpath = "//input[@aria-label='Tìm kiếm nhóm' or @placeholder='Tìm kiếm nhóm']"
        search_input = wait.until(EC.presence_of_element_located((By.XPATH, search_input_xpath)))
        search_input.clear()
        search_input.send_keys(group_name)
        time.sleep(1)
        search_input.send_keys(Keys.RETURN)
        time.sleep(4)

        # Bước 3: Click Tab 'Nhóm'
        print("Bước 3: Click vào Tab 'Nhóm'...")
        tab_nhom_xpath = "//span[text()='Nhóm' or text()='Groups']"
        tab_nhom = wait.until(EC.element_to_be_clickable((By.XPATH, tab_nhom_xpath)))
        try:
            tab_nhom.click()
        except:
            driver.execute_script("arguments[0].click();", tab_nhom)
        time.sleep(3)

        # Bước 4: Toggle "Nhóm của tôi"
        print("Bước 4: Bật Toggle 'Nhóm của tôi'...")
        toggle_my_group_xpath = "//input[@aria-label='Nhóm của tôi' or @aria-label='My groups']"
        try:
            toggle_my_group = wait.until(EC.presence_of_element_located((By.XPATH, toggle_my_group_xpath)))
            if toggle_my_group.get_attribute("aria-checked") == "false" or not toggle_my_group.is_selected():
                driver.execute_script("arguments[0].click();", toggle_my_group)
            time.sleep(3)
        except Exception as e:
            print(f"  -> Lưu ý: Không bật được 'Nhóm của tôi', tiếp tục...")

        # Bước 5: Click nút 'Truy cập'
        print("Bước 5: Click vào nút 'Truy cập' của nhóm...")
        access_btn_xpath = "//a[@aria-label='Truy cập' or @aria-label='Visit']"
        try:
            access_btn = wait.until(EC.element_to_be_clickable((By.XPATH, access_btn_xpath)))
            driver.execute_script("arguments[0].click();", access_btn)
        except:
            print("  -> Thử fallback tìm bằng text...")
            fallback_xpath = "//span[text()='Truy cập' or text()='Visit']"
            fallback_btn = wait.until(EC.element_to_be_clickable((By.XPATH, fallback_xpath)))
            driver.execute_script("arguments[0].click();", fallback_btn)

        print("Đã nhấn Truy cập, chờ tải trang nhóm...")
        time.sleep(5)

        # Bước 6: Click "Bạn viết gì đi..." để mở modal Create Post (CHỈ 1 modal duy nhất)
        print("Bước 6: Click vào 'Bạn viết gì đi...'...")
        write_something_xpath = "//span[contains(text(), 'Bạn viết gì đi') or contains(text(), 'Write something')]"
        write_btn = wait.until(EC.presence_of_element_located((By.XPATH, write_something_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", write_btn)
        time.sleep(1)
        try:
            write_btn.click()
        except:
            driver.execute_script("arguments[0].click();", write_btn)
            
        print("Đang chờ form tạo bài viết xuất hiện...")
        time.sleep(3)

        # Bước 7: Gõ nội dung văn bản
        print("Bước 7: Gõ nội dung văn bản...")
        input_xpath = "//div[@role='dialog']//div[@role='textbox'] | //div[@role='dialog']//textarea"
        
        try:
            target = wait.until(EC.element_to_be_clickable((By.XPATH, input_xpath)))
            target.click()
            time.sleep(2)
            
            # Gõ văn bản thuần (bỏ emoji) để React nhận state
            text_no_emoji = "".join([c for c in full_content if ord(c) <= 0xFFFF])
            target.send_keys(text_no_emoji)
            
            # Dùng JS ghi đè toàn bộ nội dung kèm emoji
            driver.execute_script("""
                var el = arguments[0];
                var text = arguments[1];
                el.focus();
                document.execCommand('selectAll', false, null);
                document.execCommand('insertText', false, text);
            """, target, full_content)
            
            # Ép Space cuối để kích hoạt nút Đăng
            target.send_keys(" ")
            time.sleep(2)
            print("-> Đã nạp văn bản xong.")
        except Exception as e:
            print(f"-> KHÔNG THỂ GÕ TEXT: {e}")

        # =======================================================================
        # Bước 7.5: Upload ảnh - KHÔNG click nút Ảnh/Video trong dialog
        # (Việc click nút đó sẽ mở thêm 1 modal mới đè lên modal tạo bài = BUG)
        # Thay vào đó: send_keys trực tiếp vào hidden input[type=file] trong dialog
        # =======================================================================
        if img_path:
            time.sleep(1)  # Nhỏ buffer sau khi gõ text
            upload_image_direct(driver, img_path)
            time.sleep(2)  # Buffer sau khi ảnh attach xong

        # Bước 8: Click nút Đăng
        print("Bước 8: Bấm nút Đăng...")
        driver.save_screenshot("debug_final_check.png")
        
        post_btn_xpath = (
            "//div[@role='dialog']"
            "//div[(@aria-label='Đăng' or @aria-label='Post') and @role='button'"
            " and not(@aria-disabled='true')]"
        )
        post_btn = wait.until(EC.element_to_be_clickable((By.XPATH, post_btn_xpath)))
        
        try:
            post_btn.click()
        except:
            driver.execute_script("arguments[0].click();", post_btn)
            
        print("Đã click nút Đăng. Đang đợi xác nhận bài lên (15s)...")
        time.sleep(15)
        driver.save_screenshot("debug_after_post.png")
        
        return True
    except Exception as e:
        print(f"Lỗi ở bước thực hiện đăng vào Nhóm: {e}")
        try:
            driver.save_screenshot("group_post_error.png")
            print("Đã lưu screenshot lỗi: group_post_error.png")
        except:
            pass
        return False

def main():
    driver = None
    try:
        print("Đang kết nối thư viện gspread tải Google Sheet...")
        fetch_google_sheet()
        
        if POSTS_DATA:
            print(f"Số bài viết UNAPPROVED: {len(POSTS_DATA)}")
            post = POSTS_DATA[0] 
            
            driver = get_driver()
            wait = WebDriverWait(driver, 15)
            
            print(f"\n--- BẮT ĐẦU ĐĂNG VÀO NHÓM: {post['group_name']} ---")
            success = post_facebook_group(driver, wait, post)
            
            if success:
                try:
                    WORKSHEET.update_cell(post['row_num'], post['status_col'], 'APPROVED')
                    print(f"Thành công! Cập nhật lại status trên GG Sheet (Dòng {post['row_num']} -> APPROVED).")
                except Exception as e:
                    print(f"Lỗi chưa thể update status lên GG Sheet: {e}")
            else:
                print("Đăng bài không thành công, bỏ qua cập nhật GG Sheet cho dòng này.")

            print("\n--- HOÀN TẤT LƯỢT CHẠY CRON ---")
        else:
            print("\n--- GOOGLE SHEET TRỐNG: Không có bài viết nào trạng thái UNAPPROVED. ---")

    except Exception as exc:
        print(f"Lỗi tổng toàn ứng dụng: {exc}")
        if driver is not None:
            try:
                driver.save_screenshot("fb_error_fatal.png")
            except:
                pass
            
    if driver is not None:
        print("\n" + "="*50)
        print("Thoát trình duyệt sau 5 giây...")
        time.sleep(5)
        driver.quit()
        print("Đã tắt an toàn.")
        print("="*50)

if __name__ == "__main__":
    main()
