import pandas as pd

# 파일 경로
path = r"C:\Users\changjin\workspace\lab\pln\user_1000.csv"
df = pd.read_csv(path)

# couple인 경우 gender를 "Both"로 변경
df.loc[df["companion"] == "couple", "gender"] = "Both"

# 저장
df.to_csv("synthetic_users_1000_fixed.csv", index=False)

print("[INFO] gender 수정 완료 → synthetic_users_1000_fixed.csv")
