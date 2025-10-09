import json
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일에서 환경변수 로드
load_dotenv()

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_place_data():
    """장소 상세 정보 CSV 파일 로드"""
    base_path = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"
    
    files = {
        "Attraction": "attractions_fixed.csv",
        "Restaurant": "restaurants_fixed.csv",
        "Accommodation": "accommodations_fixed.csv",
        "Cafe": "cafe_fixed.csv"
    }
    
    place_data = {}
    for category, filename in files.items():
        df = pd.read_csv(os.path.join(base_path, filename))
        place_data[category] = df
        print(f"✅ {category}: {len(df)}개 로드")
    
    return place_data

def merge_recommendations_with_details(recommendations, place_data):
    """추천 장소와 상세 정보 병합"""
    enriched = {}
    
    for category, places in recommendations.items():
        if category not in place_data:
            continue
            
        place_ids = [p["id"] for p in places]
        df = place_data[category]
        filtered = df[df['id'].isin(place_ids)].copy()
        
        score_map = {p["id"]: p["final_score"] for p in places}
        filtered['final_score'] = filtered['id'].map(score_map)
        
        enriched[category] = filtered
        print(f"📊 {category}: {len(filtered)}개 준비 완료")
    
    return enriched

def prepare_all_candidates_for_gpt(enriched_data, itinerary):
    """GPT에 전달할 전체 후보 데이터 준비 (lat/lng만 포함)"""
    candidates_json = {}
    
    for category, df in enriched_data.items():
        places = []
        for _, row in df.iterrows():
            place = {
                "id": int(row['id']),
                "name": str(row['name']),
                "final_score": float(row['final_score']),
                "lat": float(row['latitude']) if 'latitude' in row else float(row['lat']),
                "lng": float(row['longitude']) if 'longitude' in row else float(row['lng']),
            }
            
            # 카테고리별 가격 정보 추가
            if category == "Accommodation":
                first_day = itinerary['itinerary'][0]
                season = first_day['season']
                is_weekend = first_day['is_weekend']
                
                if season == "peak":
                    if is_weekend:
                        price_col = 'peak_weekend_price_avg'
                    else:
                        price_col = 'peak_weekday_price_avg'
                else:
                    if is_weekend:
                        price_col = 'offpeak_weekend_price_avg'
                    else:
                        price_col = 'offpeak_weekday_price_avg'
                
                place["price_per_night"] = float(row[price_col]) if pd.notna(row[price_col]) else 0
                
            elif category in ["Restaurant", "Cafe"]:
                place["avg_price"] = float(row['avg_price']) if pd.notna(row.get('avg_price', 0)) else 0
            else:
                place["price"] = 0
            
            places.append(place)
        
        places.sort(key=lambda x: x['final_score'], reverse=True)
        candidates_json[category] = places
    
    return candidates_json

