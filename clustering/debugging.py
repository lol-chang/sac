import json

# JSON 파일 경로
json_path = r"C:\Users\changjin\workspace\lab\pln\clustering\greedy_hotzones_merged.json"

# JSON 파일 읽기
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# 결과 출력
print("="*70)
print("📊 클러스터별 카테고리 개수 통계")
print("="*70)

hotzones = data["hotzones"]
categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]

for hotzone in hotzones:
    cluster_id = hotzone["cluster_id"]
    print(f"\n🏷️ 클러스터 {cluster_id}")
    
    total = 0
    for cat in categories:
        count = len(hotzone["categories"].get(cat, []))
        print(f"  {cat}: {count}개")
        total += count
    
    print(f"  총합: {total}개")

# 전체 통계
print("\n" + "="*70)
print("📈 전체 통계")
print("="*70)

total_stats = {cat: 0 for cat in categories}
for hotzone in hotzones:
    for cat in categories:
        total_stats[cat] += len(hotzone["categories"].get(cat, []))

for cat in categories:
    print(f"{cat}: {total_stats[cat]}개")

print(f"총 클러스터 수: {len(hotzones)}개")
print(f"총 장소 수: {sum(total_stats.values())}개")