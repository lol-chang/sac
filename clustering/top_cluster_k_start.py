# # import json
# # import os
# # import numpy as np
# # import pandas as pd

# # def load_user_info(user_info_file):
# #     """유저 정보 파일 로드 (travel_style 가져오기)"""
# #     df = pd.read_csv(user_info_file)
# #     user_info_dict = {}
    
# #     for _, row in df.iterrows():
# #         user_info_dict[row['user_id']] = row['travel_style']
    
# #     return user_info_dict


# # def get_category_weights(travel_style):
# #     """
# #     여행 스타일에 따른 카테고리별 가중치 반환
# #     """
# #     weights = {
# #         'Healing': {
# #             'Accommodation': 1.5,  # 힐링 여행은 숙소가 중요
# #             'Cafe': 1.3,           # 카페에서 여유
# #             'Restaurant': 0.8,
# #             'Attraction': 0.7
# #         },
# #         'Foodie': {
# #             'Accommodation': 0.8,
# #             'Cafe': 1.1,
# #             'Restaurant': 1.8,     # 맛집 여행은 레스토랑이 최우선
# #             'Attraction': 0.7
# #         },
# #         'Activity': {
# #             'Accommodation': 0.7,
# #             'Cafe': 0.8,
# #             'Restaurant': 1.0,
# #             'Attraction': 1.8      # 액티비티 여행은 관광지 중심
# #         },
# #         'Cultural': {
# #             'Accommodation': 0.8,
# #             'Cafe': 1.2,
# #             'Restaurant': 1.0,
# #             'Attraction': 1.5      # 문화 여행은 관광지와 카페
# #         }
# #     }
    
# #     # 기본값 (travel_style이 없거나 매칭 안되면)
# #     default_weights = {
# #         'Accommodation': 1.0,
# #         'Cafe': 1.0,
# #         'Restaurant': 1.0,
# #         'Attraction': 1.0
# #     }
    
# #     return weights.get(travel_style, default_weights)


# # def load_user_preferences(user_file_path):
# #     """유저 선호도 파일 로드"""
# #     with open(user_file_path, 'r', encoding='utf-8') as f:
# #         preferences = json.load(f)
    
# #     # 모든 카테고리의 장소 선호도를 하나의 딕셔너리로 통합
# #     preference_dict = {}
# #     for category, places in preferences.items():
# #         for place in places:
# #             preference_dict[place['id']] = place['final_score']
    
# #     return preference_dict


# # def score_hotzones_with_user_preference(hotzone_file, user_pref_file, user_info_dict, output_file):
# #     """
# #     유저 선호도 기반으로 클러스터와 장소 점수 매기기 (travel_style 가중치 적용)
# #     """
# #     # 1. 파일 로드
# #     with open(hotzone_file, 'r', encoding='utf-8') as f:
# #         hotzone_data = json.load(f)
    
# #     user_preferences = load_user_preferences(user_pref_file)
    
# #     # 유저 ID 추출
# #     user_id = os.path.basename(user_pref_file).replace('_recommendations_softmax.json', '')
    
# #     # 유저의 travel_style 가져오기
# #     travel_style = user_info_dict.get(user_id, 'Healing')  # 기본값: Healing
# #     category_weights = get_category_weights(travel_style)
    
# #     print(f"✅ Hotzone 파일 로드: {len(hotzone_data['hotzones'])}개 클러스터")
# #     print(f"✅ 유저 선호도 로드: {len(user_preferences)}개 장소")
# #     print(f"👤 유저 ID: {user_id}")
# #     print(f"🎨 여행 스타일: {travel_style}")
# #     print(f"⚖️ 카테고리 가중치: Acc={category_weights['Accommodation']}, "
# #           f"Caf={category_weights['Cafe']}, "
# #           f"Res={category_weights['Restaurant']}, "
# #           f"Att={category_weights['Attraction']}")
    
