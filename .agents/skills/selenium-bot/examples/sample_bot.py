import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_driver(profile_path):
    # 1. Luôn ép buộc X11 Display
    os.environ["DISPLAY"] = ":10.0"
    
    # 2. Options bắt buộc cho VPS Linux
    options = Options()
    options.binary_location = "/usr/bin/google-chrome"
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--start-maximized")
    options.add_experimental_option("detach", True)

    return webdriver.Chrome(options=options)

def main():
    profile = os.path.join(os.getcwd(), "bot-profile")
    driver = get_driver(profile)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get("https://example.com")
        
        # 3. Kỹ thuật chờ và click dự phòng
        element = wait.until(EC.element_to_be_clickable((By.TAG_NAME, "h1")))
        try:
            element.click()
        except:
            driver.execute_script("arguments[0].click();", element)
            
        print("Tương tác thành công!")
    except Exception as e:
        driver.save_screenshot("error_snap.png")
        print(f"Lỗi, đã lưu ảnh: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
