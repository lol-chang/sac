import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import matplotlib as mpl

# ======================
# 🔧 한글 폰트 설정 (Windows: 맑은 고딕, Mac: AppleGothic, Linux: NanumGothic)
# ======================
plt.rcParams["font.family"] = "Malgun Gothic"   # 윈도우
# plt.rcParams["font.family"] = "AppleGothic"   # 맥북이면 이걸로
# plt.rcParams["font.family"] = "NanumGothic"   # 리눅스에 나눔고딕 설치 시

# 음수 기호 깨짐 방지
mpl.rcParams["axes.unicode_minus"] = False

# ======================
# 1️⃣ 데이터 로드
# ======================
path = r"C:\Users\changjin\workspace\lab\pln\data_set\clustering_category_combine.csv"
df = pd.read_csv(path)

# ======================
# 2️⃣ 중심 기준 계산 (사분면 분할용)
# ======================
center_lat = df["latitude"].median()
center_lng = df["longitude"].median()
print(f"📍 중심 좌표: ({center_lat:.4f}, {center_lng:.4f})")

# ======================
# 3️⃣ 카테고리 목록 (4종)
# ======================
categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
colors = {
    "Accommodation": "red",
    "Cafe": "orange",
    "Restaurant": "green",
    "Attraction": "blue"
}

# ======================
# 4️⃣ 시각화
# ======================
fig, axes = plt.subplots(2, 2, figsize=(14, 12))
axes = axes.flatten()

for i, cat in enumerate(categories):
    ax = axes[i]
    sub = df[df["category"] == cat]

    ax.scatter(sub["longitude"], sub["latitude"], c=colors[cat], s=30, alpha=0.7)
    ax.axhline(center_lat, color="black", linestyle="--", linewidth=1)
    ax.axvline(center_lng, color="black", linestyle="--", linewidth=1)
    ax.set_title(f"{cat} (n={len(sub)})", fontsize=13, fontweight="bold")
    ax.set_xlabel("Longitude (경도)")
    ax.set_ylabel("Latitude (위도)")
    ax.grid(alpha=0.3)

plt.suptitle("📍 강릉 내 카테고리별 위치 분포 (4사분면 기준)", fontsize=16, fontweight="bold")
plt.tight_layout(rect=[0, 0, 1, 0.97])

# ======================
# 5️⃣ 저장 & 표시
# ======================
save_path = r"C:\Users\changjin\workspace\lab\pln\clustering\category_separated_quadrants.png"
plt.savefig(save_path, dpi=200)
plt.show()

print(f"✅ 시각화 저장 완료: {save_path}")