# #     # 2. 각 클러스터의 카테고리별 점수 총합 계산
# #     all_categories = ['Accommodation', 'Cafe', 'Restaurant', 'Attraction']
# #     category_sums_per_cluster = {}
    
# #     for hotzone in hotzone_data['hotzones']:
# #         cluster_id = hotzone['cluster_id']
# #         category_sums = {}
        
# #         for category in all_categories:
# #             places = hotzone['categories'].get(category, [])
# #             total_score = 0.0
            
# #             for place in places:
# #                 place_id = place['id']
# #                 user_score = user_preferences.get(place_id, 0.0)
# #                 total_score += user_score
            
# #             category_sums[category] = total_score
        
# #         category_sums_per_cluster[cluster_id] = category_sums
    
# #     # 3. 카테고리별 최대/최소값 계산 (정규화를 위해)
# #     category_min_max = {}
# #     for category in all_categories:
# #         all_sums = [sums[category] for sums in category_sums_per_cluster.values()]
# #         category_min_max[category] = {
# #             'min': min(all_sums) if all_sums else 0.0,
# #             'max': max(all_sums) if all_sums else 1.0
# #         }
    
# #     print("\n📊 카테고리별 점수 총합 범위:")
# #     for category, minmax in category_min_max.items():
# #         print(f"  {category}: {minmax['min']:.4f} ~ {minmax['max']:.4f}")
    
# #     # 4. 각 클러스터 점수 계산 및 장소에 점수 매칭
# #     scored_hotzones = []
    
# #     for hotzone in hotzone_data['hotzones']:
# #         cluster_id = hotzone['cluster_id']
# #         normalized_category_scores = []
        
# #         # 카테고리별 정규화된 점수 계산
# #         for category in all_categories:
# #             places = hotzone['categories'].get(category, [])
# #             scored_places = []
            
# #             cat_sum = category_sums_per_cluster[cluster_id][category]
# #             cat_min = category_min_max[category]['min']
# #             cat_max = category_min_max[category]['max']
# #             cat_range = cat_max - cat_min
            
# #             # 카테고리 총합 정규화
# #             if cat_range > 0:
# #                 normalized_cat_score = (cat_sum - cat_min) / cat_range
# #             else:
# #                 normalized_cat_score = 0.0
            
# #             normalized_category_scores.append(normalized_cat_score)
            
# #             # 각 장소에 점수 매칭
# #             for place in places:
# #                 place_id = place['id']
# #                 user_score = user_preferences.get(place_id, 0.0)
                
# #                 scored_place = place.copy()
# #                 scored_place['user_preference_score'] = round(user_score, 4)
# #                 scored_places.append(scored_place)
            
# #             # 카테고리 내 장소를 유저 선호도 점수 순으로 정렬
# #             scored_places.sort(key=lambda x: x['user_preference_score'], reverse=True)
# #             hotzone['categories'][category] = scored_places
        
# #         # cluster_user_score = 정규화된 카테고리 점수들에 가중치 적용 후 합
# #         weighted_scores = [
# #             normalized_category_scores[i] * category_weights[all_categories[i]]
# #             for i in range(len(all_categories))
# #         ]
# #         cluster_user_score = sum(weighted_scores)
        
# #         hotzone['cluster_user_score'] = round(cluster_user_score, 4)
# #         hotzone['category_scores'] = {
# #             category: round(score, 4) 
# #             for category, score in zip(all_categories, normalized_category_scores)
# #         }
# #         hotzone['weighted_category_scores'] = {
# #             category: round(weighted_scores[i], 4)
# #             for i, category in enumerate(all_categories)
# #         }
# #         hotzone['travel_style'] = travel_style
        
# #         scored_hotzones.append(hotzone)
        
# #         print(f"  C{cluster_id}: cluster_user_score {cluster_user_score:.4f} "
# #               f"| 정규화: (Acc:{normalized_category_scores[0]:.2f}, "
# #               f"Caf:{normalized_category_scores[1]:.2f}, "
# #               f"Res:{normalized_category_scores[2]:.2f}, "
# #               f"Att:{normalized_category_scores[3]:.2f}) "
# #               f"| 가중치 적용: (Acc:{weighted_scores[0]:.2f}, "
# #               f"Caf:{weighted_scores[1]:.2f}, "
# #               f"Res:{weighted_scores[2]:.2f}, "
# #               f"Att:{weighted_scores[3]:.2f})")
    