def create_smart_prompt(itinerary, candidates):
    """GPT가 직접 거리 계산 및 설명문 작성하도록 하는 프롬프트"""
    
    prompt = f"""Expert travel planner: Create an optimal n-day itinerary in Korea with unique daily places, budget control, and 3km movement limit. Please respond in JSON format.

    ## Itinerary Structure
    {json.dumps(itinerary, ensure_ascii=False, indent=2)}

    ## Places (lat/lng included)
    {json.dumps(candidates, ensure_ascii=False, indent=2)}

    ## Distance Function (REQUIRED)
    ```python
    def calculate_distance(lat1, lng1, lat2, lng2):
        import math
        lat1_rad, lng1_rad, lat2_rad, lng2_rad = map(math.radians, [lat1, lng1, lat2, lng2])
        dlat, dlng = lat2_rad - lat1_rad, lng2_rad - lng1_rad
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        return 6371 * 2 * math.asin(math.sqrt(a))  # km
    ```

    ## Rules
    - Distance: Every move ≤ 3km using calculate_distance()
    - Budget: Daily ≤ {itinerary['budget_per_day']:,} KRW, Accommodation ≤ 65%
    - No Repetition: Same accommodation for all days. Each Attraction, Cafe, Restaurant must appear only once across the entire itinerary (no repeats across days).

    ## Schedule Template
    - 09:30 → Accommodation (base)
    - 10:30 → Attraction (within 10km)
    - 12:00 → Cafe (≤3km)
    - 13:30 → Restaurant (≤3km)
    - 15:00 → Attraction (≤3km, different from the first attraction)
    - 16:30 → Cafe (≤3km, different from the first cafe)
    - 18:00 → Restaurant (≤3km, different from the first restaurant)
    - 19:30 → Return to accommodation

    ## Output Requirements
    Include a Korean daily description summarizing the route, mood, and highlights (1–2 sentences) in "daily_description".
    
    ## Required JSON Format
    {{
    "budget_per_day": 666666,
    "itinerary": [
        {{
        "day": 1,
        "date": "2025-10-07",
        "travel_day": "화",
        "season": "offpeak",
        "is_weekend": false,
        "transport": "car",
        "place_plan": [...],
        "daily_cost": 666666,
        "cost_breakdown": {{"accommodation": ..., "restaurants": ..., "cafe": ..., "attractions": ...}},
        "daily_description": "첫째 날은 경포해변을 중심으로 바다 풍경과 해물 요리를 즐기는 여유로운 하루입니다."
        }},
        {{
        "day": 2,
        ...
        }},
        {{
        "day": 3,
        ...
        }}
    ]
    }}

    ## Additional Instructions
    - Use calculate_distance() for all movements
    - Avoid repeating any non-accommodation place across days
    - Keep daily_description concise (1–2 Korean sentences)
    - Balance attraction, cafe, and restaurant diversity
    - Return valid JSON only
    """
    return prompt

def call_gpt_4o(prompt):
    """GPT-4o API 호출"""
    try:
        print(" 모델: gpt-4o")
        response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
        {
        "role": "system",
        "content": "You are an expert travel planner who calculates distances using the Haversine formula to build optimal routes within 3km movement constraints."
        },
        {
        "role": "user",
        "content": prompt
        }
        ],
        temperature=0.25,
        max_tokens=4000,
        response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ GPT API 호출 오류: {e}")
    return None

def validate_result(result, itinerary, enriched_data):
    """결과 검증"""
    errors = []
    warnings = []
    used_ids = set()
    accommodation_id = None

    print("\n🔍 상세 검증 중...")

    for day_data in result['itinerary']:
        day = day_data['day']
        print(f"\n📅 Day {day} 검증:")
        
        daily_cost_claimed = day_data.get('daily_cost', 0)
        daily_cost_actual = 0
        
        for place in day_data['place_plan']:
            place_id = place.get('id')
            place_name = place.get('name')
            category = place['category']
            
            if place_id is None:
                errors.append(f"Day {day}: {category}에 id가 없음")
                continue
            
            if place_name is None:
                errors.append(f"Day {day}: {category}에 name이 없음")
            
            # 중복 체크 (숙소 제외, 전체 일정 단위로 금지)
            if category == "Accommodation":
                if accommodation_id is None:
                    accommodation_id = place_id
                    print(f"   🏨 숙소 확정: {place_name} (ID: {place_id})")
                elif accommodation_id != place_id:
                    errors.append(f"Day {day}: 다른 숙소 사용")
            else:
                if place_id in used_ids:
                    errors.append(f"Day {day}: 중복 장소 (id: {place_id})")
                used_ids.add(place_id)
            
            # 가격 계산
            if category in enriched_data:
                df = enriched_data[category]
                matching = df[df['id'] == place_id]
                
                if matching.empty:
                    errors.append(f"Day {day}: 후보에 없는 장소 (id: {place_id})")
                else:
                    row = matching.iloc[0]
                    if category == "Accommodation":
                        season = day_data['season']
                        is_weekend = day_data['is_weekend']
                        if season == "peak":
                            price_col = 'peak_weekend_price_avg' if is_weekend else 'peak_weekday_price_avg'
                        else:
                            price_col = 'offpeak_weekend_price_avg' if is_weekend else 'offpeak_weekday_price_avg'
                        daily_cost_actual += float(row[price_col]) if pd.notna(row[price_col]) else 0
                    elif category in ["Restaurant", "Cafe"]:
                        daily_cost_actual += float(row['avg_price']) if pd.notna(row.get('avg_price', 0)) else 0
        
        # 예산 체크
        budget = itinerary['budget_per_day']
        print(f"   💰 예산: {budget:,.0f}원")
        print(f"   💳 GPT 계산: {daily_cost_claimed:,.0f}원")
        print(f"   ✅ 실제: {daily_cost_actual:,.0f}원")
        
        if daily_cost_actual > budget * 1.05:
            errors.append(f"Day {day}: 예산 초과 ({daily_cost_actual:,.0f}원)")
        elif daily_cost_actual > budget:
            warnings.append(f"Day {day}: 예산 약간 초과 ({daily_cost_actual:,.0f}원)")
        else:
            print(f"   ✅ 예산 준수!")

    return errors, warnings


