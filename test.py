import json

JSONL_PATH = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\tour_places_with_description.jsonl"

null_description_places = []

with open(JSONL_PATH, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        desc = data.get("description")
        if desc in [None, "", "null"]:
            null_description_places.append(data.get("place_name"))

# 결과 출력
print(f"📄 description이 비어 있는 항목 수: {len(null_description_places)}")
print("🧾 해당 장소명 리스트:")
for name in null_description_places:
    print("-", name)
