import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Circle
import numpy as np

# ========================================
# 설정
# ========================================
CONFIG = {
    "CLUSTER_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\user_based_clusters_greedy",
    "PLACE_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\clustering_category_combine.csv",
    "OUTPUT_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\visualizations",
}

# 고정 축 범위 설정 (위경도)
FIXED_AXIS = {
    "lat_min": None,  # 자동 계산 또는 수동 설정
    "lat_max": None,
    "lng_min": None,
    "lng_max": None,
}

# 클러스터별 색상 (최대 10개)
CLUSTER_COLORS = [
    '#e74c3c',  # 빨강
    '#3498db',  # 파랑
    '#2ecc71',  # 초록
    '#f39c12',  # 주황
    '#9b59b6',  # 보라
    '#1abc9c',  # 청록
    '#e67e22',  # 진한 주황
    '#34495e',  # 회색
    '#16a085',  # 진한 청록
    '#c0392b'   # 진한 빨강
]

# 카테고리별 마커 (Accommodation 제외)
CATEGORY_MARKERS = {
    'Cafe': '^',           # 삼각형
    'Restaurant': 'o',     # 원
    'Attraction': '*'      # 별
}


def load_place_locations(place_file):
    """장소 위경도 정보 로드"""
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


def calculate_global_bounds(place_file, margin=0.02):
    """
    전체 장소의 위경도 범위를 계산
    
    Args:
        place_file: 장소 데이터 파일 경로
        margin: 여백 비율 (0.02 = 2%)
    
    Returns:
        dict: {'lat_min', 'lat_max', 'lng_min', 'lng_max'}
    """
    df = pd.read_csv(place_file)
    
    lat_min = df['latitude'].min()
    lat_max = df['latitude'].max()
    lng_min = df['longitude'].min()
    lng_max = df['longitude'].max()
    
    # 여백 추가
    lat_range = lat_max - lat_min
    lng_range = lng_max - lng_min
    
    bounds = {
        'lat_min': lat_min - lat_range * margin,
        'lat_max': lat_max + lat_range * margin,
        'lng_min': lng_min - lng_range * margin,
        'lng_max': lng_max + lng_range * margin,
    }
    
    print(f"\n📍 전체 위경도 범위:")
    print(f"   위도: {bounds['lat_min']:.4f} ~ {bounds['lat_max']:.4f}")
    print(f"   경도: {bounds['lng_min']:.4f} ~ {bounds['lng_max']:.4f}")
    
    return bounds