# #     # 5. 클러스터를 cluster_user_score 순으로 정렬
# #     scored_hotzones.sort(key=lambda x: x['cluster_user_score'], reverse=True)
    
# #     # 6. 새로운 JSON 저장
# #     result = {
# #         "user_id": user_id,
# #         "travel_style": travel_style,
# #         "category_weights": category_weights,
# #         "hotzones": scored_hotzones
# #     }
    
# #     with open(output_file, 'w', encoding='utf-8') as f:
# #         json.dump(result, f, ensure_ascii=False, indent=2)
    
# #     print(f"\n💾 저장 완료: {output_file}")
# #     print(f"📊 클러스터 정렬: cluster_user_score 순으로 정렬됨")
# #     print(f"📊 각 클러스터 내 장소: 유저 선호도 순으로 정렬됨")
    
# #     # 7. 통계 출력
# #     print("\n" + "="*70)
# #     print("📈 클러스터별 cluster_user_score 랭킹 (상위 10개)")
# #     print("="*70)
# #     for idx, hotzone in enumerate(scored_hotzones[:10], 1):
# #         print(f"{idx}. 클러스터 {hotzone['cluster_id']}: "
# #               f"점수 {hotzone['cluster_user_score']:.4f}")
    
# #     return result


# # def process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir):
# #     """
# #     모든 유저에 대해 일괄 처리
# #     """
# #     os.makedirs(output_dir, exist_ok=True)
    
# #     # 유저 정보 로드
# #     print("📂 유저 정보 파일 로드 중...")
# #     user_info_dict = load_user_info(user_info_file)
# #     print(f"✅ {len(user_info_dict)}명의 유저 정보 로드 완료")
    
# #     # user_pref_dir에서 모든 유저 파일 찾기
# #     user_files = [f for f in os.listdir(user_pref_dir) if f.endswith('_recommendations_softmax.json')]
    
# #     print(f"\n🚀 총 {len(user_files)}명의 유저 처리 시작...\n")
    
# #     for user_file in sorted(user_files):
# #         user_id = user_file.replace('_recommendations_softmax.json', '')
# #         user_pref_path = os.path.join(user_pref_dir, user_file)
# #         output_path = os.path.join(output_dir, f"{user_id}_personalized_hotzones.json")
        
# #         print(f"\n{'='*70}")
# #         print(f"👤 {user_id} 처리 중...")
# #         print(f"{'='*70}")
        
# #         score_hotzones_with_user_preference(hotzone_file, user_pref_path, user_info_dict, output_path)
    
# #     print(f"\n✨ 모든 유저 처리 완료! 총 {len(user_files)}개 파일 생성")


# # # ========================================
# # # 🚀 실행
# # # ========================================
# # if __name__ == "__main__":
# #     base_dir = r"C:\Users\changjin\workspace\lab\pln"
    
# #     # 파일 경로 설정
# #     hotzone_file = os.path.join(base_dir, "clustering", "greedy_hotzones_merged.json")
# #     user_pref_dir = os.path.join(base_dir, "vector_embedding", "review_count_with_softmax", "for_clustering_user")
# #     user_info_file = os.path.join(base_dir, "data_set", "1000_user_info.csv")
# #     output_dir = os.path.join(base_dir, "clustering", "personalized_hotzones")
    
# #     # 옵션 1: 특정 유저 한 명만 처리
# #     # user_info_dict = load_user_info(user_info_file)
# #     # user_file = os.path.join(user_pref_dir, "U0001_recommendations_softmax.json")
# #     # output_file = os.path.join(output_dir, "U0001_personalized_hotzones.json")
# #     # os.makedirs(output_dir, exist_ok=True)
# #     # score_hotzones_with_user_preference(hotzone_file, user_file, user_info_dict, output_file)
    
