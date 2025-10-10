import json
import os
import pandas as pd
import numpy as np

def analyze_cluster_41(hotzone_file, personalized_dir):
    """
    클러스터 41이 왜 많이 1등으로 나오는지 분석
    """
    # 1. 클러스터 41의 기본 정보 확인
    with open(hotzone_file, 'r', encoding='utf-8') as f:
        hotzone_data = json.load(f)
    
    cluster_41 = None
    for hotzone in hotzone_data['hotzones']:
        if hotzone['cluster_id'] == 41:
            cluster_41 = hotzone
            break
    
    if cluster_41 is None:
        print("❌ 클러스터 41을 찾을 수 없습니다!")
        return
    
    print("="*70)
    print("📍 클러스터 41 기본 정보")
    print("="*70)
    print(f"위치: ({cluster_41['center_lat']}, {cluster_41['center_lng']})")
    print(f"원본 크기: {cluster_41['original_cluster_size']}개")
    print(f"총 장소 수: {cluster_41['total_places']}개")
    print(f"카테고리 다양성: {cluster_41['category_diversity']}/4")
    
    print(f"\n카테고리별 장소 수:")
    for cat, places in cluster_41['categories'].items():
        print(f"  {cat}: {len(places)}개")
    
    # 2. 클러스터 41이 1등인 유저들의 점수 분석
    print("\n" + "="*70)
    print("📊 클러스터 41이 1등인 유저들 분석")
    print("="*70)
    
    cluster_41_users = []
    
    json_files = [f for f in os.listdir(personalized_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        file_path = os.path.join(personalized_dir, json_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if len(data['hotzones']) > 0 and data['hotzones'][0]['cluster_id'] == 41:
            user_id = data['user_id']
            travel_style = data['travel_style']
            top_cluster = data['hotzones'][0]
            
            cluster_41_users.append({
                'user_id': user_id,
                'travel_style': travel_style,
                'cluster_score': top_cluster['cluster_user_score'],
                'category_avg_scores': top_cluster.get('category_avg_scores', {}),
                'weighted_scores': top_cluster.get('weighted_category_scores', {})
            })
    
    print(f"클러스터 41이 1등인 유저: {len(cluster_41_users)}명")
    
    if len(cluster_41_users) > 0:
        df = pd.DataFrame(cluster_41_users)
        
        print(f"\n여행 스타일 분포:")
        style_counts = df['travel_style'].value_counts()
        for style, count in style_counts.items():
            print(f"  {style}: {count}명")
        
        print(f"\n평균 cluster_user_score: {df['cluster_score'].mean():.4f}")
        print(f"최대: {df['cluster_score'].max():.4f}, 최소: {df['cluster_score'].min():.4f}")
        
        # 카테고리별 평균 점수
        print(f"\n카테고리별 평균 점수:")
        all_cats = ['Accommodation', 'Cafe', 'Restaurant', 'Attraction']
        for cat in all_cats:
            scores = [u['category_avg_scores'].get(cat, 0) for u in cluster_41_users]
            avg_score = np.mean(scores)
            print(f"  {cat}: {avg_score:.4f}")
    
    # 3. 다른 상위 클러스터와 비교
    print("\n" + "="*70)
    print("🔍 상위 5개 클러스터 비교")
    print("="*70)
    
    cluster_scores = {}
    
    for json_file in json_files[:10]:  # 샘플로 10명만
        file_path = os.path.join(personalized_dir, json_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for hotzone in data['hotzones'][:5]:  # 상위 5개만
            cid = hotzone['cluster_id']
            score = hotzone['cluster_user_score']
            
            if cid not in cluster_scores:
                cluster_scores[cid] = []
            cluster_scores[cid].append(score)
    
    print(f"클러스터별 평균 점수 (샘플 10명 기준):")
    for cid in sorted(cluster_scores.keys(), key=lambda x: np.mean(cluster_scores[x]), reverse=True)[:10]:
        avg = np.mean(cluster_scores[cid])
        count = len(cluster_scores[cid])
        print(f"  클러스터 {cid}: 평균 {avg:.4f} (출현 {count}회)")
    
    # 4. 클러스터 41의 장소 이름 샘플 출력
    print("\n" + "="*70)
    print("📝 클러스터 41의 장소 샘플 (각 카테고리 5개씩)")
    print("="*70)
    
    for cat, places in cluster_41['categories'].items():
        print(f"\n{cat}:")
        for place in places[:5]:
            print(f"  - {place['name']} (ID: {place['id']})")


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    base_dir = r"C:\Users\changjin\workspace\lab\pln"
    hotzone_file = os.path.join(base_dir, "clustering", "greedy_hotzones_merged.json")
    personalized_dir = os.path.join(base_dir, "clustering", "personalized_hotzones")
    
    analyze_cluster_41(hotzone_file, personalized_dir)