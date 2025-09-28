# 이거로도 4개 안잡혀서  수작업하겠습니당
# ❌ 여전히 실패한 항목들:
#  - place_id: 15367705 / place_name: 고을식당
#  - place_id: 1581548946 / place_name: 국수나무 주문진점
#  - place_id: 1472679296 / place_name: 제비리장칼국수
#  - place_id: 1359013774 / place_name: 회산보리밥뷔페
#  따로 입력 완료 !


# [8]retry_null_address.py
import json
import re
from pathlib import Path
import sys, os, time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from tqdm import tqdm

# ========= 파일 경로 =========
INPUT_FILE  = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[8-1]data_with_address.jsonl"   # ✅ 기존 결과 파일
OUTPUT_FILE = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[8-2]data_with_address_retry.jsonl"

# ========= 드라이버 생성 =========
def make_driver(headless=False, device_scale=0.4):
    options = webdriver.ChromeOptions()
    options.add_argument('window-size=1920x1080')
    options.add_argument(f'--force-device-scale-factor={device_scale}')
    options.add_argument('disable-gpu')
    options.add_argument('--log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_argument('--disable-notifications')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    if headless:
        options.add_argument('--headless=new')

    null_log = 'NUL' if sys.platform.startswith('win') else '/dev/null'
    service = Service(log_path=null_log)

    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(2)
    return driver

# ========= 주소 파싱 로직 =========
ADDR_CANDIDATE_SELECTORS = [
    'span._1vEbY', 'span._1AJn9', 'span._2yqUQ',
    '[data-nclicks-area-code="fwy_loc"] span',
    '[data-nclicks-area-code="fwy_loc"] a',
    'div.UCuLa span', 'div.UCuLa a',
    'div.rAcDm span', 'div.rAcDm a',
]
ADDR_PATTERN = re.compile(r'(?:도|시|군|구|읍|면|동|로|길)\s*\d')

def _pick_address_text(driver):
    for sel in ADDR_CANDIDATE_SELECTORS:
        elems = driver.find_elements(By.CSS_SELECTOR, sel)
        for el in elems:
            txt = (el.text or "").strip()
            if not txt or '새 창이 열립니다' in txt or len(txt) < 5:
                continue
            if ADDR_PATTERN.search(txt):
                return txt
    return None

def scrape_address_from_place(driver, place_id: str, review_url: str | None = None) -> str | None:
    loc_url = f"https://m.place.naver.com/restaurant/{place_id}/location?entry=ple&reviewSort=recent"
    try:
        driver.get(loc_url)
    except Exception:
        if review_url:
            try:
                driver.get(review_url)
            except Exception:
                return None
        else:
            return None

    try:
        WebDriverWait(driver, 0.5).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[data-nclicks-area-code="fwy_loc"], div.UCuLa, div.rAcDm')
            )
        )
    except Exception:
        pass

    addr = _pick_address_text(driver)
    if addr:
        return addr

    try:
        container = driver.find_element(By.CSS_SELECTOR, '[data-nclicks-area-code="fwy_loc"], div.UCuLa, div.rAcDm')
        lines = [ln.strip() for ln in (container.text or "").splitlines() if ln.strip()]
        cand = [ln for ln in lines if '새 창이 열립니다' not in ln and ADDR_PATTERN.search(ln)]
        if cand:
            cand.sort(key=len, reverse=True)
            return cand[0]
    except Exception:
        pass

    return None

# ========= JSONL 재시도 처리 =========
def retry_null_addresses(input_file: str, output_file: str, headless=False):
    in_path = Path(input_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    driver = make_driver(headless=headless)

    with open(in_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    total = updated = failed = skipped = 0
    failed_items = []

    with open(out_path, 'w', encoding='utf-8') as fout, tqdm(total=len(lines), desc="Retrying", unit="line") as pbar:
        for line in lines:
            total += 1
            try:
                obj = json.loads(line)
            except:
                pbar.update(1)
                continue

            # ✅ address 가 null 인 것만 재시도
            if obj.get("address") and str(obj.get("address")).strip().lower() not in ("null", ""):
                skipped += 1
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            place_id = obj.get("place_id")
            review_url = obj.get("url")
            addr = scrape_address_from_place(driver, place_id=str(place_id), review_url=review_url)
            if addr:
                obj["address"] = addr
                updated += 1
            else:
                obj["address"] = None
                failed += 1
                failed_items.append({"place_id": place_id, "place_name": obj.get("place_name")})

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            pbar.update(1)

    driver.quit()

    print(f"\n✅ Done: {out_path}")
    print(f"총 {total}건 / 새로 채움 {updated}건 / 여전히 실패 {failed}건 / 기존 유지 {skipped}건")
    if failed_items:
        print("\n❌ 여전히 실패한 항목들:")
        for item in failed_items:
            print(f" - place_id: {item['place_id']} / place_name: {item['place_name']}")

if __name__ == "__main__":
    retry_null_addresses(INPUT_FILE, OUTPUT_FILE, headless=False)



