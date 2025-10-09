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
# 🧩 1단계: 비율 기반 Greedy Cluster
# ========================================
def greedy_cluster(df, target_cluster_size=50, base_radius=0.8, min_per_cat=3):
    """
    비율 기반 동적 할당으로 균형잡힌 클러스터 생성
    """
    df = df.copy()
    df["assigned"] = False
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    clusters = []
    cluster_id = 0
    
    # 카테고리별 비율 계산
    category_counts = df["category"].value_counts().to_dict()
    total_places = len(df)
    category_ratios = {cat: category_counts.get(cat, 0) / total_places for cat in all_categories}
    
    # 희귀한 순서로 정렬
    rarity_order = sorted(category_counts.keys(), key=lambda x: category_counts[x])
    
    print(f"\n📊 카테고리 분포 및 비율:")
    for cat in all_categories:
        count = category_counts.get(cat, 0)
        ratio = category_ratios[cat]
        print(f"  {cat}: {count}개 ({ratio*100:.1f}%)")
    
    # 각 클러스터의 목표 개수 계산
    target_per_cat = {}
    for cat in all_categories:
        calculated = int(target_cluster_size * category_ratios[cat])
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
        
        if seed_idx is None:
            seed_idx = df[df["assigned"] == False].index[0]
        
        seed = df.loc[seed_idx]
        cluster_points = [seed_idx]
        df.at[seed_idx, "assigned"] = True

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
            if all(cat_count[cat] >= target_per_cat[cat] for cat in all_categories):
                break
                
            point = df.loc[i]
            dist = point["distance"]
            radius = base_radius * (1 + len(cluster_points) / 20)

            if dist > radius:
                continue

            cat = point["category"]
            
            if cat_count[cat] >= target_per_cat[cat]:
                continue

            cluster_points.append(i)
            df.at[i, "assigned"] = True
            cat_count[cat] += 1

        df.loc[cluster_points, "cluster_id"] = cluster_id
        
        total = sum(cat_count.values())
        diversity = sum(1 for count in cat_count.values() if count > 0)
        print(f"  C{cluster_id}: 총 {total}개 (다양성: {diversity}/4) | " + 
              " | ".join([f"{cat[:3]}: {cat_count[cat]}" for cat in all_categories]))
        
        cluster_id += 1
        clusters.append(cluster_points)

    # 미할당 장소 처리
    unassigned = df[df["assigned"] == False]
    if len(unassigned) > 0:
        print(f"\n⚠️ 미할당 장소 {len(unassigned)}개 → 소형 클러스터로 그룹화")
        
        unassigned_df = df[df["assigned"] == False].copy()
        
        while len(unassigned_df) > 0:
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
            
            for idx, row in unassigned_df.iterrows():
                dist = haversine_km(
                    (seed["latitude"], seed["longitude"]),
                    (row["latitude"], row["longitude"])
                )
                if dist <= 2.0:
                    small_cluster.append(idx)
                    df.at[idx, "assigned"] = True
            
            df.loc[small_cluster, "cluster_id"] = cluster_id
            
            cat_count = df.loc[small_cluster, "category"].value_counts().to_dict()
            total = len(small_cluster)
            diversity = sum(1 for cat in all_categories if cat_count.get(cat, 0) > 0)
            print(f"  C{cluster_id}: 총 {total}개 (소형, 다양성: {diversity}/4) | " + 
                  " | ".join([f"{cat[:3]}: {cat_count.get(cat, 0)}" 
                             for cat in all_categories]))
            
            cluster_id += 1
            unassigned_df = df[df["assigned"] == False].copy()

    return df


