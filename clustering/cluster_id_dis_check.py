import json
import os
from collections import Counter
import pandas as pd

def analyze_top_cluster_distribution(personalized_dir):
    """
    각 유저의 1등 클러스터 분포 분석
    """
    top_cluster_ids = []
    user_cluster_data = []
    
    # 모든 JSON 파일 읽기
    json_files = [f for f in os.listdir(personalized_dir) if f.endswith('.json')]
    
    print(f"📂 총 {len(json_files)}개 파일 분석 중...\n")
    
    for json_file in sorted(json_files):
        file_path = os.path.join(personalized_dir, json_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_id = data['user_id']
        travel_style = data['travel_style']
        
        # hotzones의 첫 번째(1등) 클러스터
        if len(data['hotzones']) > 0:
            top_cluster = data['hotzones'][0]
            cluster_id = top_cluster['cluster_id']
            cluster_score = top_cluster['cluster_user_score']
            
            top_cluster_ids.append(cluster_id)
            user_cluster_data.append({
                'user_id': user_id,
                'travel_style': travel_style,
                'top_cluster_id': cluster_id,
                'cluster_score': cluster_score
            })
    
    # 분포 계산
    cluster_counter = Counter(top_cluster_ids)
    
    print("="*70)
    print("📊 1등 클러스터 분포 (전체)")
    print("="*70)
    
    for cluster_id, count in cluster_counter.most_common():
        percentage = (count / len(json_files)) * 100
        print(f"클러스터 {cluster_id}: {count}명 ({percentage:.1f}%)")
    
    # 여행 스타일별 분포
    print("\n" + "="*70)
    print("🎨 여행 스타일별 1등 클러스터 분포")
    print("="*70)
    
    df = pd.DataFrame(user_cluster_data)
    
    for style in df['travel_style'].unique():
        print(f"\n🏷️ {style}:")
        style_df = df[df['travel_style'] == style]
        style_counter = Counter(style_df['top_cluster_id'])
        
        for cluster_id, count in style_counter.most_common(5):  # 상위 5개만
            percentage = (count / len(style_df)) * 100
            print(f"  클러스터 {cluster_id}: {count}명 ({percentage:.1f}%)")
    
    # 통계 요약
    print("\n" + "="*70)
    print("📈 통계 요약")
    print("="*70)
    print(f"총 유저 수: {len(json_files)}명")
    print(f"유니크 1등 클러스터 수: {len(cluster_counter)}개")
    print(f"가장 인기있는 클러스터: {cluster_counter.most_common(1)[0][0]}번 ({cluster_counter.most_common(1)[0][1]}명)")
    
    # 상세 테이블 저장
    output_csv = os.path.join(personalized_dir, "top_cluster_distribution.csv")
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n💾 상세 데이터 저장: {output_csv}")
    
    return df, cluster_counter


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    base_dir = r"C:\Users\changjin\workspace\lab\pln"
    personalized_dir = os.path.join(base_dir, "clustering", "personalized_hotzones")
    
    df, distribution = analyze_top_cluster_distribution(personalized_dir)