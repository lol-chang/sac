import os
import json
import pandas as pd
import numpy as np
from haversine import haversine, Unit
import logging
from datetime import datetime, timedelta

# ========================================
# 설정
# ========================================
CONFIG = {
    "USER_INFO_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\1000_user_info.csv",
    "USER_PREF_DIR": r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\for_clustering_user",
    "PLACE_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\last_clustering_category_combine_with_hours_and_price.csv",
    "OUTPUT_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\user_based_clusters_greedy",
    "LOG_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\logs",
    "PLACES_PER_CATEGORY": 15,  # 각 카테고리별 최대 장소 수
    "MAX_CLUSTER_RADIUS_KM": 6,  # 클러스터 최대 반경
    "MIN_PLACES_PER_CATEGORY": 7,  # Seed 검증: 각 카테고리별 최소 장소 수
}

# Accommodation 제외: Cafe, Restaurant, Attraction만 사용
CLUSTER_CATEGORIES = ['Cafe', 'Restaurant', 'Attraction']

# 요일 매핑 (한글 → 영어)
WEEKDAY_MAP = {
    '일': 'Sunday',
    '월': 'Monday', 
    '화': 'Tuesday',
    '수': 'Wednesday',
    '목': 'Thursday',
    '금': 'Friday',
    '토': 'Saturday'
}

WEEKDAY_ENG_TO_KOR = {v: k for k, v in WEEKDAY_MAP.items()}

# 피크 시즌 월
PEAK_MONTHS = [7, 8, 12, 1]  # 7월, 8월, 12월, 1월

# 주말 요일 (한글)
WEEKEND_DAYS = ['금', '토']  # 금요일, 토요일

# 로깅 설정
logger = None

def setup_logging(log_dir):
    """로깅 설정"""
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"clustering_{timestamp}.log")
    
    global logger
    logger = logging.getLogger('clustering')
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(message)s')
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return log_file


def log_print(message):
    """콘솔과 로그 파일 모두에 출력"""
    if logger:
        logger.info(message)
    else:
        print(message)


def get_weekday_from_date(date_str):
    """
    날짜 문자열에서 요일 추출
    Args:
        date_str: '2025-08-16' 형식
    Returns:
        요일 한글 (예: '토')
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    weekday_eng = date_obj.strftime('%A')  # 'Saturday'
    return WEEKDAY_ENG_TO_KOR.get(weekday_eng, '월')


def is_peak_season(date_str):
    """
    피크 시즌 여부 판단
    Args:
        date_str: '2025-08-16' 형식
    Returns:
        bool: 7월, 8월, 12월, 1월이면 True
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.month in PEAK_MONTHS


def is_weekend(weekday_kor):
    """
    주말 여부 판단
    Args:
        weekday_kor: 한글 요일 (예: '토')
    Returns:
        bool: 금요일, 토요일이면 True
    """
    return weekday_kor in WEEKEND_DAYS


def parse_store_hours(store_hours_str):
    """
    영업시간 문자열 파싱
    Args:
        store_hours_str: '일: 10:30 - 20:00; 월: 10:30 - 20:00; 화: 휴무; ...'
    Returns:
        dict: {'일': 'open', '월': 'open', '화': 'closed', ...}
    """
    if pd.isna(store_hours_str) or store_hours_str.strip() == '':
        # 영업시간 정보 없음 → 모든 요일 영업으로 간주
        return {day: 'open' for day in WEEKDAY_MAP.keys()}
    
    hours_dict = {}
    
    # 세미콜론으로 분리
    parts = store_hours_str.split(';')
    
    for part in parts:
        part = part.strip()
        if ':' not in part:
            continue
        
        # '일: 10:30 - 20:00' 또는 '화: 휴무'
        day, info = part.split(':', 1)
        day = day.strip()
        info = info.strip()
        
        if day in WEEKDAY_MAP.keys():
            if '휴무' in info:
                hours_dict[day] = 'closed'
            else:
                hours_dict[day] = 'open'
    
    # 명시되지 않은 요일은 영업으로 간주
    for day in WEEKDAY_MAP.keys():
        if day not in hours_dict:
            hours_dict[day] = 'open'
    
    return hours_dict


