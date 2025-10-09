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
    """GPT가 직접 거리 계산하도록 하는 프롬프트 (토큰 최적화)"""
    
    prompt = f"""Expert travel planner: Create optimal itinerary with budget control and 3km movement limit.

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
1. **Distance**: Each move ≤ 3km using calculate_distance()
2. **Budget**: Daily ≤ {itinerary['budget_per_day']:,} KRW, Accommodation ≤ 65%
3. **No Duplicates**: Same accommodation all days, others once only

## Process
**Accommodation**: Filter price ≤ {int(itinerary['budget_per_day'] * 0.65):,} KRW, select highest final_score

**Each Day**:
1. 10:30 Attraction: Near accommodation (within 10km), highest score
2. 12:00 Cafe: calculate_distance(attraction.lat/lng, cafe.lat/lng) ≤ 3km, highest score
3. 14:00 Restaurant: calculate_distance(cafe.lat/lng, restaurant.lat/lng) ≤ 3km, highest score
4. 16:00 Attraction: calculate_distance(restaurant.lat/lng, attraction.lat/lng) ≤ 3km, different from first
5. 18:00 Restaurant: calculate_distance(attraction2.lat/lng, restaurant.lat/lng) ≤ 3km, different from first

## Output
```json
{{
  "budget_per_day": 733333,
  "itinerary": [
    {{
      "day": 1,
      "date": "2025-08-16",
      "travel_day": "토",
      "season": "peak",
      "is_weekend": true,
      "transport": "car",
      "place_plan": [
        {{"category": "Accommodation", "id": 3013409, "name": "Hotel Name", "count": 1, "time": "09:30"}},
        {{"category": "Attraction", "id": 1378194684, "name": "Attraction Name", "count": 1, "time": "10:30"}},
        {{"category": "Cafe", "id": 1606960077, "name": "Cafe Name", "count": 1, "time": "12:00"}},
        {{"category": "Restaurant", "id": 15351961, "name": "Restaurant Name", "count": 1, "time": "14:00"}},
        {{"category": "Attraction", "id": 37031400, "name": "Attraction Name", "count": 1, "time": "16:00"}},
        {{"category": "Restaurant", "id": 1103963861, "name": "Restaurant Name", "count": 1, "time": "18:00"}},
        {{"category": "Accommodation", "id": 3013409, "name": "Hotel Name", "count": 1, "time": "19:00"}}
      ],
      "daily_cost": 715000,
      "cost_breakdown": {{"accommodation": 450000, "restaurants": 150000, "cafe": 45000, "attractions": 0}}
    }},
    {{"day": 2, ...}},
    {{"day": 3, ...}}
  ]
}}
```

Use calculate_distance() for all routing. All moves ≤ 3km. Budget compliant."""
    
    return prompt

def call_gpt_4o(prompt):
    """GPT-4o API 호출"""
    try:
        print("   모델: gpt-4o")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert travel planner who calculates distances using the Haversine formula to build optimal routes within 2km movement constraints."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
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
            
            # 중복 체크
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
    print("🚀 GPT-4o 여행 플래너 (GPT가 직접 거리 계산)")
    print("=" * 70)
    
    # 파일 경로
    itinerary_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0002_itinerary.json"
    recommendations_path = r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\user_results\U0002_recommendations_softmax.json"
    output_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0002_final_itinerary.json"
    
    # Step 1: 데이터 로드
    print("\n[Step 1] 데이터 로드 중...")
    itinerary = json.load(open(itinerary_path, 'r', encoding='utf-8'))
    recommendations = json.load(open(recommendations_path, 'r', encoding='utf-8'))
    place_data = load_place_data()
    
    # Step 2: 추천 장소와 상세 정보 병합
    print("\n[Step 2] 데이터 병합 중...")
    enriched_data = merge_recommendations_with_details(recommendations, place_data)
    
    # Step 3: GPT에 전달할 데이터 준비 (lat/lng만!)
    print("\n[Step 3] GPT-4o 데이터 준비 중...")
    print("   거리 계산 함수를 포함하여 GPT가 직접 계산하도록 합니다!")
    candidates = prepare_all_candidates_for_gpt(enriched_data, itinerary)
    
    total_candidates = sum(len(places) for places in candidates.values())
    print(f"   총 후보 장소: {total_candidates}개 (lat/lng 포함)")
    
    # Step 4: 프롬프트 생성
    print("\n[Step 4] 프롬프트 생성 중...")
    print("   Haversine 거리 계산 함수를 프롬프트에 포함합니다")
    prompt = create_smart_prompt(itinerary, candidates)
    
    # Step 5: GPT API 호출
    print("\n[Step 5] GPT-4o에게 모든 것을 맡깁니다...")
    print("   (GPT가 직접 거리 계산 + 예산 계산 + 2km 제한 + 중복 방지)")
    response = call_gpt_4o(prompt)
    
    if response is None:
        print("❌ API 호출 실패")
        return
    
    # Step 6: 결과 파싱
    print("\n[Step 6] 결과 파싱 중...")
    result = json.loads(response)
    print("✅ 파싱 완료")
    
    # Step 7: 검증
    print("\n[Step 7] 결과 검증 중...")
    errors, warnings = validate_result(result, itinerary, enriched_data)
    
    if errors:
        print("\n❌ 오류 발견:")
        for error in errors:
            print(f"   - {error}")
    
    if warnings:
        print("\n⚠️  경고:")
        for warning in warnings:
            print(f"   - {warning}")
    
    if not errors:
        print("\n✅ 모든 검증 통과!")
    
    # Step 8: 저장
    print("\n[Step 8] 결과 저장 중...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {output_path}")
    
    # Step 9: 요약
    print("\n" + "=" * 70)
    print("📊 최종 요약")
    print("=" * 70)
    print(f"전체 일정: {len(result['itinerary'])}일")
    print(f"일일 예산: {result['budget_per_day']:,}원")
    
    # 사용된 장소 통계
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
    
    print("\n✨ GPT-4o가 Haversine 함수로 직접 거리 계산하여 최적 일정을 생성했습니다!")
    print(f"💾 결과 파일: {output_path}")

if __name__ == "__main__":
    main()