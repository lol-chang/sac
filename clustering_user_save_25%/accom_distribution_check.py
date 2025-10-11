import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import numpy as np

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# ========================================
# 설정
# ========================================
CONFIG = {
    "CLUSTER_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\user_based_clusters_greedy",
    "PLACE_FILE": r"C:\Users\changjin\workspace\lab\pln\data_set\last_clustering_category_combine_with_hours_and_price.csv",
    "OUTPUT_DIR": r"C:\Users\changjin\workspace\lab\pln\clustering_user\accommodation_analysis"
}


def load_place_info(place_file):
    """장소 정보 로드 (이름 매칭용)"""
    df = pd.read_csv(place_file)
    place_dict = {}
    
    for _, row in df.iterrows():
        place_dict[row['id']] = {
            'name': row['name'],
            'category': row['category'],
            'latitude': row['latitude'],
            'longitude': row['longitude']
        }
    
    return place_dict


def analyze_accommodations(cluster_dir, place_dict):
    """
    모든 유저의 숙소 선택 분석
    Returns:
        accommodation_stats: 숙소별 통계 DataFrame
        user_accommodation_map: 유저별 숙소 매핑 리스트
    """
    accommodation_list = []
    no_accommodation_users = []
    
    # 모든 JSON 파일 읽기
    json_files = [f for f in os.listdir(cluster_dir) if f.endswith('.json')]
    
    print(f"📂 분석 중: {len(json_files)}개 파일")
    
    for json_file in json_files:
        file_path = os.path.join(cluster_dir, json_file)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        user_id = data['user_id']
        accommodation_id = data.get('Accommodation')
        duration_days = data['duration_days']
        budget = data['budget']
        start_date = data['start_date']
        
        if accommodation_id is None:
            no_accommodation_users.append(user_id)
        else:
            accommodation_name = place_dict.get(accommodation_id, {}).get('name', f'Unknown_{accommodation_id}')
            
            accommodation_list.append({
                'user_id': user_id,
                'accommodation_id': accommodation_id,
                'accommodation_name': accommodation_name,
                'duration_days': duration_days,
                'budget': budget,
                'start_date': start_date
            })
    
    # DataFrame 생성
    df = pd.DataFrame(accommodation_list)
    
    # 숙소별 통계
    if len(df) > 0:
        accommodation_stats = df.groupby(['accommodation_id', 'accommodation_name']).agg({
            'user_id': 'count',
            'duration_days': 'mean',
            'budget': 'mean'
        }).rename(columns={'user_id': 'count'}).reset_index()
        
        accommodation_stats = accommodation_stats.sort_values('count', ascending=False)
    else:
        accommodation_stats = pd.DataFrame()
    
    print(f"\n✅ 분석 완료!")
    print(f"   - 총 유저 수: {len(json_files)}명")
    print(f"   - 숙소 선택: {len(df)}명")
    print(f"   - 숙소 미선택: {len(no_accommodation_users)}명 (1일 여행 등)")
    print(f"   - 고유 숙소 수: {df['accommodation_id'].nunique() if len(df) > 0 else 0}개")
    
    return accommodation_stats, df, no_accommodation_users