def is_open_on_day(store_hours_str, target_day):
    """
    특정 요일에 영업하는지 확인
    Args:
        store_hours_str: 영업시간 문자열
        target_day: 확인할 요일 (한글, 예: '토')
    Returns:
        bool: 영업 여부
    """
    hours_dict = parse_store_hours(store_hours_str)
    return hours_dict.get(target_day, 'open') == 'open'


def load_place_locations(place_file):
    """장소 위경도, 영업시간, 가격 정보 로드"""
    df = pd.read_csv(place_file)
    location_dict = {}

    for _, row in df.iterrows():
        location_dict[row['id']] = {
            'latitude': row['latitude'],
            'longitude': row['longitude'],
            'name': row['name'],
            'category': row['category'],
            'store_hours': row.get('store_hours', ''),
            # 가격 정보 추가
            'offpeak_weekday_price_avg': row.get('offpeak_weekday_price_avg', None),
            'offpeak_weekend_price_avg': row.get('offpeak_weekend_price_avg', None),
            'peak_weekday_price_avg': row.get('peak_weekday_price_avg', None),
            'peak_weekend_price_avg': row.get('peak_weekend_price_avg', None),
        }

    return location_dict


def extract_all_user_places(user_pref_file, location_dict):
    """유저 선호도 장소 추출 (Accommodation 제외)"""
    with open(user_pref_file, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    
    user_places = []
    
    for category, places in preferences.items():
        # Accommodation 제외
        if category not in CLUSTER_CATEGORIES:
            continue
        
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
                    'final_score': place['final_score'],
                    'store_hours': loc['store_hours']
                })
    
    return pd.DataFrame(user_places)


def validate_seed(seed_location, available_df, max_radius_km, min_places_per_category):
    """
    Seed가 적합한지 검증: 주변에 각 카테고리별로 최소 개수 이상의 장소가 있는지 확인
    """
    category_counts = {}
    
    for category in CLUSTER_CATEGORIES:
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
    """Seed 위치에서 가장 가까운 N개의 장소 찾기"""
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


