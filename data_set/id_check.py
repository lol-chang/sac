import pandas as pd
import os

# 경로 설정
path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
files = ["attractions_fixed.csv", "restaurants_fixed.csv", "accommodations_fixed.csv"]

# 파일별 ID 저장소
id_sets = {}

# 각 파일에서 ID 수집
for fname in files:
    df = pd.read_csv(os.path.join(path, fname))
    id_col = "id" if "id" in df.columns else "place_id"  # 유동적으로 처리
    ids = set(df[id_col].dropna().astype(str).tolist())
    id_sets[fname] = ids
    print(f"{fname} → ID 개수: {len(ids)}")

# 교집합 확인
print("\n🔍 중복된 ID 확인:")

# 모든 쌍에 대해 교집합 비교
checked = set()
for f1 in files:
    for f2 in files:
        if f1 != f2 and (f2, f1) not in checked:
            overlap = id_sets[f1] & id_sets[f2]
            print(f"{f1} ↔ {f2} 중복 ID 개수: {len(overlap)}")
            if overlap:
                print("  ▶ 예시:", list(overlap)[:5])
            checked.add((f1, f2))
