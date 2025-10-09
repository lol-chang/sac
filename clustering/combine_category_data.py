import os
import pandas as pd
import numpy as np
from haversine import haversine, Unit
import matplotlib.pyplot as plt
import json
from matplotlib import font_manager, rc

# ========================================
# 🔤 한글 폰트 설정 (Windows)
# ========================================
font_path = "C:/Windows/Fonts/malgun.ttf"
font_name = font_manager.FontProperties(fname=font_path).get_name()
rc('font', family=font_name)
plt.rcParams['axes.unicode_minus'] = False


# ========================================
# 📏 거리 계산
# ========================================
def haversine_km(coord1, coord2):
    return haversine(coord1, coord2, unit=Unit.KILOMETERS)


# ========================================
# 🧩 1단계: 희귀 카테고리 우선 Greedy Cluster
# ========================================
def greedy_cluster(df, target_cluster_size=20, base_radius=0.8, min_per_cat=3):
    """
    비율 기반 동적 할당으로 균형잡힌 클러스터 생성
    
    Args:
        target_cluster_size: 목표 클러스터 크기 (기본 50개)
        min_per_cat: 각 카테고리 최소 개수 (기본 3개)
    """
    df = df.copy()
    df["assigned"] = False
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    clusters = []
    cluster_id = 0
    
    # 🔑 카테고리별 비율 계산
    category_counts = df["category"].value_counts().to_dict()
    total_places = len(df)
    category_ratios = {cat: category_counts.get(cat, 0) / total_places for cat in all_categories}
    
    # 희귀한 순서로 정렬 (개수 적은 순)
    rarity_order = sorted(category_counts.keys(), key=lambda x: category_counts[x])
    
    print(f"\n📊 카테고리 분포 및 비율:")
    for cat in all_categories:
        count = category_counts.get(cat, 0)
        ratio = category_ratios[cat]
        print(f"  {cat}: {count}개 ({ratio*100:.1f}%)")
    
    # 🔑 각 클러스터의 목표 개수 계산 (비율 기반)
    target_per_cat = {}
    for cat in all_categories:
        calculated = int(target_cluster_size * category_ratios[cat])
        # 최소 개수 보장
        target_per_cat[cat] = max(min_per_cat, calculated)
    
    print(f"\n🎯 클러스터당 목표 개수 (총 {sum(target_per_cat.values())}개):")
    for cat in all_categories:
        print(f"  {cat}: {target_per_cat[cat]}개")

    while not df[df["assigned"] == False].empty:
        # 희귀한 카테고리부터 seed로 선택
        seed_idx = None
        for cat in rarity_order:
            available = df[(df["assigned"] == False) & (df["category"] == cat)]
            if len(available) > 0:
                seed_idx = available.index[0]
                break
        
        # 희귀 카테고리가 모두 소진되면 일반 순서로
        if seed_idx is None:
            seed_idx = df[df["assigned"] == False].index[0]
        
        seed = df.loc[seed_idx]
        cluster_points = [seed_idx]
        df.at[seed_idx, "assigned"] = True

        # 모든 카테고리 초기화
        cat_count = {cat: 0 for cat in all_categories}
        cat_count[seed["category"]] += 1

        df["distance"] = df.apply(
            lambda r: haversine_km(
                (seed["latitude"], seed["longitude"]),
                (r["latitude"], r["longitude"])
            ), axis=1
        )

        sorted_idx = df[df["assigned"] == False].sort_values("distance").index

        for i in sorted_idx:
            # 🔑 모든 카테고리가 목표 개수 도달하면 종료
            if all(cat_count[cat] >= target_per_cat[cat] for cat in all_categories):
                break
                
            point = df.loc[i]
            dist = point["distance"]
            radius = base_radius * (1 + len(cluster_points) / 20)

            if dist > radius:
                continue

            cat = point["category"]
            
            # 🔑 해당 카테고리가 목표 개수 도달하면 스킵
            if cat_count[cat] >= target_per_cat[cat]:
                continue

            cluster_points.append(i)
            df.at[i, "assigned"] = True
            cat_count[cat] += 1

        df.loc[cluster_points, "cluster_id"] = cluster_id
        
        # 디버그 출력
        total = sum(cat_count.values())
        diversity = sum(1 for count in cat_count.values() if count > 0)
        print(f"  C{cluster_id}: 총 {total}개 (다양성: {diversity}/4) | " + 
              " | ".join([f"{cat[:3]}: {cat_count[cat]}" for cat in all_categories]))
        
        cluster_id += 1
        clusters.append(cluster_points)

    # 미할당 장소 처리 - 가까운 것끼리 소형 클러스터 생성
    unassigned = df[df["assigned"] == False]
    if len(unassigned) > 0:
        print(f"\n⚠️ 미할당 장소 {len(unassigned)}개 → 소형 클러스터로 그룹화")
        
        unassigned_df = df[df["assigned"] == False].copy()
        
        while len(unassigned_df) > 0:
            # 희귀 카테고리부터 시드로
            seed_idx = None
            for cat in rarity_order:
                available = unassigned_df[unassigned_df["category"] == cat]
                if len(available) > 0:
                    seed_idx = available.index[0]
                    break
            
            if seed_idx is None:
                seed_idx = unassigned_df.index[0]
            
            seed = unassigned_df.loc[seed_idx]
            
            small_cluster = [seed_idx]
            df.at[seed_idx, "assigned"] = True
            unassigned_df = unassigned_df.drop(seed_idx)
            
            # 2km 반경 내의 미할당 장소들을 묶기
            for idx, row in unassigned_df.iterrows():
                dist = haversine_km(
                    (seed["latitude"], seed["longitude"]),
                    (row["latitude"], row["longitude"])
                )
                if dist <= 2.0:  # 2km 이내
                    small_cluster.append(idx)
                    df.at[idx, "assigned"] = True
            
            # 클러스터 할당
            df.loc[small_cluster, "cluster_id"] = cluster_id
            
            cat_count = df.loc[small_cluster, "category"].value_counts().to_dict()
            total = len(small_cluster)
            diversity = sum(1 for cat in all_categories if cat_count.get(cat, 0) > 0)
            print(f"  C{cluster_id}: 총 {total}개 (소형, 다양성: {diversity}/4) | " + 
                  " | ".join([f"{cat[:3]}: {cat_count.get(cat, 0)}" 
                             for cat in all_categories]))
            
            cluster_id += 1
            
            # 다음 반복을 위해 업데이트
            unassigned_df = df[df["assigned"] == False].copy()

    return df


