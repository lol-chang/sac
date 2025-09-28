import time
import pandas as pd
from openpyxl import load_workbook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

INPUT_XLSX_PATH = "debugging_placeid_list.xlsx"

def get_real_store_name_from_url(url: str, driver, wait) -> str | None:
    try:
        driver.get(url)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "GHAhO")))
        name_elem = driver.find_element(By.CLASS_NAME, "GHAhO")
        return name_elem.text.strip()
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def fix_wrong_store_names():
    print("🚀 수정 시작")
    df = pd.read_excel(INPUT_XLSX_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)

    corrected = 0
    for i, row in df.iterrows():
        name = str(row['store_name']).strip()
        url = row['store_url_naver']
        if name == "이미지수" and isinstance(url, str) and url.startswith("https://"):
            print(f"\n🔍 [{i+1}] 잘못된 이름 수정 시도 → {url}")
            real_name = get_real_store_name_from_url(url, driver, wait)
            if real_name:
                df.at[i, 'store_name'] = real_name
                print(f"✅ 수정됨: '이미지수' → '{real_name}'")
                corrected += 1
            else:
                print("⛔ 상호명 추출 실패")

            time.sleep(0.5)

    driver.quit()

    if corrected:
        df.to_excel(INPUT_XLSX_PATH, index=False)
        print(f"\n💾 저장 완료: {corrected}건 수정됨")
    else:
        print("⚠️ 수정할 항목이 없거나 실패함")

if __name__ == "__main__":
    fix_wrong_store_names()
