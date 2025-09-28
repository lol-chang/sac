# ❌ 실패 항목들:
#  - place_id: 1811956729 / place_name: 감자유원지 / address: 강원 강릉시 경강로2115번길 7 1,2,3층
#  - place_id: 2041829875 / place_name: 유천가든 강릉직영점 / address: 강원 강릉시 해안로621번길 3 1, 2, 3층 유천가든 강릉직영점
#  - place_id: 1075857630 / place_name: 연자네보리밥 / address: 강원 강릉시 강릉대로 463 7, 8호
#  - place_id: 1869523471 / place_name: 강릉 조개빵 강릉본점 / address: 강원 강릉시 창해로 364 1F 강릉조개빵
#  - place_id: 15368440 / place_name: 정동진 정가네순두부 본점 / address: 강원 강릉시 강동면 헌화로 1094 1, 2층
#  - place_id: 911136265 / place_name: 정동진 고기랑조개랑 / address: 강릉 정동진 해변 부근에 위치 하였으며, 썬크루즈 호텔에서 도보 5분, 모래시계공원과  정동진 해변에서 3분, 정동진역에서는 도보로 10분 가량 소요됩니다. 또한 탑스텐 호텔과 하슬라아트월드까지 차량 픽업이 가능합니다.
#  - place_id: 1635128478 / place_name: 기와집닭칼국수 / address: 강원 강릉시 원대로 15 2,3호
#  - place_id: 1839877500 / place_name: 깐부네 / address: 강원 강릉시 옥천로 59 옥천로59 깐부네
#  - place_id: 1565348057 / place_name: 솔향한우곰탕 / address: 강원 강릉시 범일로 637 105 호 솔향한우곰탕
#  - place_id: 1565454479 / place_name: 만추 / address: 강원 강릉시 공항길 142-32
#  - place_id: 1117927212 / place_name: 병천순대모래내 / address: 강원 강릉시 사천면 덕실길 4 . 387-2
#  - place_id: 38521522 / place_name: 산이장칼국수 포남동1호점 / address: 산이장칼국수 포남동1호점
#  - place_id: 1311691306 / place_name: 장어정각 / address: 강원 강릉시 하슬라로192번길 18 1, 2층
#  - place_id: 1202584889 / place_name: 캠핑식당 용지각길56 / address: 캠핑식당 용지각길56

# 실패 항목들 수작업 스타트 

# [10]add_latlng.py
import json
from pathlib import Path
import requests
from tqdm import tqdm

# ========= 카카오 REST API 키 =========
KAKAO_REST_API_KEY = "03330328b7c2a80adf59ecb350c4957e"

def get_coordinates(address: str):
    """
    카카오 로컬 API를 이용해 주소를 위도/경도로 변환
    """
    url = "https://dapi.kakao.com/v2/local/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": address}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
    except Exception as e:
        print("Request error:", e)
        return None, None

    if response.status_code != 200:
        print("Error:", response.status_code, response.text)
        return None, None

    data = response.json()
    if data.get("documents"):
        x = data["documents"][0]["x"]  # 경도
        y = data["documents"][0]["y"]  # 위도
        return float(y), float(x)
    else:
        return None, None

# ========= 파일 경로 =========
INPUT_FILE  = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[9]save_data.jsonl"
OUTPUT_FILE = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[10]data_with_latlng.jsonl"

def add_latlng(input_file: str, output_file: str):
    in_path = Path(input_file)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(in_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    total = updated = skipped = failed = 0
    failed_items = []

    with open(out_path, "w", encoding="utf-8") as fout, tqdm(total=len(lines), desc="Adding LatLng", unit="line") as pbar:
        for line in lines:
            total += 1
            try:
                obj = json.loads(line)
            except:
                pbar.update(1)
                continue

            # 이미 위경도가 있는 경우 스킵
            if obj.get("latitude") not in (None, "", "null") and obj.get("longitude") not in (None, "", "null"):
                skipped += 1
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            address = obj.get("address")
            if not address:
                failed += 1
                failed_items.append({"place_id": obj.get("place_id"), "place_name": obj.get("place_name")})
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                pbar.update(1)
                continue

            lat, lng = get_coordinates(address)
            if lat and lng:
                obj["latitude"] = lat
                obj["longitude"] = lng
                updated += 1
            else:
                failed += 1
                failed_items.append({"place_id": obj.get("place_id"), "place_name": obj.get("place_name"), "address": address})

            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
            pbar.update(1)

    print(f"\n✅ Done: {out_path}")
    print(f"총 {total}건 / 새로 채움 {updated}건 / 실패 {failed}건 / 기존 유지 {skipped}건")
    if failed_items:
        print("\n❌ 실패 항목들:")
        for item in failed_items:
            print(f" - place_id: {item['place_id']} / place_name: {item['place_name']} / address: {item.get('address')}")

if __name__ == "__main__":
    add_latlng(INPUT_FILE, OUTPUT_FILE)
