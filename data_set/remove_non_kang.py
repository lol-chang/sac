import pandas as pd
import os

# 두 폴더 경로
path_X = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
path_O = r"C:\Users\changjin\workspace\lab\pln\data_set\null_O"

files = [
    "attractions_fixed.csv",
    "restaurants_fixed.csv",
    "accommodations_fixed.csv"
]

for folder in [path_X]:
    for file in files:
        file_path = os.path.join(folder, file)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)

            # address에 '강릉'이 포함되지 않은 행
            not_containing = df[~df["address"].astype(str).str.contains("강릉", na=False)]

            print(f"\n[{os.path.basename(folder)}] {file}")
            print(f" - 전체 행 수: {len(df)}")
            print(f" - '강릉' 미포함 행 수: {len(not_containing)}")
            print("-" * 60)

            # address, place_id 컬럼만 출력
            if not not_containing.empty:
                cols_to_show = ["id", "address"]
                print(not_containing[cols_to_show].to_string(index=False))
            else:
                print("✅ 모든 행에 '강릉'이 포함되어 있습니다.")
            print("=" * 60)
