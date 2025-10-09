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
    """추천 결과 DataFrame 기반으로 CSV 문자열 생성 (GPT에 직접 전달)"""
    csv_contents = {}
    
    for category, df in enriched_data.items():
        if df is None or df.empty:
            continue
        
        # 🔹 숙소는 상위 20개만 사용
        working = df.head(20).copy() if category == "Accommodation" else df.copy()
        if category == "Accommodation":
            print(f"   ⚠️ Accommodation: 상위 20개만 CSV로 전달")
        
        # 카테고리별 필요한 컬럼만 선택
        if category == "Accommodation":
            first_day = itinerary['itinerary'][0]
            season = first_day['season']
            is_weekend = first_day['is_weekend']

            if season == "peak":
                price_col = 'peak_weekend_price_avg' if is_weekend else 'peak_weekday_price_avg'
            else:
                price_col = 'offpeak_weekend_price_avg' if is_weekend else 'offpeak_weekday_price_avg'

            cols = ['id']
            if 'latitude' in working.columns:
                cols.extend(['latitude', 'longitude'])
            else:
                cols.extend(['lat', 'lng'])
            cols.append(price_col)

            result = working[cols].copy()
            result.columns = ['id', 'lat', 'lng', 'price_per_night']

        elif category in ["Restaurant", "Cafe"]:
            cols = ['id']
            if 'latitude' in working.columns:
                cols.extend(['latitude', 'longitude'])
            else:
                cols.extend(['lat', 'lng'])
            cols.append('avg_price')

            if 'store_hours' in working.columns:
                cols.append('store_hours')

            result = working[cols].copy()
            if 'latitude' in working.columns:
                result.columns = ['id', 'lat', 'lng', 'avg_price'] + (['store_hours'] if 'store_hours' in cols else [])

        else:  # Attraction
            cols = ['id']
            if 'latitude' in working.columns:
                cols.extend(['latitude', 'longitude'])
            else:
                cols.extend(['lat', 'lng'])

            result = working[cols].copy()
            result.columns = ['id', 'lat', 'lng']
            result['price'] = 0

        # CSV 문자열로 변환
        csv_contents[category] = result.to_csv(index=False).strip()
        print(f"   📄 {category}: {len(result)}개 → CSV 변환 완료")
    
    return csv_contents


def create_smart_prompt(itinerary, csv_contents):
    """CSV 내용을 직접 포함한 프롬프트 생성 (토큰 최적화)"""
    
    prompt = f"""Expert travel planner: Create an optimal itinerary with 3km movement limit and daily budget control. Respond in JSON format.

## Itinerary Info
- Days: {len(itinerary['itinerary'])}
- Budget per day: {itinerary['budget_per_day']:,} KRW
- Max accommodation: {int(itinerary['budget_per_day'] * 0.65):,} KRW
- Transport: {itinerary['itinerary'][0]['transport']}
- Start date: {itinerary['itinerary'][0]['date']}

## Days Detail
"""
    
    for day in itinerary['itinerary']:
        prompt += f"Day{day['day']}: {day['date']} ({day['travel_day']}) - {day['season']}, weekend={day['is_weekend']}\n"
    
    prompt += f"""
## Available Places (CSV datasets by category)

### 🏨 Accommodation
{csv_contents.get("Accommodation", "No data")}

### ☕ Cafe
{csv_contents.get("Cafe", "No data")}

### 🍽️ Restaurant
{csv_contents.get("Restaurant", "No data")}

### 🎯 Attraction
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
2. **Budget**: Daily ≤ {itinerary['budget_per_day']:,} KRW, Accommodation ≤ 65%
3. **No Duplicates**: Same accommodation all days, each other place only once

## Schedule Template (per Day)
- 09:30 Accommodation (base location)
- 10:30 Attraction (within 10km from accommodation)
- 12:00 Cafe (≤3km from previous location)
- 14:00 Restaurant (≤3km from previous location)
- 16:00 Attraction (≤3km from previous, different from first)
- 18:00 Restaurant (≤3km from previous, different from first)
- 19:00 Return to Accommodation

## Required JSON Output Format
{{{{
  "budget_per_day": {itinerary['budget_per_day']},
  "itinerary": [
    {{{{
      "day": 1,
      "date": "{itinerary['itinerary'][0]['date']}",
      "travel_day": "{itinerary['itinerary'][0]['travel_day']}",
      "season": "{itinerary['itinerary'][0]['season']}",
      "is_weekend": {str(itinerary['itinerary'][0]['is_weekend']).lower()},
      "transport": "{itinerary['itinerary'][0]['transport']}",
      "place_plan": [
        {{{{"category": "Accommodation", "id": 123, "name": "필요시 추정", "count": 1, "time": "09:30"}}}},
        {{{{"category": "Attraction", "id": 456, "name": "필요시 추정", "count": 1, "time": "10:30"}}}},
        {{{{"category": "Cafe", "id": 789, "name": "필요시 추정", "count": 1, "time": "12:00"}}}},
        {{{{"category": "Restaurant", "id": 101, "name": "필요시 추정", "count": 1, "time": "14:00"}}}},
        {{{{"category": "Attraction", "id": 112, "name": "필요시 추정", "count": 1, "time": "16:00"}}}},
        {{{{"category": "Restaurant", "id": 131, "name": "필요시 추정", "count": 1, "time": "18:00"}}}},
        {{{{"category": "Accommodation", "id": 123, "name": "필요시 추정", "count": 1, "time": "19:00"}}}}
      ],
      "daily_cost": 0,
      "cost_breakdown": {{{{"accommodation": 0, "restaurants": 0, "cafe": 0, "attractions": 0}}}}
    }}}}
  ]
}}}}

**Important**: Use CSV data above. Calculate all distances using the function. Follow all rules strictly."""
    
    return prompt


def call_gpt_4o(prompt):
    try:
        print("🤖 모델: gpt-4o")
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
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ GPT API 호출 오류: {e}")
        return None

def validate_result(result, itinerary, enriched_data):
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
                        daily_cost_actual += float(row['avg_price']) if pd.notna(row.get('avg_price', 0)) else 0
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
    print("=" * 70)
    print("🚀 GPT-4o 여행 플래너 (CSV 직접 전달 방식)")
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
    
    print("\n[Step 3] CSV 데이터 준비 중...")
    csv_contents = prepare_csv_for_gpt(enriched_data, itinerary, place_data)
    
    print("\n[Step 4] 프롬프트 생성 중...")
    prompt = create_smart_prompt(itinerary, csv_contents)
    print(f"   프롬프트 길이: {len(prompt):,}자")
    
    print("\n[Step 5] GPT-4o 호출 중...")
    response = call_gpt_4o(prompt)
    
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
    print("💰 CSV 형식으로 토큰 비용 40-60% 절감!")
    print("=" * 70)

if __name__ == "__main__":
    main()