# ========================================
# 🔄 2단계: 불만족 클러스터 병합
# ========================================
def merge_unsatisfied_clusters(df, min_per_cat=3, ideal_per_cat=10, max_cluster_size=50, merge_radius=5.0, max_iterations=10):
    """
    불만족 클러스터끼리만 병합
    
    Args:
        min_per_cat: 최소 허용 개수 (기본 3개)
        ideal_per_cat: 이상적인 개수 (기본 10개)
        max_cluster_size: 병합 후 최대 크기
    """
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    
    for iteration in range(max_iterations):
        print(f"\n🔄 병합 반복 {iteration + 1}회차...")
        
        # 매 반복마다 현재 상태 기준으로 분류
        acceptable_clusters = set()  # 허용 가능 (모든 카테고리 3개 이상)
        critical_clusters = []       # 긴급 병합 필요 (3개 미만 카테고리 있음)
        
        for cid, group in df.groupby("cluster_id"):
            cat_counts = group["category"].value_counts().to_dict()
            counts = {cat: cat_counts.get(cat, 0) for cat in all_categories}
            total_size = len(group)
            
            # 최소 허용 조건: 모든 카테고리가 최소 3개 이상
            has_insufficient = any(count < min_per_cat for count in counts.values())
            
            if not has_insufficient:
                acceptable_clusters.add(cid)  # 3개 이상 → 허용
            else:
                # 부족한 정도로 우선순위 결정
                insufficient_score = sum(max(0, min_per_cat - count) * 10 for count in counts.values())
                zero_count = sum(1 for count in counts.values() if count == 0)
                diversity = sum(1 for count in counts.values() if count > 0)
                priority = zero_count * 1000 + insufficient_score + (4 - diversity) * 10
                critical_clusters.append((priority, cid, total_size))
        
        print(f"  ✅ 허용 가능 클러스터: {len(acceptable_clusters)}개 (모든 카테고리 3개 이상)")
        print(f"  🔴 긴급 병합 필요: {len(critical_clusters)}개 (3개 미만 카테고리 있음)")
        
        if not critical_clusters:
            print(f"✅ 모든 클러스터가 최소 조건 만족! (반복 {iteration + 1}회)")
            break
        
        # 우선순위 순으로 정렬 (부족한 것 먼저)
        critical_clusters.sort(reverse=True)
        merged_count = 0
        
        for priority, cid, size1 in critical_clusters:
            if cid not in df["cluster_id"].values:
                continue
            
            # 실시간 재확인
            current_group = df[df["cluster_id"] == cid]
            current_counts = current_group["category"].value_counts().to_dict()
            current_dict = {cat: current_counts.get(cat, 0) for cat in all_categories}
            
            # 이미 모든 카테고리가 3개 이상이면 더 이상 병합 불필요
            if all(count >= min_per_cat for count in current_dict.values()):
                continue
            
            center1 = current_group[["latitude", "longitude"]].mean()
            best_target = None
            best_score = -1
            
            # 병합 대상 찾기 (긴급 클러스터끼리만)
            for _, target_cid, size2 in critical_clusters:
                if target_cid == cid or target_cid not in df["cluster_id"].values:
                    continue
                
                # 타겟도 실시간 재확인
                target_group = df[df["cluster_id"] == target_cid]
                target_counts = target_group["category"].value_counts().to_dict()
                target_dict = {cat: target_counts.get(cat, 0) for cat in all_categories}
                
                # 타겟이 이미 허용 가능해졌으면 제외
                if all(count >= min_per_cat for count in target_dict.values()):
                    continue
                
                # 병합 후 크기 제한
                merged_size = len(current_group) + len(target_group)
                if merged_size > max_cluster_size:
                    continue
                
                center2 = target_group[["latitude", "longitude"]].mean()
                dist = haversine_km(tuple(center1), tuple(center2))
                
                if dist > merge_radius:
                    continue
                
                # 상호 보완 점수 계산
                complementary_score = 0
                for cat in all_categories:
                    c1 = current_dict[cat]
                    c2 = target_dict[cat]
                    
                    # 0개 → 1개 이상: 초고 점수
                    if c1 == 0 and c2 > 0:
                        complementary_score += c2 * 50
                    elif c2 == 0 and c1 > 0:
                        complementary_score += c1 * 50
                    # 1~2개 → 3개 이상: 고 점수
                    elif c1 < min_per_cat and c2 > 0:
                        needed = min_per_cat - c1
                        complementary_score += min(c2, needed) * 20
                    elif c2 < min_per_cat and c1 > 0:
                        needed = min_per_cat - c2
                        complementary_score += min(c1, needed) * 20
                    # 둘 다 있지만 부족: 일반 점수
                    elif c1 < ideal_per_cat and c2 > 0:
                        complementary_score += c2
                    elif c2 < ideal_per_cat and c1 > 0:
                        complementary_score += c1
                
                # 점수: 상호보완 + 거리 페널티
                score = complementary_score - dist * 2
                
                if score > best_score:
                    best_score = score
                    best_target = target_cid
            
            # 병합 실행
            if best_target is not None:
                df.loc[df["cluster_id"] == cid, "cluster_id"] = best_target
                merged_count += 1
                dist_to_target = haversine_km(
                    tuple(center1),
                    tuple(df[df["cluster_id"] == best_target][["latitude", "longitude"]].mean())
                )
                merged_size = len(df[df["cluster_id"] == best_target])
                print(f"  ⚡ C{cid} → C{best_target} 병합 (거리: {dist_to_target:.2f}km, 병합 후: {merged_size}개)")
        
        if merged_count == 0:
            print(f"⚠️ 더 이상 병합할 수 없음 (반복 {iteration + 1}회)")
            print(f"  💡 merge_radius를 늘리거나 max_cluster_size를 늘려보세요")
            break
        
        # 클러스터 ID 재정렬
        df["cluster_id"] = df["cluster_id"].astype(int)
        new_ids = {old: new for new, old in enumerate(sorted(df["cluster_id"].unique()))}
        df["cluster_id"] = df["cluster_id"].map(new_ids)
        
        print(f"  📊 현재 클러스터 수: {len(df['cluster_id'].unique())}")
    
    return df