def create_user_cluster_plot(cluster_data, place_locations, axis_bounds):
    """
    matplotlib로 클러스터 시각화 (고정 축 범위, 숙소 포함)
    
    Args:
        cluster_data: 클러스터 JSON 데이터
        place_locations: {place_id: {'latitude': lat, 'longitude': lng, ...}}
        axis_bounds: 고정 축 범위 {'lat_min', 'lat_max', 'lng_min', 'lng_max'}
    """
    
    # Figure 생성
    fig, ax = plt.subplots(figsize=(16, 12))
    
    # 한글 폰트 설정 (Windows)
    plt.rcParams['font.family'] = 'Malgun Gothic'
    plt.rcParams['axes.unicode_minus'] = False
    
    # 숙소 위치 표시 (최상위에 표시하기 위해 먼저 처리)
    accommodation_id = cluster_data.get('Accommodation')
    if accommodation_id and accommodation_id in place_locations:
        acc_loc = place_locations[accommodation_id]
        acc_lat = acc_loc['latitude']
        acc_lng = acc_loc['longitude']
        acc_name = acc_loc['name']
        
        # 숙소 마커 (큰 집 모양 - 펜타곤)
        ax.scatter(acc_lng, acc_lat,
                  s=600, marker='H',  # Hexagon (육각형)
                  c='gold',
                  edgecolors='black',
                  linewidths=3,
                  label='Accommodation',
                  zorder=15,  # 가장 위에 표시
                  alpha=0.9)
        
        # 숙소 이름 텍스트
        ax.text(acc_lng, acc_lat + 0.01,  # 약간 위에 표시
               acc_name,
               fontsize=10,
               fontweight='bold',
               ha='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7),
               zorder=16)
    
    # 클러스터별로 플롯
    for cluster in cluster_data['clusters']:
        cluster_id = cluster['cluster_id']
        cluster_color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
        seed_place = cluster['seed_place']
        seed_id = seed_place['id']
        
        # Seed 위치
        if seed_id in place_locations:
            seed_loc = place_locations[seed_id]
            seed_lat = seed_loc['latitude']
            seed_lng = seed_loc['longitude']
            
            # Seed 마커 (큰 다이아몬드)
            ax.scatter(seed_lng, seed_lat, 
                      s=500, marker='D', 
                      c=cluster_color, 
                      edgecolors='black', 
                      linewidths=2.5,
                      label=f'Day {cluster_id + 1} Seed',
                      zorder=10)
        
        # 클러스터 중심
        center_lat = cluster['center_lat']
        center_lng = cluster['center_lng']
        
        # 클러스터 중심 마커 (X 표시)
        ax.scatter(center_lng, center_lat,
                  s=250, marker='x',
                  c=cluster_color,
                  linewidths=3,
                  zorder=9)
        
        # 각 카테고리별 장소
        for category, places in cluster['categories'].items():
            marker = CATEGORY_MARKERS.get(category, 'o')
            
            lngs = []
            lats = []
            
            for place in places:
                place_id = place['id']
                
                # Seed는 이미 표시했으므로 스킵
                if place_id == seed_id:
                    continue
                
                # 장소 위치
                if place_id not in place_locations:
                    continue
                
                place_loc = place_locations[place_id]
                lats.append(place_loc['latitude'])
                lngs.append(place_loc['longitude'])
            
            # 카테고리별 장소들 플롯
            if len(lats) > 0:
                ax.scatter(lngs, lats,
                          s=120, marker=marker,
                          c=cluster_color,
                          alpha=0.7,
                          edgecolors='white',
                          linewidths=1.5,
                          zorder=5)
        
        # 클러스터 범위 (원)
        max_distance = 0
        for category, places in cluster['categories'].items():
            for place in places:
                if place['distance_from_center'] > max_distance:
                    max_distance = place['distance_from_center']
        
        if max_distance > 0:
            # 위경도를 km로 변환 (대략적)
            # 위도 1도 ≈ 111km, 경도 1도 ≈ 88km (한국 기준)
            radius_lat = max_distance / 111
            radius_lng = max_distance / 88
            
            circle = Circle((center_lng, center_lat),
                          radius=radius_lat,
                          color=cluster_color,
                          fill=False,
                          linewidth=2,
                          linestyle='--',
                          alpha=0.5,
                          zorder=3)
            ax.add_patch(circle)
    
    # ★ 고정 축 범위 설정
    ax.set_xlim(axis_bounds['lng_min'], axis_bounds['lng_max'])
    ax.set_ylim(axis_bounds['lat_min'], axis_bounds['lat_max'])
    
    # 제목 및 레이블 (travel_style 대신 start_date 사용)
    user_id = cluster_data['user_id']
    duration_days = cluster_data['duration_days']
    start_date = cluster_data.get('start_date', 'N/A')
    start_weekday = cluster_data.get('start_weekday', '')
    
    title = f"{user_id} - {duration_days}일"
    if start_date != 'N/A':
        title += f" | 시작: {start_date} ({start_weekday}요일)"
    
    ax.set_title(title, fontsize=20, fontweight='bold', pad=20)
    ax.set_xlabel('경도 (Longitude)', fontsize=14)
    ax.set_ylabel('위도 (Latitude)', fontsize=14)
    
    # 그리드
    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
    
    # 범례 생성
    legend_elements = []
    
    # 숙소 범례 (최상단)
    legend_elements.append(
        plt.Line2D([0], [0], marker='H', color='w',
                  markerfacecolor='gold', markersize=14, markeredgewidth=2,
                  markeredgecolor='black',
                  label='🏨 Accommodation')
    )
    legend_elements.append(mpatches.Patch(color='none', label=''))  # 빈 줄
    
    # 클러스터별 범례
    for cluster in cluster_data['clusters']:
        cluster_id = cluster['cluster_id']
        cluster_color = CLUSTER_COLORS[cluster_id % len(CLUSTER_COLORS)]
        seed_cat = cluster.get('seed_category', 'N/A')
        cluster_date = cluster.get('date', '')
        cluster_weekday = cluster.get('weekday', '')
        
        label = f'Day {cluster_id + 1} ({seed_cat})'
        if cluster_date:
            label += f' - {cluster_weekday}'
        
        legend_elements.append(
            mpatches.Patch(color=cluster_color, label=label)
        )
    
    # 카테고리별 범례
    legend_elements.append(mpatches.Patch(color='none', label=''))  # 빈 줄
    
    # Seed 마커 범례
    legend_elements.append(
        plt.Line2D([0], [0], marker='D', color='w', 
                  markerfacecolor='gray', markersize=12, markeredgewidth=1.5,
                  label='Seed Place')
    )
    
    # 카테고리별 마커 범례
    for category, marker in CATEGORY_MARKERS.items():
        legend_elements.append(
            plt.Line2D([0], [0], marker=marker, color='w', 
                      markerfacecolor='gray', markersize=10,
                      label=category)
        )
    
    # 범례 표시
    ax.legend(handles=legend_elements, 
             loc='upper right', 
             fontsize=10,
             framealpha=0.9,
             edgecolor='black')
    
    # 축 비율 맞추기
    ax.set_aspect('equal', adjustable='box')
    
    plt.tight_layout()
    
    return fig


