# import os
# import json
# import pandas as pd

# # ✅ 데이터셋 경로
# BASE_PATH = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
# FILES = {
#     "Attraction": "attractions_fixed.csv",
#     "Restaurant": "restaurants_fixed.csv",
#     "Accommodation": "accommodations_fixed.csv",
#     "Cafe": "cafe_fixed.csv"
# }

# def load_place_data():
#     """CSV 파일들을 모두 읽어서 category별 DataFrame으로 반환"""
#     place_data = {}
#     for category, filename in FILES.items():
#         file_path = os.path.join(BASE_PATH, filename)
#         if not os.path.exists(file_path):
#             print(f"⚠️ 파일 없음: {file_path}")
#             continue
#         df = pd.read_csv(file_path)
#         place_data[category] = df
#         print(f"✅ {category}: {len(df)}행 로드 완료")
#     return place_data


# def fill_place_names(result_json, place_data):
#     """GPT 결과 JSON에서 id 기준으로 name을 실제 데이터셋에서 찾아 채움"""
#     updated = result_json.copy()

#     # category별 name 컬럼 후보 (데이터셋 구조가 다를 수 있으므로 대비)
#     name_candidates = {
#         "Accommodation": ["name", "accommodation_name", "title"],
#         "Restaurant": ["name", "restaurant_name", "title"],
#         "Cafe": ["name", "cafe_name", "title"],
#         "Attraction": ["name", "attraction_name", "title"]
#     }

#     for day_data in updated["itinerary"]:
#         for place in day_data["place_plan"]:
#             cat = place["category"]
#             pid = place["id"]

#             if cat not in place_data:
#                 continue

#             df = place_data[cat].copy()

#             # id 컬럼 정규화
#             if "id" not in df.columns:
#                 continue
#             df["id"] = pd.to_numeric(df["id"], errors="coerce")

#             # id 일치하는 행 찾기
#             match = df[df["id"] == pid]
#             if not match.empty:
#                 # 가능한 name 컬럼 중 실제 존재하는 것 사용
#                 for col in name_candidates[cat]:
#                     if col in match.columns:
#                         val = match.iloc[0][col]
#                         if pd.notna(val):
#                             place["name"] = str(val)
#                             break
#                 else:
#                     place["name"] = f"{cat} #{pid}"
#             else:
#                 place["name"] = f"{cat} #{pid}"

#     return updated


# def main():
#     # 🔹 GPT 결과 JSON 파일 경로
#     input_json_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_CSV.json"
#     output_json_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_named.json"

#     print("🚀 데이터 로드 중...")
#     result = json.load(open(input_json_path, "r", encoding="utf-8"))
#     place_data = load_place_data()

#     print("\n🔍 name 필드 채우는 중...")
#     updated_result = fill_place_names(result, place_data)

#     print("\n💾 결과 저장 중...")
#     with open(output_json_path, "w", encoding="utf-8") as f:
#         json.dump(updated_result, f, ensure_ascii=False, indent=2)

#     print(f"✅ 저장 완료: {output_json_path}")

# if __name__ == "__main__":
#     main()

import os
import json
import pandas as pd

# ✅ 데이터셋 경로
BASE_PATH = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
FILES = {
    "Attraction": "attractions_fixed.csv",
    "Restaurant": "restaurants_fixed.csv",
    "Accommodation": "accommodations_fixed.csv",
    "Cafe": "cafe_fixed.csv"
}

def load_place_data():
    """CSV 파일들을 모두 읽어서 category별 DataFrame으로 반환"""
    place_data = {}
    for category, filename in FILES.items():
        file_path = os.path.join(BASE_PATH, filename)
        if not os.path.exists(file_path):
            print(f"⚠️ 파일 없음: {file_path}")
            continue
        df = pd.read_csv(file_path)
        place_data[category] = df
        print(f"✅ {category}: {len(df)}행 로드 완료")
    return place_data


def fill_place_names(result_json, place_data):
    """GPT 결과 JSON에서 id 기준으로 name을 실제 데이터셋에서 찾아 채움"""
    updated = result_json.copy()

    # category별 name 컬럼 후보 (데이터셋 구조가 다를 수 있으므로 대비)
    name_candidates = {
        "Accommodation": ["name", "accommodation_name", "title"],
        "Restaurant": ["name", "restaurant_name", "title"],
        "Cafe": ["name", "cafe_name", "title"],
        "Attraction": ["name", "attraction_name", "title"]
    }

    for day_data in updated["itinerary"]:
        for place in day_data["place_plan"]:
            cat = place["category"]
            pid = place["id"]

            if cat not in place_data:
                continue

            df = place_data[cat].copy()

            # id 컬럼 정규화
            if "id" not in df.columns:
                continue
            df["id"] = pd.to_numeric(df["id"], errors="coerce")

            # id 일치하는 행 찾기
            match = df[df["id"] == pid]
            if not match.empty:
                # 가능한 name 컬럼 중 실제 존재하는 것 사용
                for col in name_candidates[cat]:
                    if col in match.columns:
                        val = match.iloc[0][col]
                        if pd.notna(val):
                            place["name"] = str(val)
                            break
                else:
                    place["name"] = f"{cat} #{pid}"
            else:
                place["name"] = f"{cat} #{pid}"

    return updated


def calculate_daily_costs(result_json):
    """cost_breakdown 값들을 더해서 daily_cost를 재계산"""
    updated = result_json.copy()
    
    print("\n💰 daily_cost 재계산 중...")
    for day_data in updated["itinerary"]:
        day = day_data["day"]
        cost_breakdown = day_data.get("cost_breakdown", {})
        
        # cost_breakdown의 모든 값을 더함
        calculated_cost = sum([
            cost_breakdown.get("accommodation", 0),
            cost_breakdown.get("restaurants", 0),
            cost_breakdown.get("cafe", 0),
            cost_breakdown.get("attractions", 0)
        ])
        
        # 기존 daily_cost와 비교
        original_cost = day_data.get("daily_cost", 0)
        day_data["daily_cost"] = calculated_cost
        
        print(f"   Day {day}: {original_cost:,}원 → {calculated_cost:,}원 (차이: {calculated_cost - original_cost:+,}원)")
    
    return updated


def main():
    # 🔹 GPT 결과 JSON 파일 경로
    input_json_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_CSV.json"
    output_json_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_named.json"

    print("🚀 데이터 로드 중...")
    result = json.load(open(input_json_path, "r", encoding="utf-8"))
    place_data = load_place_data()

    print("\n🔍 name 필드 채우는 중...")
    updated_result = fill_place_names(result, place_data)

    print("\n💰 daily_cost 재계산 중...")
    updated_result = calculate_daily_costs(updated_result)

    print("\n💾 결과 저장 중...")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(updated_result, f, ensure_ascii=False, indent=2)

    print(f"✅ 저장 완료: {output_json_path}")


if __name__ == "__main__":
    main()