# ========================================
# 🧱 Hotzone JSON 생성
# ========================================
def build_hotzones(df):
    hotzones = []
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]

    for cid, group in df.groupby("cluster_id"):
        center_lat = group["latitude"].mean()
        center_lng = group["longitude"].mean()

        categories = {}
        for cat in all_categories:
            if cat in group["category"].unique():
                cat_group = group[group["category"] == cat]
                items = [
                    {
                        "id": int(row["id"]) if "id" in row and not pd.isna(row["id"]) else idx,
                        "name": row["name"],
                        "final_score": round(np.random.uniform(0.5, 0.9), 2)
                    }
                    for idx, row in cat_group.iterrows()
                ]
                categories[cat] = items
            else:
                categories[cat] = []

        hotzone = {
            "cluster_id": int(cid),
            "center_lat": round(center_lat, 6),
            "center_lng": round(center_lng, 6),
            "hotzone_score": round(
                min(1.0, len(group) / 50 + len([v for v in categories.values() if v]) * 0.1), 2
            ),
            "category_diversity": sum(len(v) > 0 for v in categories.values()),
            "total_places": len(group),
            "categories": categories
        }
        hotzones.append(hotzone)
    return {"hotzones": hotzones}


# ========================================
# 🎨 시각화
# ========================================
def visualize_clusters(df, save_path, title):
    plt.figure(figsize=(10, 8))
    clusters = sorted(df["cluster_id"].unique(), key=int)
    colors = plt.cm.tab20(np.linspace(0, 1, len(clusters)))

    for color, cid in zip(colors, clusters):
        sub = df[df["cluster_id"] == cid]
        plt.scatter(sub["longitude"], sub["latitude"], s=25, color=color, alpha=0.8, label=f"C{cid}")

    plt.xlabel("Longitude (경도)")
    plt.ylabel("Latitude (위도)")
    plt.title(title)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=7)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=200)
    print(f"✅ 시각화 저장 완료: {save_path}")
    plt.close()