# #     # 옵션 2: 모든 유저 일괄 처리
# #     process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir)
# import json
# import os
# import numpy as np
# import pandas as pd

# def load_user_info(user_info_file):
#     """유저 정보 파일 로드 (travel_style 가져오기)"""
#     df = pd.read_csv(user_info_file)
#     user_info_dict = {}
    
#     for _, row in df.iterrows():
#         user_info_dict[row['user_id']] = row['travel_style']
    
#     return user_info_dict


# def get_category_weights(travel_style):
#     """
#     여행 스타일에 따른 카테고리별 가중치 반환
#     """
#     weights = {
#         'Healing': {
#             'Accommodation': 3.0,  # 힐링 여행은 숙소가 중요
#             'Cafe': 3.0,           # 카페에서 여유
#             'Restaurant': 0.4,
#             'Attraction': 0.4
#         },
#         'Foodie': {
#             'Accommodation': 0.4,
#             'Cafe': 1.3,
#             'Restaurant': 3.0,     # 맛집 여행은 레스토랑이 최우선
#             'Attraction': 0.4
#         },
#         'Activity': {
#             'Accommodation': 2,
#             'Cafe': 0.5,
#             'Restaurant': 0.4,
#             'Attraction': 3.5      # 액티비티 여행은 관광지 중심
#         },
#         'Cultural': {
#             'Accommodation': 1.2,
#             'Cafe': 0.8,
#             'Restaurant': 1,
#             'Attraction': 2     # 문화 여행은 관광지와 카페
#         }
#     }
    
#     # 기본값 (travel_style이 없거나 매칭 안되면)
#     default_weights = {
#         'Accommodation': 1.0,
#         'Cafe': 1.0,
#         'Restaurant': 1.0,
#         'Attraction': 1.0
#     }
    
#     return weights.get(travel_style, default_weights)


# def load_user_preferences(user_file_path):
#     """유저 선호도 파일 로드"""
#     with open(user_file_path, 'r', encoding='utf-8') as f:
#         preferences = json.load(f)
    
#     # 모든 카테고리의 장소 선호도를 하나의 딕셔너리로 통합
#     preference_dict = {}
#     for category, places in preferences.items():
#         for place in places:
#             preference_dict[place['id']] = place['final_score']
    
#     return preference_dict


# def score_hotzones_with_user_preference(hotzone_file, user_pref_file, user_info_dict, output_file):
#     """
#     유저 선호도 기반으로 클러스터와 장소 점수 매기기 (travel_style 가중치 적용)
#     """
#     # 1. 파일 로드
#     with open(hotzone_file, 'r', encoding='utf-8') as f:
#         hotzone_data = json.load(f)
    
#     user_preferences = load_user_preferences(user_pref_file)
    
#     # 유저 ID 추출
#     user_id = os.path.basename(user_pref_file).replace('_recommendations_softmax.json', '')
    
#     # 유저의 travel_style 가져오기
#     travel_style = user_info_dict.get(user_id, 'Healing')  # 기본값: Healing
#     category_weights = get_category_weights(travel_style)
    
#     print(f"✅ Hotzone 파일 로드: {len(hotzone_data['hotzones'])}개 클러스터")
#     print(f"✅ 유저 선호도 로드: {len(user_preferences)}개 장소")
#     print(f"👤 유저 ID: {user_id}")
#     print(f"🎨 여행 스타일: {travel_style}")
#     print(f"⚖️ 카테고리 가중치: Acc={category_weights['Accommodation']}, "
#           f"Caf={category_weights['Cafe']}, "
#           f"Res={category_weights['Restaurant']}, "
#           f"Att={category_weights['Attraction']}")
    
#     # 2. 각 클러스터의 카테고리별 평균 점수 계산 및 가중치 적용
#     all_categories = ['Accommodation', 'Cafe', 'Restaurant', 'Attraction']
#     scored_hotzones = []
    