def visualize_top_accommodations(accommodation_stats, top_n=20):
    """상위 N개 숙소 막대 그래프"""
    if len(accommodation_stats) == 0:
        print("⚠️ 시각화할 데이터가 없습니다.")
        return None
    
    top_data = accommodation_stats.head(top_n)
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    bars = ax.barh(range(len(top_data)), top_data['count'], color='skyblue', edgecolor='navy')
    
    # 막대 위에 숫자 표시
    for i, (count, name) in enumerate(zip(top_data['count'], top_data['accommodation_name'])):
        ax.text(count + 0.5, i, f'{int(count)}명', va='center', fontsize=9)
    
    ax.set_yticks(range(len(top_data)))
    ax.set_yticklabels(top_data['accommodation_name'], fontsize=10)
    ax.set_xlabel('선택한 유저 수 (명)', fontsize=12, fontweight='bold')
    ax.set_title(f'상위 {top_n}개 인기 숙소', fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    return fig


def visualize_accommodation_distribution(accommodation_stats):
    """숙소 선택 빈도 분포"""
    if len(accommodation_stats) == 0:
        print("⚠️ 시각화할 데이터가 없습니다.")
        return None
    
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # 1) 선택 빈도 히스토그램
    ax1 = axes[0]
    ax1.hist(accommodation_stats['count'], bins=20, color='coral', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('선택 빈도 (명)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('숙소 수', fontsize=11, fontweight='bold')
    ax1.set_title('숙소별 선택 빈도 분포', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    
    # 통계 정보 추가
    mean_count = accommodation_stats['count'].mean()
    median_count = accommodation_stats['count'].median()
    ax1.axvline(mean_count, color='red', linestyle='--', linewidth=2, label=f'평균: {mean_count:.1f}')
    ax1.axvline(median_count, color='blue', linestyle='--', linewidth=2, label=f'중앙값: {median_count:.1f}')
    ax1.legend()
    
    # 2) 누적 분포
    ax2 = axes[1]
    sorted_counts = accommodation_stats['count'].sort_values(ascending=False).reset_index(drop=True)
    cumsum = sorted_counts.cumsum()
    cumsum_pct = (cumsum / cumsum.iloc[-1]) * 100
    
    ax2.plot(range(1, len(cumsum_pct) + 1), cumsum_pct, marker='o', linewidth=2, markersize=4, color='green')
    ax2.set_xlabel('숙소 순위', fontsize=11, fontweight='bold')
    ax2.set_ylabel('누적 비율 (%)', fontsize=11, fontweight='bold')
    ax2.set_title('숙소 선택 누적 분포', fontsize=13, fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # 상위 20% 숙소가 몇 %의 유저를 커버하는지
    top20_idx = int(len(cumsum_pct) * 0.2)
    if top20_idx > 0:
        top20_coverage = cumsum_pct.iloc[top20_idx - 1]
        ax2.axhline(top20_coverage, color='red', linestyle='--', linewidth=1.5, 
                   label=f'상위 20% 숙소 → {top20_coverage:.1f}% 유저')
        ax2.axvline(top20_idx, color='red', linestyle='--', linewidth=1.5)
        ax2.legend()
    
    plt.tight_layout()
    
    return fig


def visualize_budget_vs_accommodation(df, accommodation_stats, top_n=15):
    """예산별 숙소 선택 패턴"""
    if len(df) == 0:
        print("⚠️ 시각화할 데이터가 없습니다.")
        return None
    
    # 상위 숙소만 필터링
    top_accommodations = accommodation_stats.head(top_n)['accommodation_id'].tolist()
    df_filtered = df[df['accommodation_id'].isin(top_accommodations)].copy()
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # 박스플롯
    accommodation_names = [accommodation_stats[accommodation_stats['accommodation_id'] == aid]['accommodation_name'].values[0] 
                          for aid in top_accommodations]
    
    data_for_plot = []
    labels_for_plot = []
    
    for aid, name in zip(top_accommodations, accommodation_names):
        budgets = df_filtered[df_filtered['accommodation_id'] == aid]['budget'].values
        if len(budgets) > 0:
            data_for_plot.append(budgets)
            labels_for_plot.append(f"{name}\n(n={len(budgets)})")
    
    bp = ax.boxplot(data_for_plot, labels=labels_for_plot, patch_artist=True, vert=False)
    
    # 색상 설정
    for patch in bp['boxes']:
        patch.set_facecolor('lightblue')
        patch.set_alpha(0.7)
    
    ax.set_xlabel('예산 (만원)', fontsize=12, fontweight='bold')
    ax.set_title(f'상위 {top_n}개 숙소별 유저 예산 분포', fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='x', alpha=0.3)
    
    # x축을 만원 단위로 표시
    ax.set_xticklabels([f'{int(x/10000)}' for x in ax.get_xticks()])
    
    plt.tight_layout()
    
    return fig


def print_statistics(accommodation_stats, df, no_accommodation_users):
    """통계 정보 출력"""
    print("\n" + "="*70)
    print("📊 숙소 선택 통계")
    print("="*70)
    
    if len(accommodation_stats) == 0:
        print("⚠️ 통계 데이터가 없습니다.")
        return
    
    total_users = len(df) + len(no_accommodation_users)
    
    print(f"\n📌 전체 현황")
    print(f"   - 전체 유저: {total_users}명")
    print(f"   - 숙소 선택: {len(df)}명 ({len(df)/total_users*100:.1f}%)")
    print(f"   - 숙소 미선택: {len(no_accommodation_users)}명 ({len(no_accommodation_users)/total_users*100:.1f}%)")
    
    print(f"\n🏨 숙소 통계")
    print(f"   - 고유 숙소 수: {len(accommodation_stats)}개")
    print(f"   - 평균 선택 빈도: {accommodation_stats['count'].mean():.2f}명/숙소")
    print(f"   - 중앙값 선택 빈도: {accommodation_stats['count'].median():.0f}명/숙소")
    print(f"   - 최다 선택 숙소: {accommodation_stats.iloc[0]['accommodation_name']} ({int(accommodation_stats.iloc[0]['count'])}명)")
    
    print(f"\n🔝 상위 10개 인기 숙소")
    for i, row in accommodation_stats.head(10).iterrows():
        print(f"   {i+1:2d}. {row['accommodation_name']:<30s} - {int(row['count']):3d}명 "
              f"(평균 예산: {row['budget']/10000:.1f}만원, 평균 일수: {row['duration_days']:.1f}일)")
    
    # 선택 빈도 1회인 숙소
    single_choice = accommodation_stats[accommodation_stats['count'] == 1]
    print(f"\n📍 1명만 선택한 숙소: {len(single_choice)}개 ({len(single_choice)/len(accommodation_stats)*100:.1f}%)")
    
    # 예산 구간별 통계
    print(f"\n💰 예산 구간별 숙소 선택")
    df['budget_range'] = pd.cut(df['budget'], bins=[0, 200000, 400000, 600000, 1000000], 
                                 labels=['20만원 이하', '20-40만원', '40-60만원', '60만원 이상'])
    budget_summary = df['budget_range'].value_counts().sort_index()
    for budget_range, count in budget_summary.items():
        print(f"   - {budget_range}: {count}명 ({count/len(df)*100:.1f}%)")


def main():
    """메인 실행 함수"""
    print("🚀 숙소 분포 분석 시작\n")
    
    # 출력 디렉토리 생성
    os.makedirs(CONFIG['OUTPUT_DIR'], exist_ok=True)
    
    # 장소 정보 로드
    print("📂 장소 정보 로드 중...")
    place_dict = load_place_info(CONFIG['PLACE_FILE'])
    print(f"✅ {len(place_dict)}개 장소 정보 로드 완료\n")
    
    # 숙소 분석
    accommodation_stats, df, no_accommodation_users = analyze_accommodations(
        CONFIG['CLUSTER_DIR'], 
        place_dict
    )
    
    # 통계 출력
    print_statistics(accommodation_stats, df, no_accommodation_users)
    
    # 시각화
    if len(accommodation_stats) > 0:
        print("\n📊 시각화 생성 중...")
        
        # 1) 상위 숙소 막대 그래프
        fig1 = visualize_top_accommodations(accommodation_stats, top_n=20)
        if fig1:
            fig1.savefig(os.path.join(CONFIG['OUTPUT_DIR'], 'top_accommodations.png'), 
                        dpi=300, bbox_inches='tight')
            print("   ✅ top_accommodations.png 저장 완료")
            plt.close(fig1)
        
        # 2) 분포 분석
        fig2 = visualize_accommodation_distribution(accommodation_stats)
        if fig2:
            fig2.savefig(os.path.join(CONFIG['OUTPUT_DIR'], 'accommodation_distribution.png'), 
                        dpi=300, bbox_inches='tight')
            print("   ✅ accommodation_distribution.png 저장 완료")
            plt.close(fig2)
        
        # 3) 예산별 분석
        fig3 = visualize_budget_vs_accommodation(df, accommodation_stats, top_n=15)
        if fig3:
            fig3.savefig(os.path.join(CONFIG['OUTPUT_DIR'], 'budget_vs_accommodation.png'), 
                        dpi=300, bbox_inches='tight')
            print("   ✅ budget_vs_accommodation.png 저장 완료")
            plt.close(fig3)
        
        # 4) 통계 CSV 저장
        accommodation_stats.to_csv(
            os.path.join(CONFIG['OUTPUT_DIR'], 'accommodation_statistics.csv'), 
            index=False, 
            encoding='utf-8-sig'
        )
        print("   ✅ accommodation_statistics.csv 저장 완료")
        
        # 5) 전체 데이터 CSV 저장
        df.to_csv(
            os.path.join(CONFIG['OUTPUT_DIR'], 'user_accommodation_mapping.csv'), 
            index=False, 
            encoding='utf-8-sig'
        )
        print("   ✅ user_accommodation_mapping.csv 저장 완료")
    
    print("\n" + "="*70)
    print(f"✨ 분석 완료! 결과는 '{CONFIG['OUTPUT_DIR']}'에 저장되었습니다.")
    print("="*70)


if __name__ == "__main__":
    main()