def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("🚀 GPT-4o 여행 플래너 (유니크 장소 + 하루 요약 포함)")
    print("=" * 70)

    itinerary_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_itinerary.json"
    # recommendations_path = r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\user_results\U0002_recommendations_softmax.json"
    recommendations_path = r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\user_results\U0001_recommendations_softmax.json"
    output_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_testtesttesttest.json"

    # Step 1
    print("\n[Step 1] 데이터 로드 중...")
    itinerary = json.load(open(itinerary_path, 'r', encoding='utf-8'))
    recommendations = json.load(open(recommendations_path, 'r', encoding='utf-8'))
    place_data = load_place_data()

    # Step 2
    print("\n[Step 2] 데이터 병합 중...")
    enriched_data = merge_recommendations_with_details(recommendations, place_data)

    # Step 3
    print("\n[Step 3] GPT 데이터 준비 중...")
    candidates = prepare_all_candidates_for_gpt(enriched_data, itinerary)

    # Step 4
    print("\n[Step 4] 프롬프트 생성 중...")
    prompt = create_smart_prompt(itinerary, candidates)

    # Step 5
    print("\n[Step 5] GPT 호출 중...")
    response = call_gpt_4o(prompt)
    if response is None:
        print("❌ API 호출 실패")
        return

    # Step 6
    print("\n[Step 6] 결과 파싱 중...")
    result = json.loads(response)
    print("✅ 파싱 완료")

    # Step 7
    print("\n[Step 7] 결과 검증 중...")
    errors, warnings = validate_result(result, itinerary, enriched_data)

    if errors:
        print("\n❌ 오류 발견:")
        for error in errors:
            print(f"   - {error}")
    if warnings:
        print("\n⚠️ 경고:")
        for warning in warnings:
            print(f"   - {warning}")
    if not errors:
        print("\n✅ 모든 검증 통과!")

    # Step 8
    print("\n[Step 8] 결과 저장 중...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {output_path}")

    # Step 9
    print("\n" + "=" * 70)
    print("📊 최종 요약")
    print("=" * 70)
    print(f"전체 일정: {len(result['itinerary'])}일")
    print(f"일일 예산: {result['budget_per_day']:,}원")

    accommodation_name = None
    used_places = {"Cafe": set(), "Restaurant": set(), "Attraction": set()}
    total_cost = 0

    for day_data in result['itinerary']:
        total_cost += day_data.get('daily_cost', 0)
        for place in day_data['place_plan']:
            if place['category'] == "Accommodation":
                accommodation_name = place.get('name', 'Unknown')
            elif place['category'] in used_places:
                used_places[place['category']].add(place['id'])

    print(f"\n🏨 숙소: {accommodation_name}")
    print(f"\n📍 사용된 장소 수:")
    for category, ids in used_places.items():
        emoji = {"Cafe": "☕", "Restaurant": "🍽️", "Attraction": "🎯"}
        print(f"  {emoji[category]} {category}: {len(ids)}개")

    print(f"\n💰 전체 여행 비용: {total_cost:,}원")
    print(f"💳 일 평균: {total_cost // len(result['itinerary']):,}원")
    print("\n✨ 하루별 설명(daily_description)이 포함된 최종 일정이 생성되었습니다!")


if __name__ == "__main__":
    main()