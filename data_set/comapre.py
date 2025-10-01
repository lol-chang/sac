import pandas as pd
import os
from tabulate import tabulate  # pip install tabulate

# 두 폴더 경로
path_X = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
path_O = r"C:\Users\changjin\workspace\lab\pln\data_set\null_O"

files = [
    "attractions_fixed.csv",
    "restaurants_fixed.csv",
    "accommodations_fixed.csv"
]

results = []

for fname in files:
    file_X = os.path.join(path_X, fname)
    file_O = os.path.join(path_O, fname)

    df_X = pd.read_csv(file_X)
    df_O = pd.read_csv(file_O)

    # like/dislike 둘 다 비어있는 행 삭제
    like_empty = df_X['like'].isna() | (df_X['like'].astype(str).str.strip() == "")
    dislike_empty = df_X['dislike'].isna() | (df_X['dislike'].astype(str).str.strip() == "")
    cleaned_X = df_X[~(like_empty & dislike_empty)]

    # 🔥 실제 파일 덮어쓰기 (삭제 반영)
    cleaned_X.to_csv(file_X, index=False, encoding="utf-8-sig")

    total_X = df_X.shape[0]
    removed = total_X - cleaned_X.shape[0]
    total_cleaned_X = cleaned_X.shape[0]
    total_O = df_O.shape[0]

    results.append([fname, total_X, removed, total_cleaned_X, total_O])

summary = pd.DataFrame(results, columns=["파일명", "원본 개수", "삭제된 개수", "null_X 개수", "null_O 개수"])

# 표 깔끔하게 출력
print(tabulate(summary, headers="keys", tablefmt="pretty", showindex=False))
