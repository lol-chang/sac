import pandas as pd

# CSV 불러오기
df = pd.read_csv(r"C:\Users\changjin\workspace\lab\pln\data_set\null_X\accommodations_fixed.csv")

# 사용할 가격 컬럼 리스트
price_cols = [
    "offpeak_weekday_price_avg",
    "offpeak_weekend_price_avg",
    "peak_weekday_price_avg",
    "peak_weekend_price_avg"
]

# row 단위 평균 숙박비 계산 (모든 조건 포함)
df["full_price_avg"] = df[price_cols].mean(axis=1)

# 서브카테고리별 평균 구하기
sub_category_price = df.groupby("sub_category")["full_price_avg"].mean().reset_index()

# 보기 좋게 정렬 (가격 낮은 순)
sub_category_price = sub_category_price.sort_values("full_price_avg").reset_index(drop=True)

print(sub_category_price)
