"""
combine_category_data_with_hours.py

핫존 탐색용 최소 데이터 통합 스크립트 (영업시간 포함 + 숙소 요금 정보 포함 버전)
- 4개 카테고리: Accommodation, Attraction, Restaurant, Cafe
- 필드:
    - 숙소: id, name, latitude, longitude, 4개 요금 평균
    - 나머지: id, name, latitude, longitude, store_hours
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

        # --- 숙소: lat/lng → latitude/longitude로 변경 ---
        if category == "Accommodation":
            if "lat" in df.columns and "lng" in df.columns:
                df = df.rename(columns={"lat": "latitude", "lng": "longitude"})

            # ✅ 숙소는 4개 요금 평균 필드 추가
            price_cols = [
                "offpeak_weekday_price_avg",
                "offpeak_weekend_price_avg",
                "peak_weekday_price_avg",
                "peak_weekend_price_avg"
            ]
            needed_cols = ["id", "name", "latitude", "longitude"] + [
                col for col in price_cols if col in df.columns
            ]

        else:
            # ✅ 카페, 음식점, 관광지는 store_hours 포함
            needed_cols = ["id", "name", "latitude", "longitude", "store_hours"]

        # --- 필요한 컬럼만 남기기 ---
        df = df[[col for col in needed_cols if col in df.columns]].copy()
        df["category"] = category

        # --- 누락된 좌표 제거 ---
        df = df.dropna(subset=["latitude", "longitude"])
        
        print(f"✅ {category}: {len(df)}개 로드 및 필터링 완료")
        dfs.append(df)

    if not dfs:
        raise ValueError("❌ 로드된 데이터가 없습니다.")

    # --- 전체 합치기 ---
    combined = pd.concat(dfs, ignore_index=True)
    print(f"\n📦 총 {len(combined)}개 장소 통합 완료")

    # --- 결과 저장 ---
    combined.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"💾 저장 완료: {output_path}")

if __name__ == "__main__":
    base_path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
    output_path = r"C:\Users\changjin\workspace\lab\pln\data_set\last_clustering_category_combine_with_hours_and_price.csv"
    combine_category_data_with_hours(base_path, output_path)
