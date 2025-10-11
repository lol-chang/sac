import os
import json

# 폴더 경로
base_dir = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan"

# 폴더 내 모든 파일 순회
for filename in os.listdir(base_dir):
    if not filename.endswith(".json"):
        continue

    file_path = os.path.join(base_dir, filename)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # itinerary가 있고, day가 1인 단 하루짜리일 때만 처리
    itinerary = data.get("itinerary", [])
    if len(itinerary) == 1 and itinerary[0].get("day") == 1:
        place_plan = itinerary[0].get("place_plan", [])
        if len(place_plan) > 0:
            print(f"수정 중: {filename}")
            # 첫 번째 항목 제거
            place_plan.pop(0)

            # 다시 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        # 여러 day가 있는 파일은 패스
        continue

print("✅ 처리 완료!")
