# """
# combine_category_data_minimal.py

# 핫존 탐색용 최소 데이터 통합 스크립트.
# - 4개 카테고리: Accommodation, Attraction, Restaurant, Cafe
# - 필드: id, name, category, latitude, longitude
# - 숙소 파일(lat/lng)을 latitude/longitude로 변환
# """

# import os
# import pandas as pd

# def combine_category_data_minimal(base_path, output_path):
#     """
#     4개 카테고리 CSV에서 필요한 필드만 추출해 통합
#     """
#     files = {
#         "Accommodation": "accommodations_fixed.csv",
#         "Attraction": "attractions_fixed.csv",
#         "Restaurant": "restaurants_fixed.csv",
#         "Cafe": "cafe_fixed.csv"
#     }

#     dfs = []
#     for category, filename in files.items():
#         path = os.path.join(base_path, filename)
#         if not os.path.exists(path):
#             print(f"⚠️ {filename} 없음 — 건너뜀")
#             continue

#         df = pd.read_csv(path)

#         # --- 숙소: lat/lng 컬럼명을 latitude/longitude로 변경 ---
#         if category == "Accommodation":
#             if "lat" in df.columns and "lng" in df.columns:
#                 df = df.rename(columns={"lat": "latitude", "lng": "longitude"})
        
#         # --- 필요한 컬럼만 남기기 ---
#         needed_cols = ["id", "name", "latitude", "longitude"]
#         df = df[[col for col in needed_cols if col in df.columns]].copy()
#         df["category"] = category

#         # --- 누락된 값 제거 ---
#         df = df.dropna(subset=["latitude", "longitude"])
        
#         print(f"✅ {category}: {len(df)}개 로드 및 필터링 완료")
#         dfs.append(df)

#     if not dfs:
#         raise ValueError("❌ 로드된 데이터가 없습니다.")

#     combined = pd.concat(dfs, ignore_index=True)
#     print(f"\n📦 총 {len(combined)}개 장소 통합 완료")

#     # --- 결과 저장 ---
#     combined.to_csv(output_path, index=False, encoding="utf-8-sig")
#     print(f"💾 저장 완료: {output_path}")

# if __name__ == "__main__":
#     base_path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
#     output_path = r"C:\Users\changjin\workspace\lab\pln\data_set\clustering_category_combine.csv"
#     combine_category_data_minimal(base_path, output_path)
"""
combine_category_data_with_hours.py

핫존 탐색용 최소 데이터 통합 스크립트 (영업시간 포함 버전)
- 4개 카테고리: Accommodation, Attraction, Restaurant, Cafe
- 필드:
    id, name, category, latitude, longitude, store_hours(숙소 제외)
"""

import os
import pandas as pd

def combine_category_data_with_hours(base_path, output_path):
    """
    4개 카테고리 CSV에서 필요한 필드만 추출해 통합
    """
    files = {
        "Accommodation": "accommodations_fixed.csv",
        "Attraction": "attractions_fixed.csv",
        "Restaurant": "restaurants_fixed.csv",
        "Cafe": "cafe_fixed.csv"
    }

    dfs = []
    for category, filename in files.items():
        path = os.path.join(base_path, filename)
        if not os.path.exists(path):
            print(f"⚠️ {filename} 없음 — 건너뜀")
            continue

        df = pd.read_csv(path)

        # --- 숙소: lat/lng 컬럼명을 latitude/longitude로 변경 ---
        if category == "Accommodation":
            if "lat" in df.columns and "lng" in df.columns:
                df = df.rename(columns={"lat": "latitude", "lng": "longitude"})
            
            # 숙소는 store_hours 제외
            needed_cols = ["id", "name", "latitude", "longitude"]

        else:
            # 카페, 음식점, 관광지는 store_hours 포함
            needed_cols = ["id", "name", "latitude", "longitude", "store_hours"]

        # --- 필요한 컬럼만 남기기 ---
        df = df[[col for col in needed_cols if col in df.columns]].copy()
        df["category"] = category

        # --- 누락된 값 제거 ---
        df = df.dropna(subset=["latitude", "longitude"])
        
        print(f"✅ {category}: {len(df)}개 로드 및 필터링 완료")
        dfs.append(df)

    if not dfs:
        raise ValueError("❌ 로드된 데이터가 없습니다.")

    combined = pd.concat(dfs, ignore_index=True)
    print(f"\n📦 총 {len(combined)}개 장소 통합 완료")

    # --- 결과 저장 ---
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"💾 저장 완료: {output_path}")

if __name__ == "__main__":
    base_path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
    output_path = r"C:\Users\changjin\workspace\lab\pln\data_set\clustering_category_combine_with_hours.csv"
    combine_category_data_with_hours(base_path, output_path)
