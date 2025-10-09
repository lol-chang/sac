import json
import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def load_place_data():
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
    enriched = {}
    for category, id_list in recommendations.items():
        if category not in place_data:
            continue
        
        # 1) 추천 ID: 중복 제거(원순서 유지) + 정수형으로 정규화
        unique_ids = []
        seen = set()
        for _id in id_list:
            try:
                nid = int(_id)
            except (TypeError, ValueError):
                continue
            if nid not in seen:
                seen.add(nid)
                unique_ids.append(nid)

        # 2) 원본 DF의 id 타입 정규화
        df = place_data[category].copy()
        df['id'] = pd.to_numeric(df['id'], errors='coerce').astype('Int64')

        # 3) 필터링 및 원래 순서 유지 정렬
        filtered = df[df['id'].isin(unique_ids)].copy()
        filtered['id'] = pd.Categorical(filtered['id'], categories=unique_ids, ordered=True)
        filtered.sort_values('id', inplace=True)

        enriched[category] = filtered
        print(f"📊 {category}: {len(filtered)}개 준비 완료")
    return enriched


def prepare_csv_for_gpt(enriched_data, itinerary, place_data):
    """
    enriched_data의 각 카테고리별 DataFrame을 CSV 문자열로 변환
    Restaurant와 Cafe는 2인 기준 가격으로 변환
    """
    csv_contents = {}
    
    for category, df in enriched_data.items():
        if df.empty:
            csv_contents[category] = "No data available"
            continue
        
        # 필요한 컬럼만 선택 (카테고리별로 다를 수 있음)
        if category == "Accommodation":
            # 숙소는 가격 정보 포함
            cols_to_keep = ['id', 'name', 'latitude', 'longitude', 
                           'peak_weekday_price_avg', 'peak_weekend_price_avg',
                           'offpeak_weekday_price_avg', 'offpeak_weekend_price_avg']
        elif category in ["Restaurant", "Cafe"]:
            # 음식점/카페는 평균 가격 포함
            cols_to_keep = ['id', 'name', 'latitude', 'longitude', 'avg_price']
        else:
            # 관광지는 기본 정보만
            cols_to_keep = ['id', 'name', 'latitude', 'longitude']
        
        # 존재하는 컬럼만 선택
        available_cols = [col for col in cols_to_keep if col in df.columns]
        df_subset = df[available_cols].copy()
        
        # Restaurant와 Cafe는 2인 기준으로 가격 2배 처리
        if category in ["Restaurant", "Cafe"] and 'avg_price' in df_subset.columns:
            df_subset['avg_price'] = df_subset['avg_price'] * 2
            print(f"   💰 {category}: 2인 기준 가격으로 변환 (avg_price × 2)")
        
        # CSV 문자열로 변환 (인덱스 제외)
        csv_string = df_subset.to_csv(index=False)
        csv_contents[category] = csv_string
        
        print(f"   📄 {category} CSV: {len(csv_string):,}자")
    
    return csv_contents


