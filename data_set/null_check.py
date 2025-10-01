import pandas as pd
import os

path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"

files = [
    "attractions_fixed.csv",
    "restaurants_fixed.csv",
    "accommodations_fixed.csv"
]

for file in files:
    file_path = os.path.join(path, file)
    df = pd.read_csv(file_path)

    total_count = len(df)
    description_count = df['description'].notna().sum()
    null_count = df['description'].isna().sum()

    print(f"📄 {file}")
    print(f"  - 전체 row 수: {total_count}")
    print(f"  - description 있는 항목 수: {description_count}")
    print(f"  - description NULL 수: {null_count}")
    print("-" * 50)
