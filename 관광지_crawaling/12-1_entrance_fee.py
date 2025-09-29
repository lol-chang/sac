import json
import time
import random
import re
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.common.by import By


INPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[12-0]store_hours.jsonl"
OUTPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[12-1]entrance_fee.jsonl"


def setup_driver(mobile=False):
    """웹드라이버 설정 (mobile=True면 모바일 UA 강제)"""
    options = webdriver.ChromeOptions()
    if mobile:
        ua = (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile Safari/604.1"
        )
    else:
        ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

    options.add_argument(f"--user-agent={ua}")
    options.add_argument("--headless")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--log-level=3")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    return driver


def extract_price_info_mobile(driver, url):
    """모바일 페이지에서 입장료/가격 정보 추출"""
    driver.get(url)
    time.sleep(2)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)

    try:
        menu_items = driver.find_elements(By.CSS_SELECTOR, "ul.jnwQZ li.gHmZ_")
        results = []
        for item in menu_items:
            try:
                name = item.find_element(By.CSS_SELECTOR, "div.ds3HZ").text.strip()
            except:
                name = "입장료"
            try:
                price = item.find_element(By.CSS_SELECTOR, "div.mkBm3").text.strip()
            except:
                price = ""
            if price:
                results.append(f"{name}: {price}")
        return results if results else None
    except:
        return None


def get_entrance_fee(url, driver_m):
    """입장료 정보만 추출"""
    match = re.search(r"/restaurant/(\d+)", url)
    if not match:
        return None
    place_id = match.group(1)
    mobile_url = f"https://m.place.naver.com/restaurant/{place_id}/home"
    return extract_price_info_mobile(driver_m, mobile_url)


def process_jsonl(input_path, output_path):
    driver_m = setup_driver(mobile=True)

    try:
        with open(input_path, "r", encoding="utf-8") as infile:
            lines = [line.strip() for line in infile if line.strip()]

        with open(output_path, "w", encoding="utf-8") as outfile:
            for i, line in enumerate(tqdm(lines, desc="크롤링 중")):
                data = json.loads(line)
                url = data.get("url", "")
                if url:
                    entrance_fee = get_entrance_fee(url, driver_m)
                else:
                    entrance_fee = None

                # ✅ 운영시간(store_hours) 제거하고 entrance_fee만 저장
                data["entrance_fee"] = entrance_fee
                if "store_hours" in data:
                    data.pop("store_hours")

                print(
                    f"[{i+1}/{len(lines)}] {data.get('place_name','')} entrance_fee: {entrance_fee}"
                )

                outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
                time.sleep(random.uniform(1, 2))
    finally:
        driver_m.quit()


if __name__ == "__main__":
    process_jsonl(INPUT_PATH, OUTPUT_PATH)
