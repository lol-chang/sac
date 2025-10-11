import os
import json
import pandas as pd
import numpy as np
from haversine import haversine, Unit

# ========================================
# 설정
# ========================================
CONFIG = {
    "USER_INFO_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\1000_user_info.csv",
    "USER_PREF_DIR": r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\for_clustering_user",
    "PLACE_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\clustering_category_combine.csv",
    "OUTPUT_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\user_based_clusters_greedy",
    "PLACES_PER_CATEGORY": 10,  # 각 카테고리별 최대 장소 수
    "MAX_CLUSTER_RADIUS_KM": 15,  # 클러스터 최대 반경 (이보다 먼 곳은 포함 안 함)
    "MIN_PLACES_PER_CATEGORY": 5,  # Seed 검증: 각 카테고리별 최소 장소 수
    "CLUSTER_DISTANCE_WEIGHT": 0.3  # 다음 Seed 선택 시 거리 가중치 (0~1)
}

# Travel Style별 Seed 카테고리 정의
SEED_CATEGORY_MAP = {
    'Foodie': ['Restaurant'],
    'Healing': ['Accommodation'],
    'Activity': ['Attraction'],
    'Cultural': ['Attraction', 'Cafe']  # 번갈아가면서 사용
}

ALL_CATEGORIES = ['Accommodation', 'Cafe', 'Restaurant', 'Attraction']


def load_place_locations(place_file):
    """하나의 통합 CSV에서 모든 장소의 위경도 정보 로드"""
    df = pd.read_csv(place_file)
    location_dict = {}

    for _, row in df.iterrows():
        location_dict[row['id']] = {
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'name': row['name'],
            'category': row['category']
        }

    return location_dict


