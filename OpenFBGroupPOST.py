import os
import sys
import time
import pandas as pd
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
# Trỏ về thư mục profile đã được nhân bản cục bộ để tránh đụng độ (file lock) với file OpenFBV2POST.py đang chạy song song
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
        
        # Thêm cột Status nếu chưa có
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
            status = str(row.get('Status', '')).strip()
            
            # Chỉ xử lý các bài ở trạng thái UNAPPROVED và có Tên Nhóm
            if status == 'UNAPPROVED' and ten_nhom != 'nan' and ten_nhom != '':
                POSTS_DATA.append({
                    "group_name": ten_nhom,
                    "title": tieu_de if tieu_de != 'nan' else "", 
                    "content": noi_dung if noi_dung != 'nan' else "",
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

def post_facebook_group(driver, wait, post_data):
    group_name = post_data['group_name']
    full_content = ""
    if post_data['title']:
        full_content += post_data['title'] + "\n\n"
    if post_data['content']:
        full_content += post_data['content']

    try:
        # Bước 1: Redicrect vào link
        print("Bước 1: Redirect vào link Groups Feed...")
        driver.get("https://www.facebook.com/groups/feed/#")
        time.sleep(5)

        # Bước 2: Click vào Tìm Kiếm Nhóm
        print(f"Bước 2: Tìm kiếm nhóm '{group_name}'...")
        # Tìm input dựa vào aria-label hoặc attribute như user yêu cầu
        search_input_xpath = "//input[@aria-label='Tìm kiếm nhóm' or @placeholder='Tìm kiếm nhóm']"
        search_input = wait.until(EC.presence_of_element_located((By.XPATH, search_input_xpath)))
        search_input.clear()
        search_input.send_keys(group_name)
        time.sleep(1)
        search_input.send_keys(Keys.RETURN)
        time.sleep(4)

        # Bước 3: Click vào thẻ có chữ Nhóm (chọn bộ lọc Nhóm)
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
            print(f"  -> Lưu ý: Không thể bật 'Nhóm của tôi' (Có thể đã bật sẵn hoặc không hiện), tiếp tục...")

        # Bước 5: Click vào thẻ có chữ "Truy cập"
        print("Bước 5: Click vào nút 'Truy cập' của nhóm...")
        access_btn_xpath = "//a[@aria-label='Truy cập' or @aria-label='Visit']"
        try:
            access_btn = wait.until(EC.element_to_be_clickable((By.XPATH, access_btn_xpath)))
            driver.execute_script("arguments[0].click();", access_btn)
        except:
            # Fallback trong trường hợp nút không nằm ở aria-label mà nằm ở span text bình thường
            print("  -> Không tìm thấy thuộc tính aria-label='Truy cập', thử tìm bằng thẻ nội dung text...")
            fallback_xpath = "//span[text()='Truy cập' or text()='Visit']"
            fallback_btn = wait.until(EC.element_to_be_clickable((By.XPATH, fallback_xpath)))
            driver.execute_script("arguments[0].click();", fallback_btn)

        print("Đã nhấn Truy cập, chờ tải trang chủ của nhóm...")
        time.sleep(5)

        # Bước 6: Click vào "Bạn viết gì đi..."
        print("Bước 6: Click vào 'Bạn viết gì đi...'...")
        write_something_xpath = "//span[contains(text(), 'Bạn viết gì đi') or contains(text(), 'Write something')]"
        write_btn = wait.until(EC.presence_of_element_located((By.XPATH, write_something_xpath)))
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", write_btn)
        time.sleep(1)
        try:
            write_btn.click()
        except:
            driver.execute_script("arguments[0].click();", write_btn)
            
        print("Đang chờ form tạo bài viết công khai xuất hiện...")
        time.sleep(3)

        # Bước 7: Điền nội dung
        print("Bước 7: Lấy thông tin từ sheet và gõ vào textarea 'Tạo bài viết công khai'...")
        # Lấy chính xác thẻ có aria-label tương ứng (hoặc textarea) để tránh nhầm lẫn vùng nhập Comment
        textarea_xpath = "//textarea[@aria-label='Tạo bài viết công khai...' or @aria-label='Create a public post...'] | //div[@role='dialog']//*[@aria-label='Tạo bài viết công khai...' or @aria-label='Create a public post...']"
        # Chúng ta dùng visibility thay vì presence để chắc chắn form đã hiện
        textarea = wait.until(EC.visibility_of_element_located((By.XPATH, textarea_xpath)))
        
        try:
            textarea.click()
        except:
            driver.execute_script("arguments[0].focus();", textarea)
        time.sleep(1)

        # Gõ trực tiếp bằng send_keys vì đây là một thẻ <textarea> chuẩn
        try:
            textarea.send_keys(full_content)
        except:
            # Fallback nếu element bị chặn phím
            js_fill = """
            arguments[0].value = arguments[1];
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """
            driver.execute_script(js_fill, textarea, full_content)
        
        print("Đã điền xong nội dung. Chờ React nhận diện chữ...")
        time.sleep(2)

        # Bước 8: Click "Đăng"
        print("Bước 8: Click nút Đăng...")
        driver.save_screenshot("debug_before_post.png")
        
        # Đặc trị lỗi aria-disabled: Bắt buộc nó ấn Space để React lưu trạng thái
        textarea.send_keys(" ")
        time.sleep(1)
        
        post_btn_xpath = "//div[(contains(@aria-label, 'Đăng') or contains(@aria-label, 'Post')) and @role='button']"
        post_btn = wait.until(EC.element_to_be_clickable((By.XPATH, post_btn_xpath)))
        
        # Kiem tra neu nút bị làm mờ bởi react
        btn_aria = post_btn.get_attribute("aria-disabled")
        print(f"DEBUG: Nút Đăng có aria-disabled = {btn_aria}")
        
        try:
            post_btn.click()
        except:
            driver.execute_script("arguments[0].click();", post_btn)
            
        print("Đã click nút Đăng. Đợi Facebook xử lý...")
        time.sleep(6) # Chờ đủ lâu để FB đăng bài
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
