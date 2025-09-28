# [12]check_null_latlng.py
import json
from pathlib import Path

# ========= 파일 경로 =========
INPUT_FILE  = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[10]data_with_latlng.jsonl"

def check_null_latlng(input_file: str):
    in_path = Path(input_file)

    total = 0
    null_latlng = 0
    null_items = []

    with open(in_path, "r", encoding="utf-8") as f:
        for line in f:
            total += 1
            try:
                obj = json.loads(line)
            except:
                continue

            lat = obj.get("latitude")
            lng = obj.get("longitude")

            if lat in (None, "", "null") or lng in (None, "", "null"):
                null_latlng += 1
                null_items.append({"place_id": obj.get("place_id"), "place_name": obj.get("place_name")})

    print(f"총 {total}건 중 위도/경도 null 항목: {null_latlng}건")
    if null_items:
        print("\n❌ Null 위경도 항목들:")
        for item in null_items:
            print(f" - place_id: {item['place_id']} / place_name: {item['place_name']}")

if __name__ == "__main__":
    check_null_latlng(INPUT_FILE)
