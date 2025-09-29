import json
import time
import re
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from tqdm import tqdm
import urllib.parse

# ----------------- 설정 -----------------
INPUT_JSONL = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[4]tour_places_summarized_filled.jsonl"
OUTPUT_JSONL = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[5]tour_places_with_naver_info.jsonl"

# 검색 지연 시간 (초) - 너무 빠르면 차단될 수 있음
SEARCH_DELAY = 1


def setup_driver():
    """Chrome 드라이버 설정"""
    options = Options()
    # 헤드리스 모드 (브라우저 창 안 보이게) - 디버깅시에는 주석처리
    # options.add_argument('--headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # User Agent 설정
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def search_naver_place(driver, place_name, address=None):
    """네이버에서 장소 검색하여 place_id와 URL 추출"""
    try:
        # 검색어 조합 (장소명 + 주소 일부)
        search_query = place_name
        if address:
            # 주소에서 시/도/군/구 정보만 추가
            addr_parts = address.split()
            if len(addr_parts) >= 2:
                search_query += f" {addr_parts[0]} {addr_parts[1]}"

        print(f"🔍 검색어: {search_query}")

        # 네이버 검색 페이지로 이동
        search_url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(search_query)}"
        driver.get(search_url)

        # 로딩 대기
        time.sleep(2)

        # 플레이스 검색 결과 찾기 (여러 패턴 시도)
        place_selectors = [
            "a[href*='place/']",  # 기본 플레이스 링크
            "a[href*='map.naver.com/v5/search']",  # 지도 검색 결과
            ".place_bluelink a",  # 플레이스 블루링크
            ".total_tit a",  # 통합검색 제목
        ]

        place_url = None
        place_id = None

        for selector in place_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    href = element.get_attribute("href")
                    if href and ("place/" in href or "map.naver.com" in href):
                        place_url = href

                        # place_id 추출
                        place_id_match = re.search(r"place/(\d+)", href)
                        if place_id_match:
                            place_id = place_id_match.group(1)
                            print(f"✅ 발견: place_id={place_id}, url={place_url}")
                            return place_id, place_url

                        # 지도 URL에서 place_id 추출 시도
                        if "map.naver.com" in href:
                            # 지도 페이지로 이동하여 place_id 추출
                            driver.get(href)
                            time.sleep(3)
                            current_url = driver.current_url
                            place_id_match = re.search(r"place/(\d+)", current_url)
                            if place_id_match:
                                place_id = place_id_match.group(1)
                                place_url = current_url
                                print(
                                    f"✅ 지도에서 발견: place_id={place_id}, url={place_url}"
                                )
                                return place_id, place_url

                        break

                if place_url:
                    break

            except Exception as e:
                continue

        # 직접 네이버 지도에서 검색 시도
        if not place_id:
            print("📍 네이버 지도에서 직접 검색 시도...")
            map_search_url = (
                f"https://map.naver.com/v5/search/{urllib.parse.quote(search_query)}"
            )
            driver.get(map_search_url)
            time.sleep(3)

            # 검색 결과 첫 번째 항목 클릭 시도
            try:
                first_result = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (
                            By.CSS_SELECTOR,
                            "li[data-id] a, .item_title a, .place_bluelink",
                        )
                    )
                )
                first_result.click()
                time.sleep(3)

                current_url = driver.current_url
                place_id_match = re.search(r"place/(\d+)", current_url)
                if place_id_match:
                    place_id = place_id_match.group(1)
                    place_url = current_url
                    print(
                        f"✅ 지도 검색에서 발견: place_id={place_id}, url={place_url}"
                    )
                    return place_id, place_url

            except TimeoutException:
                pass

        if not place_id:
            print("❌ 검색 결과 없음")
            return None, None

    except Exception as e:
        print(f"❌ 검색 오류: {str(e)}")
        return None, None


def process_jsonl():
    """JSONL 파일 처리"""
    driver = setup_driver()

    try:
        processed = 0
        found = 0
        not_found = 0
        errors = 0

        with open(INPUT_JSONL, "r", encoding="utf-8") as infile, open(
            OUTPUT_JSONL, "w", encoding="utf-8"
        ) as outfile:

            lines = list(infile)
            print(f"📊 총 처리할 항목: {len(lines)}개")

            for i, line in enumerate(tqdm(lines, desc="🔍 네이버 플레이스 검색")):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                    place_name = record.get("place_name", "")
                    address = record.get("address", "")

                    if not place_name:
                        print(f"⚠️ place_name이 없음 (라인 {i+1})")
                        outfile.write(line)
                        continue

                    print(f"\n📍 처리중 ({i+1}/{len(lines)}): {place_name}")

                    # 이미 place_id가 있으면 스킵 (선택적)
                    if record.get("place_id") and record.get("url"):
                        print("✅ 이미 정보가 있음 - 스킵")
                        outfile.write(line)
                        continue

                    # 네이버에서 검색
                    place_id, place_url = search_naver_place(
                        driver, place_name, address
                    )

                    if place_id and place_url:
                        record["place_id"] = place_id
                        record["url"] = place_url
                        found += 1
                        print(f"✅ 성공: {place_name} -> {place_id}")
                    else:
                        not_found += 1
                        print(f"❌ 실패: {place_name}")

                    processed += 1

                    # 수정된 레코드 저장
                    outfile.write(json.dumps(record, ensure_ascii=False) + "\n")

                    # 검색 간격 대기
                    time.sleep(SEARCH_DELAY)

                except json.JSONDecodeError as e:
                    print(f"❌ JSON 파싱 오류 (라인 {i+1}): {e}")
                    outfile.write(line)
                    errors += 1
                except Exception as e:
                    print(f"❌ 처리 오류 (라인 {i+1}): {e}")
                    outfile.write(line)
                    errors += 1

        print("\n" + "=" * 60)
        print("🎉 완료!")
        print(f"📊 결과 통계:")
        print(f"   - 총 처리: {processed}개")
        print(f"   - 성공: {found}개")
        print(f"   - 실패: {not_found}개")
        print(f"   - 오류: {errors}개")
        print(f"📁 저장 위치: {OUTPUT_JSONL}")
        print("=" * 60)

    finally:
        driver.quit()


def test_single_search():
    """단일 검색 테스트"""
    driver = setup_driver()
    try:
        place_name = "등명해변"
        address = "강원특별자치도 강릉시 강동면 정동진리"

        print(f"🧪 테스트 검색: {place_name}")
        place_id, place_url = search_naver_place(driver, place_name, address)

        if place_id:
            print(f"✅ 테스트 성공!")
            print(f"   place_id: {place_id}")
            print(f"   url: {place_url}")
        else:
            print("❌ 테스트 실패")

    finally:
        driver.quit()


if __name__ == "__main__":
    print("🚀 네이버 플레이스 크롤러 시작")
    print("=" * 60)

    # 테스트 먼저 실행할지 선택
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_single_search()
    else:
        process_jsonl()