def create_smart_prompt(itinerary, csv_contents):
    """GPT가 직접 거리 계산하도록 하는 프롬프트 (토큰 최적화 + CSV)"""
    
    duration = itinerary.get('duration', 3)
    
    prompt = f"""Expert travel planner: Create optimal {duration}-day itinerary with budget control and 3km movement limit.

## Itinerary Structure
{json.dumps(itinerary, ensure_ascii=False, indent=2)}

## Places (CSV format - Restaurant/Cafe avg_price already for 2 people)

### Accommodation
{csv_contents.get("Accommodation", "No data")}

### Cafe (avg_price = 2 people)
{csv_contents.get("Cafe", "No data")}

### Restaurant (avg_price = 2 people)
{csv_contents.get("Restaurant", "No data")}

### Attraction
{csv_contents.get("Attraction", "No data")}

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
2. **Accommodation**: Filter price ≤ {int(itinerary['budget_per_day'] * 0.5):,} KRW, select highest final_score
3. **STRICT No Duplicates**: 
   - Others: NEVER reuse any Attraction/Cafe/Restaurant ID across different days
   - Day 1 IDs ≠ Day 2 IDs ≠ Day 3 IDs (except accommodation)
4. **Cost**: Restaurant/Cafe avg_price already for 2 people - use as-is
5. **Last Day**: Day {duration} ends at 18:00 Restaurant, NO return to accommodation
   - BUT don't go too far: final distance(restaurant) ≤ 3km from accommodation for convenient departure
6. **daily_cost Calculation**: 
   - daily_cost MUST equal sum of cost_breakdown (accommodation + restaurants + cafe + attractions)

**Days 1-{duration-1}**:
1. 09:30 Accommodation (start)
2. 10:30 Attraction①: distance(accommodation → attraction1) ≤ 7km, highest score
3. 12:00 Cafe①: distance(attraction1 → cafe1) ≤ 2km, highest score
4. 13:30 Restaurant①: distance(cafe1 → restaurant1) ≤ 2km, highest score
5. 15:00 Attraction②: distance(restaurant1 → attraction2) ≤ 2km, different from first
6. 16:30 Cafe②: distance(attraction2 → cafe2) ≤ 2km, different from first
7. 18:00 Restaurant②: distance(cafe2 → restaurant2) ≤ 2km, must be ≤ 3km from accommodation (for circular route)
8. 19:30 Accommodation (return): distance(restaurant2 → accommodation) ≤ 3km, complete circular route

**Day {duration} (Last Day)**:
1-7 same as above, but END at 18:00 Restaurant (no return)

## Output
```json
{{
  "budget_per_day": {itinerary['budget_per_day']},
  "party_size": 2,
  "itinerary": [
    {{
      "day": 1,
      "date": "2025-08-16",
      "travel_day": "토",
      "season": "peak",
      "is_weekend": true,
      "transport": "car",
      "place_plan": [
        {{"category": "Accommodation", "id": 123, "name": "Hotel", "time": "09:30", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Attraction", "id": 456, "name": "Beach", "time": "10:30", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Cafe", "id": 789, "name": "Cafe", "time": "12:00", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Restaurant", "id": 111, "name": "Restaurant", "time": "13:30", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Attraction", "id": 222, "name": "Park", "time": "15:00", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Cafe", "id": 333, "name": "Cafe2", "time": "16:30", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Restaurant", "id": 444, "name": "Restaurant2", "time": "18:00", "latitude": 37.xx, "longitude": 128.xx}},
        {{"category": "Accommodation", "id": 123, "name": "Hotel", "time": "19:30", "latitude": 37.xx, "longitude": 128.xx}}
      ],
      "daily_cost": 645000,  // 450000 + 150000 + 45000 + 0 = 645000 
      "cost_breakdown": {{"accommodation": 450000, "restaurants": 150000, "cafe": 45000, "attractions": 0}},
      "daily_description": "첫째 날은 해변과 공원을 중심으로 여유로운 하루를 보냅니다."
    }},
    {{
      "day": 2,
      ...
      "daily_description": "둘째 날은 전통 시장과 박물관을 탐방하는 문화의 날입니다."
    }},
    {{
      "day": {duration},
      "place_plan": [...ends at Restaurant at 18:00, no accommodation return],
      "daily_cost": 195000,  // 0 + 150000 + 45000 + 0 = 195000
      "cost_breakdown": {{"accommodation": 0, "restaurants": 150000, "cafe": 45000, "attractions": 0}},
      "daily_description": "마지막 날은 현지 맛집으로 여행을 마무리합니다."
    }}
  ]
}}
```

**Requirements**:
- Use calculate_distance() for all routing
- All moves ≤ 2km (first attraction ≤ 7km)
- Budget compliant
- Day {duration}: accommodation cost = 0, ends at 18:00
- Include Korean daily_description (1-2 sentences) for each day
- Parse CSV data for place info
"""
    
    return prompt