def greedy_clustering(df, n_clusters, start_date, places_per_category, max_radius_km, min_places_per_category):
    """
    Greedy 방식 클러스터링 (Accommodation 제외, 영업시간 체크)
    """
    clusters = []
    cluster_centers = []
    used_place_ids = set()
    available_df = df.copy()
    
    # 시작 날짜 datetime 객체로 변환
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    
    for cluster_idx in range(n_clusters):
        # 해당 클러스터의 날짜 계산 (시작일 + cluster_idx일)
        cluster_date = start_date_obj + timedelta(days=cluster_idx)
        cluster_date_str = cluster_date.strftime('%Y-%m-%d')
        cluster_weekday = get_weekday_from_date(cluster_date_str)
        
        log_print(f"\n{'='*70}")
        log_print(f"📅 Day {cluster_idx} - {cluster_date_str} ({cluster_weekday}요일)")
        log_print(f"{'='*70}")
        
        # 사용 가능한 Seed 후보 필터링 (이미 사용된 장소 제외)
        available_seeds = available_df[~available_df['id'].isin(used_place_ids)].copy()
        
        if len(available_seeds) == 0:
            log_print(f"⚠️ 클러스터 {cluster_idx}: 더 이상 사용 가능한 장소 없음")
            break
        
        # 영업시간 체크: 해당 날짜의 요일에 휴무인 장소 제외
        available_seeds['is_open'] = available_seeds['store_hours'].apply(
            lambda x: is_open_on_day(x, cluster_weekday)
        )
        
        # 휴무인 장소 로그 출력
        closed_places = available_seeds[~available_seeds['is_open']]
        if len(closed_places) > 0:
            log_print(f"   📅 {cluster_weekday}요일 휴무로 Seed 후보에서 제외: {len(closed_places)}개")
            for _, place in closed_places.head(10).iterrows():
                log_print(f"      - {place['name']} ({place['category']}, Score: {place['final_score']:.4f})")
        
        available_seeds = available_seeds[available_seeds['is_open']].copy()
        
        if len(available_seeds) == 0:
            log_print(f"⚠️ 클러스터 {cluster_idx}: {cluster_weekday}요일에 영업하는 장소 없음")
            log_print(f"   → 영업시간 무시하고 진행")
            available_seeds = available_df[~available_df['id'].isin(used_place_ids)].copy()
        
        # 모든 클러스터에서 final_score 순으로 정렬
        seed_candidates = available_seeds.sort_values('final_score', ascending=False)
        
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
                log_print(f"✅ 클러스터 {cluster_idx} Seed 검증 통과: {candidate['name']} ({candidate['category']})")
                for cat, cnt in category_counts.items():
                    log_print(f"   {cat}: {cnt}개 사용 가능")
                break
            else:
                failed_cats = [cat for cat, cnt in category_counts.items() if cnt < min_places_per_category]
                log_print(f"❌ Seed 후보 '{candidate['name']}' 검증 실패: {', '.join(failed_cats)} 부족")
        
        if seed_place is None:
            log_print(f"⚠️ 클러스터 {cluster_idx}: 검증을 통과한 Seed를 찾을 수 없음")
            seed_place = seed_candidates.iloc[0]
            seed_location = (seed_place['latitude'], seed_place['longitude'])
            log_print(f"⚠️ 검증 없이 진행: {seed_place['name']}")
        
        if len(cluster_centers) > 0:
            min_dist = min([haversine(seed_location, c, unit=Unit.KILOMETERS) for c in cluster_centers])
            log_print(f"🎯 클러스터 {cluster_idx} Seed: {seed_place['name']} ({seed_place['category']}, Score: {seed_place['final_score']:.4f}, 최근접 클러스터: {min_dist:.1f}km)")
        else:
            log_print(f"🎯 클러스터 {cluster_idx} Seed: {seed_place['name']} ({seed_place['category']}, Score: {seed_place['final_score']:.4f})")
        
        seed_category = seed_place['category']
        cluster_places = {seed_category: [seed_place]}
        used_place_ids.add(seed_place['id'])
        
        for category in CLUSTER_CATEGORIES:
            if category == seed_category:
                n_to_find = places_per_category - 1
            else:
                n_to_find = places_per_category
            
            if n_to_find <= 0:
                continue
            
            available_category = available_df[
                (available_df['category'] == category) &
                (~available_df['id'].isin(used_place_ids))
            ]
            
            nearest = find_nearest_places(
                seed_location,
                available_category,
                category,
                n_to_find,
                max_radius_km
            )
            
            if category not in cluster_places:
                cluster_places[category] = []
            
            for _, place in nearest.iterrows():
                cluster_places[category].append(place)
                used_place_ids.add(place['id'])
            
            if len(nearest) > 0:
                avg_dist = nearest['distance'].mean()
                max_dist = nearest['distance'].max()
                log_print(f"   {category}: {len(cluster_places[category])}개 추가 (평균: {avg_dist:.1f}km, 최대: {max_dist:.1f}km)")
            else:
                log_print(f"   {category}: 0개 추가 ({max_radius_km}km 이내 사용 가능한 장소 없음)")
        
        center_lat = seed_location[0]
        center_lng = seed_location[1]
        cluster_centers.append((center_lat, center_lng))
        
        cluster_data = {
            'cluster_id': cluster_idx,
            'date': cluster_date_str,
            'weekday': cluster_weekday,
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
        
        for category in CLUSTER_CATEGORIES:
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
        log_print(f"✅ 클러스터 {cluster_idx} 완료: 총 {len(used_place_ids)}개 장소 사용됨")
    
    return clusters


def select_best_accommodation(user_pref_file, clusters, location_dict, start_date, budget, duration_days, 
                              distance_weight=0.15, max_distance_km=10.0):
    """
    예산을 고려하여 최적의 숙소 선택 (30~50% 허용 범위)
    """
    if len(clusters) == 0:
        return None
    
    coords = np.array([[c['center_lat'], c['center_lng']] for c in clusters])
    mean = coords.mean(axis=0)
    
    log_print(f"\n{'='*70}")
    log_print(f"🏨 숙소 선택 중...")
    log_print(f"{'='*70}")
    
    # =============================
    # 1️⃣ 가중 평균 중심 계산
    # =============================
    dist = np.array([haversine((mean[0], mean[1]), (c['center_lat'], c['center_lng']), unit=Unit.KILOMETERS)
                     for c in clusters])
    weights = 1 / (1 + dist**2)
    weighted_center = np.average(coords, axis=0, weights=weights)
    overall_center_lat, overall_center_lng = weighted_center
    
    # =============================
    # 2️⃣ 예산 계산 (30~50%)
    # =============================
    accommodation_nights = duration_days - 1  # 숙박 일수
    min_accommodation_budget = budget * 0.3
    max_accommodation_budget = budget * 0.5
    per_night_min = min_accommodation_budget / accommodation_nights
    per_night_max = max_accommodation_budget / accommodation_nights
    
    log_print(f"\n💰 예산 범위:")
    log_print(f"   - 전체 예산: {budget:,}원")
    log_print(f"   - 숙소 총 예산 범위: {min_accommodation_budget:,.0f}원 ~ {max_accommodation_budget:,.0f}원")
    log_print(f"   - 1박당 예산 범위: {per_night_min:,.0f}원 ~ {per_night_max:,.0f}원")
    
    # =============================
    # 3️⃣ 시즌 / 요일 판단
    # =============================
    peak = is_peak_season(start_date)
    start_weekday = get_weekday_from_date(start_date)
    weekend = is_weekend(start_weekday)
    
    season = "peak" if peak else "offpeak"
    day_type = "weekend" if weekend else "weekday"
    price_column = f"{season}_{day_type}_price_avg"
    
    log_print(f"\n📅 시즌/요일 정보:")
    log_print(f"   - 시즌: {season}")
    log_print(f"   - 요일: {day_type}")
    log_print(f"   - 적용 가격 컬럼: {price_column}")
    
    # =============================
    # 4️⃣ 후보 필터링
    # =============================
    with open(user_pref_file, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    
    accommodations = preferences.get('Accommodation', [])
    if len(accommodations) == 0:
        log_print("⚠️ 숙소 선호도 정보 없음")
        return None
    
    scored_accommodations = []
    for acc in accommodations:
        acc_id = acc['id']
        if acc_id not in location_dict:
            continue
        
        acc_info = location_dict[acc_id]
        acc_lat, acc_lng = acc_info['latitude'], acc_info['longitude']
        acc_price = acc_info.get(price_column)
        
        # 유효 가격 필터: 30~50% 예산 범위 내
        if pd.isna(acc_price) or acc_price is None:
            continue
        if acc_price < per_night_min or acc_price > per_night_max:
            continue
        
        # 거리 계산
        distance = haversine((overall_center_lat, overall_center_lng), (acc_lat, acc_lng), unit=Unit.KILOMETERS)
        if distance > max_distance_km:
            continue
        
        # 점수 계산 (선호도 85% + 거리 15%)
        preference_score = acc['final_score']
        distance_score = max(0, 1 - (distance / max_distance_km))
        final_score = (1 - distance_weight) * preference_score + distance_weight * distance_score
        
        scored_accommodations.append({
            'id': acc_id,
            'name': acc_info['name'],
            'price': acc_price,
            'distance': distance,
            'final_score': final_score
        })
    
    if len(scored_accommodations) == 0:
        log_print(f"⚠️ 1박당 {per_night_min:,.0f}~{per_night_max:,.0f}원 범위에 맞는 숙소 없음")
        return None
    
    # =============================
    # 5️⃣ 최종 선택
    # =============================
    scored_accommodations.sort(key=lambda x: x['final_score'], reverse=True)
    best = scored_accommodations[0]
    
    log_print(f"\n✅ 선택된 숙소: {best['name']}")
    log_print(f"   - 가격: {best['price']:,.0f}원")
    log_print(f"   - 거리: {best['distance']:.2f}km")
    log_print(f"   - 최종 점수: {best['final_score']:.4f}")
    
    return best['id']


def process_user(user_id, user_info, user_pref_dir, location_dict, output_dir):
    """단일 유저 처리"""
    user_pref_file = os.path.join(user_pref_dir, f"{user_id}_recommendations_softmax.json")
    
    if not os.path.exists(user_pref_file):
        log_print(f"⚠️ {user_id} 파일 없음")
        return
    
    duration_days = user_info['duration_days']
    start_date = user_info['start_date']
    budget = user_info['budget']
    
    start_weekday = get_weekday_from_date(start_date)
    
    log_print(f"\n{'='*70}")
    log_print(f"👤 {user_id} 처리 중...")
    log_print(f"{'='*70}")
    log_print(f"   여행 일수: {duration_days}일")
    log_print(f"   시작 날짜: {start_date} ({start_weekday}요일)")
    log_print(f"   예산: {budget:,}원")
    
    df = extract_all_user_places(user_pref_file, location_dict)
    
    log_print(f"✅ 추출된 장소: {len(df)}개")
    for cat in CLUSTER_CATEGORIES:
        count = len(df[df['category'] == cat])
        log_print(f"   {cat}: {count}개")
    
    n_clusters = duration_days
    clusters = greedy_clustering(
        df,
        n_clusters,
        start_date,
        places_per_category=CONFIG['PLACES_PER_CATEGORY'],
        max_radius_km=CONFIG['MAX_CLUSTER_RADIUS_KM'],
        min_places_per_category=CONFIG['MIN_PLACES_PER_CATEGORY']
    )
    
    log_print(f"\n✅ Greedy 클러스터링 완료: {len(clusters)}개 클러스터")
    
    # 숙소 선택 (1일 여행이면 스킵)
    accommodation_id = None
    if duration_days > 1:
        accommodation_id = select_best_accommodation(
            user_pref_file,
            clusters,
            location_dict,
            start_date,
            budget,
            duration_days,
            distance_weight=0.15,
            max_distance_km=10.0
        )
    else:
        log_print(f"\n🏨 1일 여행으로 숙소 불필요")
    
    result = {
        'user_id': user_id,
        'start_date': start_date,
        'start_weekday': start_weekday,
        'duration_days': duration_days,
        'budget': budget,
        'num_clusters': len(clusters),
        'clustering_method': 'greedy_score_based_with_store_hours',
        'seed_strategy': 'highest_score_only',
        'max_cluster_radius_km': CONFIG['MAX_CLUSTER_RADIUS_KM'],
        'min_places_per_category': CONFIG['MIN_PLACES_PER_CATEGORY'],
        'places_per_category': CONFIG['PLACES_PER_CATEGORY'],
        'Accommodation': accommodation_id,
        'clusters': clusters
    }
    
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{user_id}_daily_clusters.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    log_print(f"\n💾 저장 완료: {output_file}")


def process_all_users():
    """모든 유저 일괄 처리"""
    log_file = setup_logging(CONFIG['LOG_DIR'])
    log_print(f"📝 로그 파일: {log_file}\n")
    
    os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
    
    log_print("📂 장소 위치 정보 로드 중...")
    location_dict = load_place_locations(CONFIG['PLACE_FILE'])
    log_print(f"✅ {len(location_dict)}개 장소 위치 정보 로드 완료\n")
    
    user_df = pd.read_csv(CONFIG['USER_INFO_FILE'])
    
    for idx, user in user_df.iterrows():
        user_id = user['user_id']
        user_info = {
            'duration_days': user['duration_days'],
            'start_date': user['start_date'],
            'budget': user['budget']
        }
        
        process_user(user_id, user_info, CONFIG['USER_PREF_DIR'],
                     location_dict, CONFIG['OUTPUT_DIR'])
    
    log_print(f"\n{'='*70}")
    log_print(f"✨ 전체 유저 처리 완료! 총 {len(user_df)}명")
    log_print(f"📝 로그 저장 완료: {log_file}")
    log_print(f"{'='*70}")


if __name__ == "__main__":
    process_all_users()