def visualize_user_cluster(user_id, cluster_dir, output_dir, place_file, axis_bounds):
    """특정 유저의 클러스터 시각화 (PNG)"""
    
    # 클러스터 JSON 파일 로드
    cluster_file = os.path.join(cluster_dir, f"{user_id}_daily_clusters.json")
    
    if not os.path.exists(cluster_file):
        print(f"❌ {user_id} 클러스터 파일 없음: {cluster_file}")
        return
    
    with open(cluster_file, 'r', encoding='utf-8') as f:
        cluster_data = json.load(f)
    
    print(f"\n📊 {user_id} 클러스터 시각화 중...")
    
    # travel_style이 있으면 표시, 없으면 생략
    if 'travel_style' in cluster_data:
        print(f"   여행 스타일: {cluster_data['travel_style']}")
    
    if 'start_date' in cluster_data:
        print(f"   시작 날짜: {cluster_data['start_date']} ({cluster_data.get('start_weekday', '')}요일)")
    
    print(f"   클러스터 수: {cluster_data['num_clusters']}개")
    
    # 장소 위치 정보 로드 (숙소 정보 확인 전에 먼저 로드!)
    place_locations = load_place_locations(place_file)
    
    # 숙소 정보 디버깅
    accommodation_id = cluster_data.get('Accommodation')
    print(f"   숙소 ID: {accommodation_id}")
    if accommodation_id:
        if accommodation_id in place_locations:
            acc_name = place_locations[accommodation_id]['name']
            print(f"   숙소 이름: {acc_name}")
            print(f"   ✅ 숙소 시각화 준비 완료")
        else:
            print(f"   ⚠️ 숙소 ID가 place_locations에 없음!")
    else:
        print(f"   ⚠️ JSON에 숙소 정보 없음!")
    
    # 플롯 생성
    fig = create_user_cluster_plot(cluster_data, place_locations, axis_bounds)
    
    # PNG 파일로 저장
    os.makedirs(output_dir, exist_ok=True)
    png_file = os.path.join(output_dir, f"{user_id}_clusters.png")
    fig.savefig(png_file, dpi=300, bbox_inches='tight')
    plt.close(fig)
    
    print(f"✅ PNG 저장 완료: {png_file}")


def visualize_all_users(cluster_dir, output_dir, place_file):
    """모든 유저의 클러스터 시각화 (PNG)"""
    
    cluster_files = [f for f in os.listdir(cluster_dir) if f.endswith('_daily_clusters.json')]
    
    if len(cluster_files) == 0:
        print("❌ 클러스터 파일이 없습니다.")
        return
    
    # 전체 위경도 범위 계산 (고정 축 범위용)
    if all(FIXED_AXIS[key] is None for key in FIXED_AXIS):
        print("\n🔍 전체 장소 데이터에서 축 범위 자동 계산 중...")
        axis_bounds = calculate_global_bounds(place_file, margin=0.02)
    else:
        # 수동 설정된 범위 사용
        axis_bounds = FIXED_AXIS
        print(f"\n📍 수동 설정된 축 범위 사용:")
        print(f"   위도: {axis_bounds['lat_min']} ~ {axis_bounds['lat_max']}")
        print(f"   경도: {axis_bounds['lng_min']} ~ {axis_bounds['lng_max']}")
    
    print(f"\n📊 총 {len(cluster_files)}명의 유저 클러스터 시각화 시작...")
    
    for idx, filename in enumerate(cluster_files, 1):
        user_id = filename.replace('_daily_clusters.json', '')
        print(f"\n[{idx}/{len(cluster_files)}] {user_id} 처리 중...")
        
        visualize_user_cluster(user_id, cluster_dir, output_dir, place_file, axis_bounds)
    
    print(f"\n✨ 전체 시각화 완료! 총 {len(cluster_files)}개 PNG 파일 생성")
    print(f"📁 저장 위치: {output_dir}")


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    # 옵션 1: 특정 유저 시각화
    # axis_bounds = calculate_global_bounds(CONFIG['PLACE_FILE'], margin=0.02)
    # visualize_user_cluster(
    #     user_id='U0001',
    #     cluster_dir=CONFIG['CLUSTER_DIR'],
    #     output_dir=CONFIG['OUTPUT_DIR'],
    #     place_file=CONFIG['PLACE_FILE'],
    #     axis_bounds=axis_bounds
    # )
    
    # 옵션 2: 전체 유저 시각화 (고정 축 범위 자동 계산)
    visualize_all_users(
        cluster_dir=CONFIG['CLUSTER_DIR'],
        output_dir=CONFIG['OUTPUT_DIR'],
        place_file=CONFIG['PLACE_FILE']
    )