def extract_all_user_places(user_pref_file, location_dict):
    """유저 선호도 모든 장소 추출 (위경도 포함)"""
    with open(user_pref_file, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    
    user_places = []
    
    for category, places in preferences.items():
        for place in places:
            place_id = place['id']
            if place_id in location_dict:
                loc = location_dict[place_id]
                user_places.append({
                    'id': place_id,
                    'name': loc['name'],
                    'category': category,
                    'latitude': loc['latitude'],
                    'longitude': loc['longitude'],
                    'final_score': place['final_score']
                })
    
    return pd.DataFrame(user_places)


def get_seed_category(travel_style, cluster_idx):
    """Travel Style과 클러스터 인덱스에 따른 Seed 카테고리 반환"""
    seed_categories = SEED_CATEGORY_MAP.get(travel_style, ['Attraction'])
    
    # Cultural의 경우 Attraction과 Cafe를 번갈아가면서
    if travel_style == 'Cultural':
        return seed_categories[cluster_idx % len(seed_categories)]
    
    return seed_categories[0]


def validate_seed(seed_location, available_df, max_radius_km, min_places_per_category):
    """
    Seed가 적합한지 검증: 주변에 각 카테고리별로 최소 개수 이상의 장소가 있는지 확인
    
    Returns:
        (is_valid, category_counts): (검증 통과 여부, 카테고리별 장소 개수)
    """
    category_counts = {}
    
    for category in ALL_CATEGORIES:
        # 해당 카테고리의 사용 가능한 장소들
        category_places = available_df[available_df['category'] == category].copy()
        
        if len(category_places) == 0:
            category_counts[category] = 0
            continue
        
        # Seed로부터 거리 계산
        category_places['distance'] = category_places.apply(
            lambda r: haversine(seed_location, 
                               (r['latitude'], r['longitude']),
                               unit=Unit.KILOMETERS),
            axis=1
        )
        
        # max_radius_km 이내의 장소 개수
        count = len(category_places[category_places['distance'] <= max_radius_km])
        category_counts[category] = count
    
    # 모든 카테고리가 최소 개수 이상인지 확인
    is_valid = all(count >= min_places_per_category for count in category_counts.values())
    
    return is_valid, category_counts


def find_nearest_places(seed_location, available_df, category, n_places, max_radius_km):
    """
    Seed 위치에서 가장 가까운 N개의 장소 찾기 (특정 카테고리)
    max_radius_km 이내의 장소만 선택 (반경 내에 없으면 적게 선택됨)
    """
    category_places = available_df[available_df['category'] == category].copy()
    
    if len(category_places) == 0:
        return pd.DataFrame()
    
    # Seed로부터 거리 계산
    category_places['distance'] = category_places.apply(
        lambda r: haversine(seed_location, 
                           (r['latitude'], r['longitude']),
                           unit=Unit.KILOMETERS),
        axis=1
    )
    
    # max_radius_km 이내의 장소만 필터링
    category_places = category_places[category_places['distance'] <= max_radius_km]
    
    if len(category_places) == 0:
        return pd.DataFrame()
    
    # 거리 가까운 순으로 정렬
    category_places = category_places.sort_values('distance', ascending=True)
    
    return category_places.head(n_places)


def greedy_clustering(df, n_clusters, travel_style, places_per_category, max_radius_km, min_places_per_category, cluster_distance_weight):
    """
    Greedy 방식으로 클러스터링
    
    1. Travel Style에 따른 Seed 카테고리에서 선택
    2. 첫 번째 Seed: final_score 가장 높은 것
    3. 이후 Seed: 기존 클러스터들과 멀리 떨어진 + 선호도 높은 장소
    4. **Seed 검증**: 주변 max_radius_km 이내에 각 카테고리별 최소 개수 이상 있어야 함
    5. 검증 통과한 Seed 주변에서 거리가 가까운 순서대로 최대 N개씩 선택
    6. 선택된 장소들은 사용 불가능으로 표시 (다음 클러스터에서 제외)
    7. n_clusters만큼 반복
    """
    clusters = []
    cluster_centers = []  # 각 클러스터의 중심 좌표
    used_place_ids = set()
    available_df = df.copy()
    
    for cluster_idx in range(n_clusters):
        # Seed 카테고리 결정
        seed_category = get_seed_category(travel_style, cluster_idx)
        
        # 사용 가능한 Seed 후보 필터링 (이미 클러스터에 포함된 장소 제외)
        available_seeds = available_df[
            (available_df['category'] == seed_category) &
            (~available_df['id'].isin(used_place_ids))
        ]
        
        if len(available_seeds) == 0:
            print(f"⚠️ 클러스터 {cluster_idx}: {seed_category}에서 사용 가능한 Seed 없음")
            # 다른 카테고리에서 시도
            available_seeds = available_df[~available_df['id'].isin(used_place_ids)]
            if len(available_seeds) == 0:
                print(f"⚠️ 클러스터 {cluster_idx}: 더 이상 사용 가능한 장소 없음")
                break
        
        # Seed 후보들을 점수순으로 정렬하여 순회
        if len(cluster_centers) == 0:
            # 첫 번째 클러스터: final_score 순으로 정렬
            seed_candidates = available_seeds.sort_values('final_score', ascending=False)
        else:
            # 이후 클러스터: 기존 클러스터와의 거리 + 선호도 고려
            seed_candidates = available_seeds.copy()
            for idx, row in seed_candidates.iterrows():
                seed_loc = (row['latitude'], row['longitude'])
                min_dist = min([haversine(seed_loc, c, unit=Unit.KILOMETERS) for c in cluster_centers])
                
                # 거리 정규화
                score_val = row['final_score']
                
                # 간단한 점수 계산 (정규화 없이)
                combined = score_val * (1 - cluster_distance_weight) + (min_dist / 100) * cluster_distance_weight
                seed_candidates.at[idx, 'seed_score'] = combined
            
            seed_candidates = seed_candidates.sort_values('seed_score', ascending=False)
        
        # 적합한 Seed 찾기 (검증 통과할 때까지)
        seed_place = None
        seed_location = None
        
        for _, candidate in seed_candidates.iterrows():
            candidate_location = (candidate['latitude'], candidate['longitude'])
            
            # Seed 검증
            is_valid, category_counts = validate_seed(
                candidate_location,
                available_df[~available_df['id'].isin(used_place_ids)],
                max_radius_km,
                min_places_per_category
            )
            
            if is_valid:
                seed_place = candidate
                seed_location = candidate_location
                print(f"✅ 클러스터 {cluster_idx} Seed 검증 통과: {candidate['name']}")
                for cat, cnt in category_counts.items():
                    print(f"   {cat}: {cnt}개 사용 가능")
                break
            else:
                # 검증 실패 - 다음 후보로
                failed_cats = [cat for cat, cnt in category_counts.items() if cnt < min_places_per_category]
                print(f"❌ Seed 후보 '{candidate['name']}' 검증 실패: {', '.join(failed_cats)} 부족")
        
        # 적합한 Seed를 찾지 못한 경우
        if seed_place is None:
            print(f"⚠️ 클러스터 {cluster_idx}: 검증을 통과한 Seed를 찾을 수 없음 (주변에 장소가 너무 적음)")
            # 검증 없이 가장 좋은 후보 사용
            seed_place = seed_candidates.iloc[0]
            seed_location = (seed_place['latitude'], seed_place['longitude'])
            print(f"⚠️ 검증 없이 진행: {seed_place['name']}")
        
        # 기존 클러스터와의 거리 정보 출력
        if len(cluster_centers) > 0:
            min_dist = min([haversine(seed_location, c, unit=Unit.KILOMETERS) for c in cluster_centers])
            print(f"🎯 클러스터 {cluster_idx} Seed: {seed_place['name']} ({seed_category}, Score: {seed_place['final_score']:.4f}, 최근접 클러스터: {min_dist:.1f}km)")
        else:
            print(f"🎯 클러스터 {cluster_idx} Seed: {seed_place['name']} ({seed_category}, Score: {seed_place['final_score']:.4f})")
        
        # Seed를 클러스터에 추가
        cluster_places = {seed_category: [seed_place]}
        used_place_ids.add(seed_place['id'])
        
        # 각 카테고리별로 거리 가까운 장소 찾기 (max_radius_km 이내만)
        for category in ALL_CATEGORIES:
            if category == seed_category:
                # Seed 카테고리는 이미 1개 있으므로 N-1개 더 찾기
                n_to_find = places_per_category - 1
            else:
                n_to_find = places_per_category
            
            if n_to_find <= 0:
                continue
            
            # 사용 가능한 장소만 필터링 (이미 클러스터에 포함된 장소 제외)
            available_category = available_df[
                (available_df['category'] == category) &
                (~available_df['id'].isin(used_place_ids))
            ]
            
            # 거리 가까운 장소 찾기 (max_radius_km 이내만)
            nearest = find_nearest_places(
                seed_location,
                available_category,
                category,
                n_to_find,
                max_radius_km
            )
            
            # 클러스터에 추가
            if category not in cluster_places:
                cluster_places[category] = []
            
            for _, place in nearest.iterrows():
                cluster_places[category].append(place)
                used_place_ids.add(place['id'])  # 사용된 장소 기록
            
            if len(nearest) > 0:
                avg_dist = nearest['distance'].mean()
                max_dist = nearest['distance'].max()
                print(f"   {category}: {len(cluster_places[category])}개 추가 (평균: {avg_dist:.1f}km, 최대: {max_dist:.1f}km)")
            else:
                print(f"   {category}: 0개 추가 ({max_radius_km}km 이내 사용 가능한 장소 없음)")
        
        # 클러스터 중심 = Seed 위치 (Seed 주변으로 클러스터링하기 위함)
        center_lat = seed_location[0]
        center_lng = seed_location[1]
        cluster_centers.append((center_lat, center_lng))  # 중심 좌표 저장
        
        # 클러스터 데이터 구성
        cluster_data = {
            'cluster_id': cluster_idx,
            'seed_category': seed_category,
            'seed_place': {
                'id': int(seed_place['id']),
                'name': seed_place['name'],
                'final_score': round(float(seed_place['final_score']), 4)
            },
            'center_lat': round(center_lat, 6),
            'center_lng': round(center_lng, 6),
            'categories': {}
        }
        
        # 각 카테고리별 장소 정리
        for category in ALL_CATEGORIES:
            places_list = []
            if category in cluster_places:
                for place in cluster_places[category]:
                    distance = haversine(
                        (center_lat, center_lng),
                        (place['latitude'], place['longitude']),
                        unit=Unit.KILOMETERS
                    )
                    places_list.append({
                        'id': int(place['id']),
                        'name': place['name'],
                        'final_score': round(float(place['final_score']), 4),
                        'distance_from_center': round(distance, 2)
                    })
            
            cluster_data['categories'][category] = places_list
        
        clusters.append(cluster_data)
        print(f"✅ 클러스터 {cluster_idx} 완료: 총 {len(used_place_ids)}개 장소 사용됨\n")
    
    return clusters


def process_user(user_id, user_info, user_pref_dir, location_dict, output_dir):
    """단일 유저 처리"""
    user_pref_file = os.path.join(user_pref_dir, f"{user_id}_recommendations_softmax.json")
    
    if not os.path.exists(user_pref_file):
        print(f"⚠️ {user_id} 파일 없음")
        return
    
    duration_days = user_info['duration_days']
    travel_style = user_info['travel_style']
    
    print(f"\n{'='*70}")
    print(f"👤 {user_id} 처리 중...")
    print(f"   여행 일수: {duration_days}일")
    print(f"   여행 스타일: {travel_style}")
    print(f"{'='*70}")
    
    # 1️⃣ 유저 선호 모든 장소 추출
    df = extract_all_user_places(user_pref_file, location_dict)
    
    print(f"✅ 추출된 장소: {len(df)}개")
    for cat in ALL_CATEGORIES:
        count = len(df[df['category'] == cat])
        print(f"   {cat}: {count}개")
    
    # 2️⃣ Greedy 클러스터링
    n_clusters = duration_days
    clusters = greedy_clustering(
        df,
        n_clusters,
        travel_style,
        places_per_category=CONFIG['PLACES_PER_CATEGORY'],
        max_radius_km=CONFIG['MAX_CLUSTER_RADIUS_KM'],
        min_places_per_category=CONFIG['MIN_PLACES_PER_CATEGORY'],
        cluster_distance_weight=CONFIG['CLUSTER_DISTANCE_WEIGHT']
    )
    
    print(f"✅ Greedy 클러스터링 완료: {len(clusters)}개 클러스터")
    
    # 3️⃣ 결과 JSON 저장
    result = {
        'user_id': user_id,
        'travel_style': travel_style,
        'duration_days': duration_days,
        'num_clusters': len(clusters),
        'clustering_method': 'greedy_with_validation',
        'seed_strategy': f"{travel_style}_based",
        'max_cluster_radius_km': CONFIG['MAX_CLUSTER_RADIUS_KM'],
        'min_places_per_category': CONFIG['MIN_PLACES_PER_CATEGORY'],
        'places_per_category': CONFIG['PLACES_PER_CATEGORY'],
        'clusters': clusters
    }
    
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{user_id}_daily_clusters.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"💾 저장 완료: {output_file}")