# ========================================
# 📊 클러스터 품질 보고서
# ========================================
def print_cluster_report(df, min_acceptable=3, ideal_per_cat=10, max_size=50):
    """
    클러스터 품질 보고서
    """
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    print("\n" + "="*70)
    print("📊 클러스터 품질 보고서")
    print("="*70)
    
    acceptable_count = 0      # 모든 카테고리 3개 이상
    ideal_count = 0           # 모든 카테고리 10개 이상
    critical_count = 0        # 3개 미만 카테고리 있음
    oversized_count = 0
    
    for cid, group in df.groupby("cluster_id"):
        cat_counts = group["category"].value_counts().to_dict()
        counts = {cat: cat_counts.get(cat, 0) for cat in all_categories}
        total = len(group)
        diversity = sum(1 for count in counts.values() if count > 0)
        
        has_insufficient = any(count < min_acceptable for count in counts.values())
        is_ideal = all(count >= ideal_per_cat for count in counts.values())
        is_oversized = total > max_size
        
        # 상태 결정
        if has_insufficient:
            status = "🔴 긴급"
            critical_count += 1
        elif is_ideal:
            status = "✅ 이상적"
            ideal_count += 1
            acceptable_count += 1
        else:
            status = "⚠️ 허용"
            acceptable_count += 1
        
        if is_oversized:
            status += " 🔴 초과"
            oversized_count += 1
        
        print(f"\n🏷️ 클러스터 {cid} [{status}] (총 {total}개)")
        print(f"  카테고리 다양성: {diversity}/4")
        for cat in all_categories:
            count = counts[cat]
            if count < min_acceptable:
                mark = "🔴"  # 3개 미만은 긴급
            elif count >= ideal_per_cat:
                mark = "✓"  # 10개 이상은 이상적
            else:
                mark = "⚠"  # 3~9개는 허용
            print(f"  {mark} {cat}: {count}개")
        
        if is_oversized:
            print(f"  🔴 크기 초과: {max_size}개 제한을 {total - max_size}개 초과!")
    
    print("\n" + "="*70)
    print(f"✅ 이상적 클러스터: {ideal_count}개 (모든 카테고리 10개 이상)")
    print(f"⚠️ 허용 클러스터: {acceptable_count - ideal_count}개 (모든 카테고리 3개 이상)")
    print(f"🔴 긴급 병합 필요: {critical_count}개 (3개 미만 카테고리 있음)")
    if oversized_count > 0:
        print(f"🔴 크기 초과 클러스터: {oversized_count}개")
    print("="*70)


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    base_dir = r"C:\Users\changjin\workspace\lab\pln"
    data_path = os.path.join(base_dir, "data_set", "clustering_category_combine.csv")
    out_dir = os.path.join(base_dir, "clustering")
    os.makedirs(out_dir, exist_ok=True)

    df = pd.read_csv(data_path)
    print(f"✅ 데이터 로드 완료 ({len(df)}개 장소)")

    # 1️⃣ 비율 기반 동적 할당 Greedy 클러스터링
    print("\n" + "="*70)
    print("📍 1단계: 비율 기반 동적 할당 Greedy 클러스터링 시작")
    print("="*70)
    clustered = greedy_cluster(
        df, 
        target_cluster_size=50,  # 목표 클러스터 크기 50개 (비율에 따라 분배)
        base_radius=0.8,         # 기본 반경 0.8km
        min_per_cat=3            # 각 카테고리 최소 3개 보장
    )
    print(f"\n📊 1차 클러스터 수: {len(clustered['cluster_id'].unique())}")

    # 2️⃣ 불만족 클러스터끼리만 병합 (3개 미만 카테고리 해소)
    merged = merge_unsatisfied_clusters(
        clustered, 
        min_per_cat=3,         # 최소 3개 이상 (3개 이상이면 OK) ⭐
        ideal_per_cat=10,      # 이상적으로는 10개 (참고용)
        max_cluster_size=70,   # 병합 후 최대 70개 제한 (비율 기반이라 좀 더 여유있게)
        merge_radius=5.0,      # 병합 반경 5km
        max_iterations=10      # 최대 10회 반복
    )
    print(f"📊 병합 후 최종 클러스터 수: {len(merged['cluster_id'].unique())}")

    # 3️⃣ 품질 보고서 출력
    print_cluster_report(merged, min_acceptable=3, ideal_per_cat=10, max_size=70)

    # 4️⃣ 시각화
    visualize_clusters(clustered, os.path.join(out_dir, "step1_greedy.png"), "📍 1단계 Greedy 클러스터링")
    visualize_clusters(merged, os.path.join(out_dir, "step2_merged.png"), "📍 2단계 불만족 클러스터 병합")

    # 5️⃣ JSON 저장
    hotzones = build_hotzones(merged)
    json_path = os.path.join(out_dir, "greedy_hotzones_merged.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(hotzones, f, ensure_ascii=False, indent=2)
    print(f"💾 Hotzones JSON 저장 완료: {json_path}")

    print("\n✨ 비율 기반 동적 할당 + 3개 최소 기준 클러스터링 완료!")