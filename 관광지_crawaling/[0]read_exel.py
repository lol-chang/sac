import pandas as pd
import uuid
import json
from pathlib import Path

# 파일 경로
file_paths = [
    "C:/Users/changjin/workspace/lab/pln/관광지_crawaling/TourAPI_관광지.xlsx",
    "C:/Users/changjin/workspace/lab/pln/관광지_crawaling/TourAPI_문화시설.xlsx"
]

# 저장 경로
output_path = Path("C:/Users/changjin/workspace/lab/pln/관광지_crawaling/tour_places.jsonl")

jsonl_data = []

# 각 파일 처리
for file_path in file_paths:
    df = pd.read_excel(file_path)

    # 컬럼명 정리
    df.columns = df.columns.str.strip()

    for _, row in df.iterrows():
        entry = {
            "place_id": None,
            "place_name": row.get("명칭"),
            "description": row.get("개요") if pd.notna(row.get("개요")) else None,
            "sub_category": None,
            "category": "관광지",
            "source": "TourAPI",
            "url": None,
            "like": [],
            "unlike": [],
            "address": row.get("주소"),
            "latitude": float(row["위도"]) if pd.notna(row.get("위도")) else None,
            "longitude": float(row["경도"]) if pd.notna(row.get("경도")) else None,
            "id": str(uuid.uuid4()),
            "store_hours": None,
            "entrance_fee": None,
            "rating": None,
            "visiter_review_count": None,
            "blog_review_count": None,
            "all_review_count": None,
            "reviews_attraction": []
        }
        jsonl_data.append(entry)

# 저장
with open(output_path, "w", encoding="utf-8") as f:
    for item in jsonl_data:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print(f"✅ 저장 완료: {output_path} ({len(jsonl_data)}개)")