#     for hotzone in hotzone_data['hotzones']:
#         cluster_id = hotzone['cluster_id']
#         category_avg_scores = []
#         weighted_scores = []
        
#         # 카테고리별 평균 점수 계산
#         for category in all_categories:
#             places = hotzone['categories'].get(category, [])
#             scored_places = []
            
#             # 각 장소에 점수 매칭
#             scores = []
#             for place in places:
#                 place_id = place['id']
#                 user_score = user_preferences.get(place_id, 0.0)
                
#                 scored_place = place.copy()
#                 scored_place['final_score'] = round(user_score, 4)
#                 scored_places.append(scored_place)
                
#                 if user_score > 0:
#                     scores.append(user_score)
            
#             # 카테고리 내 장소를 final_score 순으로 정렬
#             scored_places.sort(key=lambda x: x['final_score'], reverse=True)
#             hotzone['categories'][category] = scored_places
            
#             # 평균 점수 계산
#             avg_score = np.mean(scores) if len(scores) > 0 else 0.0
#             category_avg_scores.append(avg_score)
            
#             # 가중치 적용
#             weight = category_weights[category]
#             weighted_score = avg_score * weight
#             weighted_scores.append(weighted_score)
        
#         # cluster_user_score = 가중치 적용된 평균 점수들의 합
#         cluster_user_score = sum(weighted_scores)
        
#         hotzone['cluster_user_score'] = round(cluster_user_score, 4)
#         hotzone['category_avg_scores'] = {
#             category: round(score, 4) 
#             for category, score in zip(all_categories, category_avg_scores)
#         }
#         hotzone['weighted_category_scores'] = {
#             category: round(weighted_scores[i], 4)
#             for i, category in enumerate(all_categories)
#         }
#         hotzone['travel_style'] = travel_style
        
#         scored_hotzones.append(hotzone)
        
#         print(f"  C{cluster_id}: cluster_user_score {cluster_user_score:.4f} "
#               f"| 평균: (Acc:{category_avg_scores[0]:.2f}, "
#               f"Caf:{category_avg_scores[1]:.2f}, "
#               f"Res:{category_avg_scores[2]:.2f}, "
#               f"Att:{category_avg_scores[3]:.2f}) "
#               f"| 가중치 적용: (Acc:{weighted_scores[0]:.2f}, "
#               f"Caf:{weighted_scores[1]:.2f}, "
#               f"Res:{weighted_scores[2]:.2f}, "
#               f"Att:{weighted_scores[3]:.2f})")
    
#     # 5. 클러스터를 cluster_user_score 순으로 정렬
#     scored_hotzones.sort(key=lambda x: x['cluster_user_score'], reverse=True)
    
#     # 6. 새로운 JSON 저장
#     result = {
#         "user_id": user_id,
#         "travel_style": travel_style,
#         "category_weights": category_weights,
#         "hotzones": scored_hotzones
#     }
    
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump(result, f, ensure_ascii=False, indent=2)
    
#     print(f"\n💾 저장 완료: {output_file}")
#     print(f"📊 클러스터 정렬: cluster_user_score 순으로 정렬됨")
#     print(f"📊 각 클러스터 내 장소: final_score 순으로 정렬됨")
    
#     # 7. 통계 출력
#     print("\n" + "="*70)
#     print("📈 클러스터별 cluster_user_score 랭킹 (상위 10개)")
#     print("="*70)
#     for idx, hotzone in enumerate(scored_hotzones[:10], 1):
#         print(f"{idx}. 클러스터 {hotzone['cluster_id']}: "
#               f"점수 {hotzone['cluster_user_score']:.4f}")
    
#     return result


# def process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir):
#     """
#     모든 유저에 대해 일괄 처리
#     """
#     os.makedirs(output_dir, exist_ok=True)
    
#     # 유저 정보 로드
#     print("📂 유저 정보 파일 로드 중...")
#     user_info_dict = load_user_info(user_info_file)
#     print(f"✅ {len(user_info_dict)}명의 유저 정보 로드 완료")
    