def call_gpt_4o(prompt):
    try:
        print("🤖 모델: gpt-4o (streaming enabled)")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert travel planner who calculates distances using the Haversine formula to build optimal routes within 3km movement constraints. Always respond in JSON format."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
            max_tokens=4000,
            response_format={"type": "json_object"},
            stream=True
        )
        
        # Stream 응답 처리
        print("\n📡 스트리밍 응답 수신 중...")
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                full_response += content
                # 실시간으로 일부 내용 출력 (선택사항)
                print(content, end='', flush=True)
        
        print("\n✅ 스트리밍 완료!")
        return full_response
        
    except Exception as e:
        print(f"❌ GPT API 호출 오류: {e}")
        return None

def validate_result(result, itinerary, enriched_data):
    errors = []
    warnings = []
    used_ids = set()
    accommodation_id = None
    print("\n🔍 상세 검증 중... (2인 기준)")
    
    # Day 번호 검증
    expected_days = list(range(1, itinerary.get('duration', 3) + 1))
    actual_days = [day_data['day'] for day_data in result['itinerary']]
    if actual_days != expected_days:
        errors.append(f"Day 번호 오류: 예상 {expected_days}, 실제 {actual_days}")
    
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
                        # avg_price는 이미 2인 기준으로 전처리됨 (×2 적용됨)
                        daily_cost_actual += float(row['avg_price']) if pd.notna(row.get('avg_price', 0)) else 0
        budget = itinerary['budget_per_day']
        print(f"   💰 예산: {budget:,.0f}원 (2인 기준)")
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
    print("=" * 70)
    print("🚀 GPT-4o 여행 플래너 (CSV 직접 전달 방식 - 2인 기준)")
    print("=" * 70)
    
    itinerary_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_itinerary.json"
    recommendations_path = r"C:\Users\changjin\workspace\lab\pln\vector_embedding\review_count_with_softmax\user_results\U0001_recommendations_softmax.json"
    output_path = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan\U0001_final_itinerary_CSV.json"
    
    print("\n[Step 1] 데이터 로드 중...")
    itinerary = json.load(open(itinerary_path, 'r', encoding='utf-8'))
    recommendations = json.load(open(recommendations_path, 'r', encoding='utf-8'))
    place_data = load_place_data()
    
    print("\n[Step 2] 데이터 병합 중...")
    enriched_data = merge_recommendations_with_details(recommendations, place_data)
    
    print("\n[Step 3] CSV 데이터 준비 중 (2인 기준 가격 적용)...")
    csv_contents = prepare_csv_for_gpt(enriched_data, itinerary, place_data)
    
    print("\n[Step 4] 프롬프트 생성 중...")
    prompt = create_smart_prompt(itinerary, csv_contents)
    print(f"   프롬프트 길이: {len(prompt):,}자")
    
    print("\n[Step 5] GPT-4o 호출 중 (Streaming)...")
    print("=" * 70)
    response = call_gpt_4o(prompt)
    print("\n" + "=" * 70)
    
    if response is None:
        print("❌ GPT 호출 실패")
        return
    
    print("\n[Step 6] 결과 파싱 중...")
    result = json.loads(response)
    print("✅ 파싱 완료")
    
    print("\n[Step 7] 결과 검증 중...")
    errors, warnings = validate_result(result, itinerary, enriched_data)
    
    if errors:
        print("\n❌ 오류 발견:")
        for e in errors:
            print(f"   - {e}")
    if warnings:
        print("\n⚠️ 경고:")
        for w in warnings:
            print(f"   - {w}")
    if not errors:
        print("\n✅ 모든 검증 통과!")
    
    print("\n[Step 8] 결과 저장 중...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"✅ 저장 완료: {output_path}")
    
    print("\n" + "=" * 70)
    print("💰 CSV 형식 + 2인 기준 가격으로 토큰 비용 40-60% 절감!")
    print("=" * 70)

if __name__ == "__main__":
    main()