def process_all_users():
    """모든 유저 일괄 처리"""
    os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
    
    # 장소 위치 정보 로드
    print("📂 장소 위치 정보 로드 중...")
    location_dict = load_place_locations(CONFIG['PLACE_FILE'])
    print(f"✅ {len(location_dict)}개 장소 위치 정보 로드 완료\n")
    
    # 유저 정보 로드
    user_df = pd.read_csv(CONFIG['USER_INFO_FILE'])
    
    for idx, user in user_df.iterrows():
        user_id = user['user_id']
        user_info = {
            'duration_days': user['duration_days'],
            'travel_style': user['travel_style']
        }
        
        process_user(user_id, user_info, CONFIG['USER_PREF_DIR'],
                     location_dict, CONFIG['OUTPUT_DIR'])
    
    print(f"\n✨ 전체 유저 처리 완료! 총 {len(user_df)}명")


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    # 옵션 1: 특정 유저 테스트
    # location_dict = load_place_locations(CONFIG['PLACE_FILE'])
    # process_user('U0001', {'duration_days': 3, 'travel_style': 'Healing'},
    #              CONFIG['USER_PREF_DIR'], location_dict, CONFIG['OUTPUT_DIR'])
    
    # 옵션 2: 전체 유저 처리
    process_all_users()