#     # user_pref_dir에서 모든 유저 파일 찾기
#     user_files = [f for f in os.listdir(user_pref_dir) if f.endswith('_recommendations_softmax.json')]
    
#     print(f"\n🚀 총 {len(user_files)}명의 유저 처리 시작...\n")
    
#     for user_file in sorted(user_files):
#         user_id = user_file.replace('_recommendations_softmax.json', '')
#         user_pref_path = os.path.join(user_pref_dir, user_file)
#         output_path = os.path.join(output_dir, f"{user_id}_personalized_hotzones.json")
        
#         print(f"\n{'='*70}")
#         print(f"👤 {user_id} 처리 중...")
#         print(f"{'='*70}")
        
#         score_hotzones_with_user_preference(hotzone_file, user_pref_path, user_info_dict, output_path)
    
#     print(f"\n✨ 모든 유저 처리 완료! 총 {len(user_files)}개 파일 생성")


# # ========================================
# # 🚀 실행
# # ========================================
# if __name__ == "__main__":
#     base_dir = r"C:\Users\changjin\workspace\lab\pln"
    
#     # 파일 경로 설정
#     hotzone_file = os.path.join(base_dir, "clustering", "greedy_hotzones_merged.json")
#     user_pref_dir = os.path.join(base_dir, "vector_embedding", "review_count_with_softmax", "for_clustering_user")
#     user_info_file = os.path.join(base_dir, "data_set", "1000_user_info.csv")
#     output_dir = os.path.join(base_dir, "clustering", "personalized_hotzones")
    
#     # 옵션 1: 특정 유저 한 명만 처리
#     # user_info_dict = load_user_info(user_info_file)
#     # user_file = os.path.join(user_pref_dir, "U0001_recommendations_softmax.json")
#     # output_file = os.path.join(output_dir, "U0001_personalized_hotzones.json")
#     # os.makedirs(output_dir, exist_ok=True)
#     # score_hotzones_with_user_preference(hotzone_file, user_file, user_info_dict, output_file)
    
#     # 옵션 2: 모든 유저 일괄 처리
#     process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir)

import json
import os
import numpy as np
import pandas as pd

def load_user_info(user_info_file):
    """유저 정보 파일 로드 (travel_style 가져오기)"""
    df = pd.read_csv(user_info_file)
    user_info_dict = {}
    
    for _, row in df.iterrows():
        user_info_dict[row['user_id']] = row['travel_style']
    
    return user_info_dict


def get_category_weights(travel_style):
    """
    여행 스타일에 따른 카테고리별 가중치 반환
    """
    weights = {
        'Healing': {
            'Accommodation': 1.5,  # 힐링 여행은 숙소가 중요
            'Cafe': 1.3,           # 카페에서 여유
            'Restaurant': 0.8,
            'Attraction': 0.7
        },
        'Foodie': {
            'Accommodation': 0.8,
            'Cafe': 1.1,
            'Restaurant': 1.8,     # 맛집 여행은 레스토랑이 최우선
            'Attraction': 0.7
        },
        'Activity': {
            'Accommodation': 0.7,
            'Cafe': 0.8,
            'Restaurant': 1.0,
            'Attraction': 1.8      # 액티비티 여행은 관광지 중심
        },
        'Cultural': {
            'Accommodation': 0.8,
            'Cafe': 1.2,
            'Restaurant': 1.0,
            'Attraction': 1.5      # 문화 여행은 관광지와 카페
        }
    }
    
    # 기본값 (travel_style이 없거나 매칭 안되면)
    default_weights = {
        'Accommodation': 1.0,
        'Cafe': 1.0,
        'Restaurant': 1.0,
        'Attraction': 1.0
    }
    
    return weights.get(travel_style, default_weights)


