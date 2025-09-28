import json
import uuid
import pandas as pd
from difflib import get_close_matches

# 🔹 경로 설정
EXCEL_PATHS = [
    r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\TourAPI_관광지.xlsx",
    r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\TourAPI_문화시설.xlsx"
]
JSONL_PATH = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\tour_places_cleaned.jsonl"
OUTPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\tour_places_with_description.jsonl"

# 🔹 엑셀 파일에서 place_name과 description 추출
desc_map = {}

for path in EXCEL_PATHS:
    df = pd.read_excel(path)
    df = df.rename(columns=lambda x: x.strip())
    df["place_name"] = df["명칭"].astype(str).str.strip()
    df["description"] = df["개요"].astype(str).str.strip()

    for _, row in df.iterrows():
        name = row["place_name"]
        desc = row["description"]
        if name and desc:
            desc_map[name] = desc

# 🔹 JSONL 파일 업데이트
updated = 0
already_filled = 0
no_match = []
similar_names = []

with open(JSONL_PATH, "r", encoding="utf-8") as infile, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:

    for line in infile:
        data = json.loads(line)
        place_name = data.get("place_name")
        current_desc = data.get("description")

        # 기존 설명이 있으면 유지
        if current_desc not in [None, "", "null"]:
            already_filled += 1
            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")
            continue

        # 정확히 일치하는 설명 찾기
        matched_desc = desc_map.get(place_name)
        if matched_desc:
            data["description"] = matched_desc
            updated += 1
        else:
            # 유사 이름 찾기
            close = get_close_matches(place_name, desc_map.keys(), n=1, cutoff=0.87)
            if close:
                similar_names.append((place_name, close[0]))
            no_match.append(place_name)

        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

# 🔹 결과 출력
print(f"✅ 설명 업데이트 완료!")
print(f"📝 새로 채운 description 개수: {updated}")
print(f"🔁 이미 채워져 있던 항목: {already_filled}")
print(f"❌ 일치하는 설명 없음: {len(no_match)}")

if similar_names:
    print("\n🔍 유사한 이름 (수동 확인 필요):")
    for original, suggestion in similar_names:
        print(f"- '{original}' ↔ '{suggestion}'")