# ========================================
# 🔄 2단계: 불만족 클러스터 병합
# ========================================
def merge_unsatisfied_clusters(df, min_per_cat=3, ideal_per_cat=10, min_cluster_size=15, max_cluster_size=70, merge_radius=8.0, max_iterations=15):
    """
    불만족 클러스터끼리만 병합
    """
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    
    for iteration in range(max_iterations):
        print(f"\n🔄 병합 반복 {iteration + 1}회차...")
        
        acceptable_clusters = set()
        critical_clusters = []
        
        for cid, group in df.groupby("cluster_id"):
            cat_counts = group["category"].value_counts().to_dict()
            counts = {cat: cat_counts.get(cat, 0) for cat in all_categories}
            total_size = len(group)
            
            is_too_small = total_size < min_cluster_size
            has_insufficient = any(count < min_per_cat for count in counts.values())
            
            if is_too_small or has_insufficient:
                size_penalty = max(0, min_cluster_size - total_size) * 5
                insufficient_score = sum(max(0, min_per_cat - count) * 10 for count in counts.values())
                zero_count = sum(1 for count in counts.values() if count == 0)
                diversity = sum(1 for count in counts.values() if count > 0)
                priority = zero_count * 1000 + size_penalty + insufficient_score + (4 - diversity) * 10
                critical_clusters.append((priority, cid, total_size))
            else:
                acceptable_clusters.add(cid)
        
        print(f"  ✅ 허용 가능 클러스터: {len(acceptable_clusters)}개")
        print(f"  🔴 긴급 병합 필요: {len(critical_clusters)}개")
        
        if not critical_clusters:
            print(f"✅ 모든 클러스터가 최소 조건 만족! (반복 {iteration + 1}회)")
            break
        
        critical_clusters.sort(reverse=True)
        merged_count = 0
        
        for priority, cid, size1 in critical_clusters:
            if cid not in df["cluster_id"].values:
                continue
            
            current_group = df[df["cluster_id"] == cid]
            current_counts = current_group["category"].value_counts().to_dict()
            current_dict = {cat: current_counts.get(cat, 0) for cat in all_categories}
            current_size = len(current_group)
            
            if current_size >= min_cluster_size and all(count >= min_per_cat for count in current_dict.values()):
                continue
            
            center1 = current_group[["latitude", "longitude"]].mean()
            best_target = None
            best_score = -1
            
            for _, target_cid, size2 in critical_clusters:
                if target_cid == cid or target_cid not in df["cluster_id"].values:
                    continue
                
                target_group = df[df["cluster_id"] == target_cid]
                target_counts = target_group["category"].value_counts().to_dict()
                target_dict = {cat: target_counts.get(cat, 0) for cat in all_categories}
                target_size = len(target_group)
                
                if target_size >= min_cluster_size and all(count >= min_per_cat for count in target_dict.values()):
                    continue
                
                merged_size = current_size + target_size
                if merged_size > max_cluster_size:
                    continue
                
                center2 = target_group[["latitude", "longitude"]].mean()
                dist = haversine_km(tuple(center1), tuple(center2))
                
                if dist > merge_radius:
                    continue
                
                complementary_score = 0
                
                size_score = (min_cluster_size - current_size) + (min_cluster_size - target_size)
                complementary_score += max(0, size_score) * 3
                
                for cat in all_categories:
                    c1 = current_dict[cat]
                    c2 = target_dict[cat]
                    
                    if c1 == 0 and c2 > 0:
                        complementary_score += c2 * 50
                    elif c2 == 0 and c1 > 0:
                        complementary_score += c1 * 50
                    elif c1 < min_per_cat and c2 > 0:
                        needed = min_per_cat - c1
                        complementary_score += min(c2, needed) * 20
                    elif c2 < min_per_cat and c1 > 0:
                        needed = min_per_cat - c2
                        complementary_score += min(c1, needed) * 20
                    elif c1 < ideal_per_cat and c2 > 0:
                        complementary_score += c2
                    elif c2 < ideal_per_cat and c1 > 0:
                        complementary_score += c1
                
                score = complementary_score - dist * 1.5
                
                if score > best_score:
                    best_score = score
                    best_target = target_cid
            
            if best_target is not None:
                df.loc[df["cluster_id"] == cid, "cluster_id"] = best_target
                merged_count += 1
                dist_to_target = haversine_km(
                    tuple(center1),
                    tuple(df[df["cluster_id"] == best_target][["latitude", "longitude"]].mean())
                )
                merged_size = len(df[df["cluster_id"] == best_target])
                print(f"  ⚡ C{cid}({current_size}개) → C{best_target} 병합 (거리: {dist_to_target:.2f}km, 병합 후: {merged_size}개)")
        
        if merged_count == 0:
            print(f"⚠️ 더 이상 병합할 수 없음 (반복 {iteration + 1}회)")
            break
        
        df["cluster_id"] = df["cluster_id"].astype(int)
        new_ids = {old: new for new, old in enumerate(sorted(df["cluster_id"].unique()))}
        df["cluster_id"] = df["cluster_id"].map(new_ids)
        
        print(f"  📊 현재 클러스터 수: {len(df['cluster_id'].unique())}")
    
    return df


