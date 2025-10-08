import os
import json
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI

# ========== 1. 환경변수 로드 ==========
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# ========== 2. 프롬프트 정의 ==========
SYSTEM_PROMPT = """여행 일정 JSON 생성기입니다.

출력 형식:
{
  "budget_per_day": 전체예산/일수,
  "itinerary": [
    {
      "day": 1,
      "date": "YYYY-MM-DD",
      "travel_day": "월",
      "season": "peak",
      "is_weekend": false,
      "transport": "car",
      "place_plan": [
        {"category": "Accommodation", "count": 1, "time": "09:30"},
        {"category": "Cafe", "count": 1, "time": "10:30"}
      ]
    }
  ]
}

규칙:
1. 모든 날 첫 활동 = Accommodation (숙소 출발)
2. 마지막 날 제외하고 마지막 활동 = Accommodation (숙소 귀환)
3. 마지막 날은 Accommodation 귀환 없음
4. travel_day = 월, 화, 수, 목, 금, 토, 일 중 하나
5. season = 7,8,12,1월이면 "peak", 나머지는 "offpeak"
6. is_weekend = 금요일 또는 토요일이면 true, 나머지 false

시간대 (나이별):
- 10~20대: 09:30~20:30
- 30~40대: 08:30~20:00
- 50대+: 08:00~18:30

스타일별 활동 개수 (하루 기준):
- Healing: Attraction 1~2, Cafe 1~2, Restaurant 2
- Foodie: Attraction 1~2, Cafe 1~2, Restaurant 3
- Activity: Attraction 3~4, Cafe 1, Restaurant 1
- Cultural: Attraction 2~3, Cafe 1, Restaurant 2

마지막 날은 Accommodation 귀환 없음.
순수 JSON만 출력하세요. 마크다운 코드블록(```) 사용 금지.
"""

# ========== 3. 유틸 함수 ==========
def get_date_info(date_str):
    """날짜 문자열로부터 요일, 시즌, 주말 여부 계산"""
    weekday_map = {0: "월", 1: "화", 2: "수", 3: "목", 4: "금", 5: "토", 6: "일"}
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    month = date_obj.month
    weekday_idx = date_obj.weekday()
    travel_day = weekday_map[weekday_idx]
    season = "peak" if month in [7, 8, 12, 1] else "offpeak"
    is_weekend = weekday_idx in [4, 5]  # 금(4), 토(5)
    return travel_day, season, is_weekend


# ========== 4. 일정 생성 함수 ==========
def generate_itinerary(user_profile: dict):
    start_date = datetime.strptime(user_profile['start_date'], "%Y-%m-%d")
    date_info_list = []

    for i in range(user_profile['duration_days']):
        current_date = start_date + timedelta(days=i)
        date_str = current_date.strftime("%Y-%m-%d")
        travel_day, season, is_weekend = get_date_info(date_str)

        date_info_list.append({
            "day": i + 1,
            "date": date_str,
            "travel_day": travel_day,
            "season": season,
            "is_weekend": is_weekend
        })

    date_info_text = "\n".join([
        f"Day {d['day']}: {d['date']} ({d['travel_day']}) - season: {d['season']}, weekend: {d['is_weekend']}"
        for d in date_info_list
    ])

    user_prompt = f"""
    유저 입력:
    - 전체 예산: {user_profile['budget']}
    - 여행 일수: {user_profile['duration_days']}
    - 여행 스타일: {user_profile['travel_style']}
    - 나이: {user_profile['age']}
    - 성별: {user_profile['gender']}
    - 출발일: {user_profile['start_date']}

    날짜별 정보:
    {date_info_text}

    위 정보를 바탕으로 JSON 일정 생성.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )

    result_text = response.choices[0].message.content.strip()
    if result_text.startswith("```"):
        lines = result_text.split('\n')
        result_text = '\n'.join(lines[1:-1])

    try:
        return json.loads(result_text)
    except Exception as e:
        print(f"⚠️ JSON 파싱 실패: {e}")
        print(result_text)
        return None


# ========== 5. 메인 실행 ==========
if __name__ == "__main__":
    # CSV 파일 경로
    csv_path = r"C:\Users\changjin\workspace\lab\pln\data_set\5_user_info.csv"

    # 결과 저장 폴더 (하나만 사용)
    base_output_dir = r"C:\Users\changjin\workspace\lab\pln\plan\all_user\1000_user_plan"
    os.makedirs(base_output_dir, exist_ok=True)

    # CSV 로드
    df = pd.read_csv(csv_path)

    # 각 유저별로 실행
    for _, row in df.iterrows():
        user_id = str(row['user_id'])
        print(f"\n🔄 {user_id} 일정 생성 중...")

        user_profile = {
            "budget": int(row['budget']),
            "duration_days": int(row['duration_days']),
            "travel_style": row['travel_style'],
            "age": int(row['age']),
            "gender": row['gender'],
            "start_date": row['start_date']
        }

        itinerary = generate_itinerary(user_profile)
        if itinerary:
            # 유저별 JSON 파일만 생성 (폴더 없음)
            output_path = os.path.join(base_output_dir, f"{user_id}_itinerary.json")
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(itinerary, f, ensure_ascii=False, indent=2)

            print(f"✅ {user_id} 일정 생성 완료 → {output_path}")
        else:
            print(f"❌ {user_id} 일정 생성 실패")