def load_user_preferences(user_file_path):
    """유저 선호도 파일 로드"""
    with open(user_file_path, 'r', encoding='utf-8') as f:
        preferences = json.load(f)
    
    # 모든 카테고리의 장소 선호도를 하나의 딕셔너리로 통합
    preference_dict = {}
    for category, places in preferences.items():
        for place in places:
            preference_dict[place['id']] = place['final_score']
    
    return preference_dict


def score_hotzones_with_user_preference(hotzone_file, user_pref_file, user_info_dict, output_file):
    """
    유저 선호도 기반으로 클러스터와 장소 점수 매기기 (travel_style 가중치 적용)
    """
    # 1. 파일 로드
    with open(hotzone_file, 'r', encoding='utf-8') as f:
        hotzone_data = json.load(f)
    
    user_preferences = load_user_preferences(user_pref_file)
    
    # 유저 ID 추출
    user_id = os.path.basename(user_pref_file).replace('_recommendations_softmax.json', '')
    
    # 유저의 travel_style 가져오기
    travel_style = user_info_dict.get(user_id, 'Healing')  # 기본값: Healing
    category_weights = get_category_weights(travel_style)
    
    print(f"✅ Hotzone 파일 로드: {len(hotzone_data['hotzones'])}개 클러스터")
    print(f"✅ 유저 선호도 로드: {len(user_preferences)}개 장소")
    print(f"👤 유저 ID: {user_id}")
    print(f"🎨 여행 스타일: {travel_style}")
    print(f"⚖️ 카테고리 가중치: Acc={category_weights['Accommodation']}, "
          f"Caf={category_weights['Cafe']}, "
          f"Res={category_weights['Restaurant']}, "
          f"Att={category_weights['Attraction']}")
    
    # 2. 각 클러스터의 카테고리별 평균 점수 계산 및 가중치 적용
    all_categories = ['Accommodation', 'Cafe', 'Restaurant', 'Attraction']
    scored_hotzones = []
    
    for hotzone in hotzone_data['hotzones']:
        cluster_id = hotzone['cluster_id']
        category_avg_scores = []
        weighted_scores = []
        
        # 카테고리별 평균 점수 계산
        for category in all_categories:
            places = hotzone['categories'].get(category, [])
            scored_places = []
            
            # 각 장소에 점수 매칭
            scores = []
            for place in places:
                place_id = place['id']
                user_score = user_preferences.get(place_id, 0.0)
                
                scored_place = place.copy()
                scored_place['final_score'] = round(user_score, 4)
                scored_places.append(scored_place)
                
                if user_score > 0:
                    scores.append(user_score)
            
            # 카테고리 내 장소를 final_score 순으로 정렬
            scored_places.sort(key=lambda x: x['final_score'], reverse=True)
            hotzone['categories'][category] = scored_places
            
            # 평균 점수 계산
            avg_score = np.mean(scores) if len(scores) > 0 else 0.0
            category_avg_scores.append(avg_score)
            
            # 가중치 적용
            weight = category_weights[category]
            weighted_score = avg_score * weight
            weighted_scores.append(weighted_score)
        
        # cluster_user_score = 가중치 적용된 평균 점수들의 합
        raw_score = sum(weighted_scores)
        
        # 원본 클러스터 크기 페널티 적용
        original_size = hotzone.get('original_cluster_size', 50)
        size_penalty = original_size / 50  # 50개 기준으로 정규화
        cluster_user_score = raw_score * size_penalty
        
        hotzone['cluster_user_score'] = round(cluster_user_score, 4)
        hotzone['raw_score'] = round(raw_score, 4)  # 페널티 전 점수도 저장
        hotzone['category_avg_scores'] = {
            category: round(score, 4) 
            for category, score in zip(all_categories, category_avg_scores)
        }
        hotzone['weighted_category_scores'] = {
            category: round(weighted_scores[i], 4)
            for i, category in enumerate(all_categories)
        }
        hotzone['travel_style'] = travel_style
        
        scored_hotzones.append(hotzone)
        
        print(f"  C{cluster_id}: cluster_user_score {cluster_user_score:.4f} "
              f"(원본:{original_size}개, 페널티:{size_penalty:.2f}) "
              f"| 평균: (Acc:{category_avg_scores[0]:.2f}, "
              f"Caf:{category_avg_scores[1]:.2f}, "
              f"Res:{category_avg_scores[2]:.2f}, "
              f"Att:{category_avg_scores[3]:.2f}) "
              f"| 가중치 적용: (Acc:{weighted_scores[0]:.2f}, "
              f"Caf:{weighted_scores[1]:.2f}, "
              f"Res:{weighted_scores[2]:.2f}, "
              f"Att:{weighted_scores[3]:.2f})")
    
    # 5. 클러스터를 cluster_user_score 순으로 정렬
    scored_hotzones.sort(key=lambda x: x['cluster_user_score'], reverse=True)
    
    # 6. 새로운 JSON 저장
    result = {
        "user_id": user_id,
        "travel_style": travel_style,
        "category_weights": category_weights,
        "hotzones": scored_hotzones
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 저장 완료: {output_file}")
    print(f"📊 클러스터 정렬: cluster_user_score 순으로 정렬됨")
    print(f"📊 각 클러스터 내 장소: final_score 순으로 정렬됨")
    
    # 7. 통계 출력
    print("\n" + "="*70)
    print("📈 클러스터별 cluster_user_score 랭킹 (상위 10개)")
    print("="*70)
    for idx, hotzone in enumerate(scored_hotzones[:10], 1):
        print(f"{idx}. 클러스터 {hotzone['cluster_id']}: "
              f"점수 {hotzone['cluster_user_score']:.4f}")
    
    return result


def process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir):
    """
    모든 유저에 대해 일괄 처리
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 유저 정보 로드
    print("📂 유저 정보 파일 로드 중...")
    user_info_dict = load_user_info(user_info_file)
    print(f"✅ {len(user_info_dict)}명의 유저 정보 로드 완료")
    
    # user_pref_dir에서 모든 유저 파일 찾기
    user_files = [f for f in os.listdir(user_pref_dir) if f.endswith('_recommendations_softmax.json')]
    
    print(f"\n🚀 총 {len(user_files)}명의 유저 처리 시작...\n")
    
    for user_file in sorted(user_files):
        user_id = user_file.replace('_recommendations_softmax.json', '')
        user_pref_path = os.path.join(user_pref_dir, user_file)
        output_path = os.path.join(output_dir, f"{user_id}_personalized_hotzones.json")
        
        print(f"\n{'='*70}")
        print(f"👤 {user_id} 처리 중...")
        print(f"{'='*70}")
        
        score_hotzones_with_user_preference(hotzone_file, user_pref_path, user_info_dict, output_path)
    
    print(f"\n✨ 모든 유저 처리 완료! 총 {len(user_files)}개 파일 생성")


# ========================================
# 🚀 실행
# ========================================
if __name__ == "__main__":
    base_dir = r"C:\Users\changjin\workspace\lab\pln"
    
    # 파일 경로 설정
    hotzone_file = os.path.join(base_dir, "clustering", "greedy_hotzones_merged.json")
    user_pref_dir = os.path.join(base_dir, "vector_embedding", "review_count_with_softmax", "for_clustering_user")
    user_info_file = os.path.join(base_dir, "data_set", "1000_user_info.csv")
    output_dir = os.path.join(base_dir, "clustering", "personalized_hotzones")
    
    # 옵션 1: 특정 유저 한 명만 처리
    # user_info_dict = load_user_info(user_info_file)
    # user_file = os.path.join(user_pref_dir, "U0001_recommendations_softmax.json")
    # output_file = os.path.join(output_dir, "U0001_personalized_hotzones.json")
    # os.makedirs(output_dir, exist_ok=True)
    # score_hotzones_with_user_preference(hotzone_file, user_file, user_info_dict, output_file)
    
    # 옵션 2: 모든 유저 일괄 처리
    process_all_users(hotzone_file, user_pref_dir, user_info_file, output_dir)