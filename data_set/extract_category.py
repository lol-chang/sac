import pandas as pd
import os

# 폴더 경로
path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"

files = [
    "attractions_fixed.csv",
    "restaurants_fixed.csv",
    "accommodations_fixed.csv"
]

for fname in files:
    file_path = os.path.join(path, fname)
    print(f"\n=== {fname} ===")
    df = pd.read_csv(file_path)

    for col in ["like", "dislike"]:
        if col in df.columns:
            # 고유값에서 앞 20개만 가져오기
            unique_vals = df[col].dropna().unique()[:20]

            print(f"{col} (first 20 of {len(unique_vals)} unique values):")
            for val in unique_vals:
                keywords = [kw.strip() for kw in val.split(";") if kw.strip()]
                print("  -", keywords)
        else:
            print(f"{col}: (컬럼 없음)")