# ========================================
# 🧱 Hotzone JSON 생성
# ========================================
def build_hotzones(df, target_per_cat=None):
    """
    Hotzone JSON 생성 - 카테고리별 고정 개수 할당
    """
    hotzones = []
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    
    # 카테고리별 목표 개수 설정
    if target_per_cat is None:
        target_per_cat = {
            "Accommodation": 30,
            "Cafe": 10,
            "Restaurant": 25,
            "Attraction": 10
        }
    
    print(f"\n🎯 카테고리별 목표 개수:")
    for cat in all_categories:
        print(f"  {cat}: {target_per_cat[cat]}개")

    for cid, group in df.groupby("cluster_id"):
        center_lat = group["latitude"].mean()
        center_lng = group["longitude"].mean()
        center_coord = (center_lat, center_lng)

        categories = {}
        
        for cat in all_categories:
            cat_group = group[group["category"] == cat]
            current_count = len(cat_group)
            cat_target = target_per_cat[cat]
            
            items = []
            
            if current_count < cat_target:
                # 전체 데이터에서 해당 카테고리 찾기
                all_cat_places = df[df["category"] == cat].copy()
                
                # 중심으로부터 거리 계산
                all_cat_places["distance_to_center"] = all_cat_places.apply(
                    lambda r: haversine_km(
                        center_coord,
                        (r["latitude"], r["longitude"])
                    ), axis=1
                )
                
                # 가장 가까운 cat_target개 선택
                nearest = all_cat_places.nsmallest(cat_target, "distance_to_center")
                
                for idx, row in nearest.iterrows():
                    items.append({
                        "id": int(row["id"]) if "id" in row and not pd.isna(row["id"]) else idx,
                        "name": row["name"],
                        "final_score": round(np.random.uniform(0.5, 0.9), 2),
                        "distance_from_center": round(row["distance_to_center"], 2)
                    })
                
                added = len(items) - current_count
                if added > 0:
                    print(f"  ✅ C{cid} {cat}: {current_count}개 → {len(items)}개 (가까운 곳 {added}개 추가)")
            else:
                # 이미 충분하면 현재 클러스터에서만
                for idx, row in cat_group.head(cat_target).iterrows():
                    distance = haversine_km(center_coord, (row["latitude"], row["longitude"]))
                    items.append({
                        "id": int(row["id"]) if "id" in row and not pd.isna(row["id"]) else idx,
                        "name": row["name"],
                        "final_score": round(np.random.uniform(0.5, 0.9), 2),
                        "distance_from_center": round(distance, 2)
                    })
            
            categories[cat] = items

        hotzone = {
            "cluster_id": int(cid),
            "center_lat": round(center_lat, 6),
            "center_lng": round(center_lng, 6),
            "hotzone_score": round(
                min(1.0, len(group) / 50 + sum(len(v) for v in categories.values()) / 100), 2
            ),
            "category_diversity": sum(len(v) > 0 for v in categories.values()),
            "total_places": sum(len(v) for v in categories.values()),
            "original_cluster_size": len(group),
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
def print_cluster_report(df, min_acceptable=3, min_size=15, ideal_per_cat=10, max_size=70):
    all_categories = ["Accommodation", "Cafe", "Restaurant", "Attraction"]
    print("\n" + "="*70)
    print("📊 클러스터 품질 보고서")
    print("="*70)
    
    acceptable_count = 0
    ideal_count = 0
    critical_count = 0
    oversized_count = 0
    
    for cid, group in df.groupby("cluster_id"):
        cat_counts = group["category"].value_counts().to_dict()
        counts = {cat: cat_counts.get(cat, 0) for cat in all_categories}
        total = len(group)
        diversity = sum(1 for count in counts.values() if count > 0)
        
        is_too_small = total < min_size
        has_insufficient = any(count < min_acceptable for count in counts.values())
        is_ideal = all(count >= ideal_per_cat for count in counts.values())
        is_oversized = total > max_size
        
        if is_too_small or has_insufficient:
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
        
        if is_too_small:
            print(f"  🔴 크기 부족: 최소 {min_size}개 필요 (현재 {total}개)")
        
        for cat in all_categories:
            count = counts[cat]
            if count < min_acceptable:
                mark = "🔴"
            elif count >= ideal_per_cat:
                mark = "✓"
            else:
                mark = "⚠"
            print(f"  {mark} {cat}: {count}개")
        
        if is_oversized:
            print(f"  🔴 크기 초과: {max_size}개 제한을 {total - max_size}개 초과!")
    
    print("\n" + "="*70)
    print(f"✅ 이상적 클러스터: {ideal_count}개")
    print(f"⚠️ 허용 클러스터: {acceptable_count - ideal_count}개")
    print(f"🔴 긴급 병합 필요: {critical_count}개")
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
        target_cluster_size=50,
        base_radius=0.8,
        min_per_cat=3
    )
    print(f"\n📊 1차 클러스터 수: {len(clustered['cluster_id'].unique())}")

    # 2️⃣ 불만족 클러스터끼리만 병합
    merged = merge_unsatisfied_clusters(
        clustered, 
        min_per_cat=3,
        ideal_per_cat=10,
        min_cluster_size=15,
        max_cluster_size=70,
        merge_radius=8.0,
        max_iterations=15
    )
    print(f"📊 병합 후 최종 클러스터 수: {len(merged['cluster_id'].unique())}")

    # 3️⃣ 품질 보고서 출력
    print_cluster_report(merged, min_acceptable=3, min_size=15, ideal_per_cat=10, max_size=70)

    # 4️⃣ 시각화
    visualize_clusters(clustered, os.path.join(out_dir, "step1_greedy.png"), "📍 1단계 Greedy 클러스터링")
    visualize_clusters(merged, os.path.join(out_dir, "step2_merged.png"), "📍 2단계 불만족 클러스터 병합")

    # 5️⃣ JSON 저장
    print("\n" + "="*70)
    print("📦 5단계: Hotzone JSON 생성 (숙소:30개, 식당:25개, 카페:10개, 관광:10개)")
    print("="*70)
    hotzones = build_hotzones(merged)  # 자동으로 데이터 분포에 맞게 계산
    json_path = os.path.join(out_dir, "greedy_hotzones_merged.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(hotzones, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Hotzones JSON 저장 완료: {json_path}")
    print(f"📊 총 {len(hotzones['hotzones'])}개 Hotzone 생성")

    print("\n✨ 비율 기반 동적 할당 + 크기/카테고리 기반 병합 완료!")