import os, json
from datetime import datetime, timedelta
from typing import Dict, List
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4o", 
    temperature=0.3,
    api_key=os.getenv("OPENAI_API_KEY")
)

# ===================== Neo4j 연결 =====================
class Neo4jConnection:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def execute_query(self, query, parameters):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]

# Neo4j 연결 설정
neo4j_conn = Neo4jConnection(
    uri="bolt://10.11.61.169:7687",
    user="neo4j",
    password="12345678"
)

# ===================== Cypher 쿼리 템플릿 =====================


# ===================== 프롬프트 =====================
SYSTEM_PROMPT = """
여행 일정 파라미터를 JSON으로 생성하세요.

# 규칙
1. budget_per_day = 전체예산 / 여행일수
2. 요일: 월~일, 시즌: 7,8,12,1월=peak/나머지=offpeak, 주말: 금토=true
3. place_plan은 아래 기준에 따라 생성 (보통 5~6개, 시간 포함)

# 연령대에 따른 일정 시간대
- 10~20대: 09:30~18:30
- 30~40대: 08:30~19:00
- 50대+: 08:00~18:30

# 스타일별 패턴
- Healing:
  - Cafe는 하루 1~2회 (아침, 오후, 저녁 중 선택)
  - Attraction은 가볍게 1~2회 (산책, 뷰포인트 등)
  - Restaurant는 2회 (점심, 저녁)

- Foodie:
  - Restaurant는 3회 (간식 포함 가능)
  - Cafe는 1~2회 (디저트, 브런치 용)
  - Attraction은 1~2회 (식사 중심 일정)

- Activity:
  - Attraction은 3~4회 (관광, 체험, 액티비티 중심)
  - Cafe/Restaurant는 간단히 2회 (식사 및 휴식용)
  - 야외 활동 후 적절한 식사 시간 고려

# 기타
- Restaurant는 조식/중식/석식 등의 용어 대신, 자연스러운 시간 (예: 08:30, 12:00 등)을 사용
- 마지막 날이 아니라면, place_plan 마지막엔 반드시 Accommodation 포함 (숙소 도착)

# 출력 (JSON만)
{
  "place_plan": [
    {"category": "Cafe/Attraction/Restaurant/Accommodation", "count": 1, "time": "HH:MM"}
  ]
}
"""

# ===================== 파라미터 생성 =====================


# ===================== 디버깅: DB 데이터 확인 및 숙소 ID 가져오기 =====================


from tabulate import tabulate
def test_db_connection():
    """Neo4j 연결 및 데이터 확인"""
    print("\n[DB 연결 테스트]")

    # 1. 숙소 확인
    query1 = """
        MATCH (a:Accommodation)
        WHERE a.id IS NOT NULL
        RETURN a.id as id, a.name as name
        LIMIT 5
    """
    results1 = neo4j_conn.execute_query(query1, {})
    print(f"\n▶ Accommodation 노드: {len(results1)}개")
    print(tabulate(results1, headers="keys", tablefmt="fancy_grid"))

    # 2. 레스토랑 확인
    query2 = """
        MATCH (r:Restaurant)
        WHERE r.place_id IS NOT NULL
        RETURN r.place_id as id, r.place_name as name
        LIMIT 5
    """
    results2 = neo4j_conn.execute_query(query2, {})
    print(f"\n▶ Restaurant 노드: {len(results2)}개")
    print(tabulate(results2, headers="keys", tablefmt="fancy_grid"))

    # 3. 관광지 확인
    query3 = """
        MATCH (a:Attraction)
        WHERE a.place_id IS NOT NULL
        RETURN a.place_id as id, a.place_name as name
        LIMIT 5
    """
    results3 = neo4j_conn.execute_query(query3, {})
    print(f"\n▶ Attraction 노드: {len(results3)}개")
    print(tabulate(results3, headers="keys", tablefmt="fancy_grid"))

    # 4. NEAR 관계 확인
    query4 = "MATCH ()-[r:NEAR]->() RETURN count(r) as count"
    results4 = neo4j_conn.execute_query(query4, {})
    print(f"\n▶ NEAR 관계: {results4[0]['count']}개\n")


# ===================== Cypher 실행 (실제 Neo4j) =====================
def execute_cypher(query: str, params: Dict) -> List[Dict]:
    """Neo4j에서 실제 쿼리 실행"""
    try:
        print(f"\n[Neo4j 쿼리 실행 중...]")
        print(f"파라미터 요약:")
        print(f"  - 출발: {params.get('start_label')} {params.get('start_id')}")
        print(f"  - 도착: {params.get('end_label')} {params.get('end_id')}")
        print(f"  - 일정: {len(params.get('place_plan', []))}개")
        print(f"  - 제외: {len(params.get('exclude_ids', []))}개 ID")
        
        results = neo4j_conn.execute_query(query, params)
        print(f"✅ 쿼리 성공: {len(results)}개 결과")
        return results
    
    except Exception as e:
        print(f"❌ Neo4j 쿼리 실패: {e}")
        return []

# ===================== 전체 여행 실행 =====================
def run_trip(user: Dict, accommodations: List[str]):
    """전체 여행 실행"""
    print(f"\n{'='*60}")
    print(f"여행 시작: {user['user_id']} ({user['duration_days']}일)")
    print(f"{'='*60}")
    
    visited_ids = []
    visited_cells = []
    all_results = []
    
    for day in range(1, user["duration_days"] + 1):
        start = accommodations[day-2] if day > 1 else None
        end = accommodations[day-1] if day < user["duration_days"] else None
        
        print(f"\n[{day}일차] 출발: {start or '없음'} → 도착: {end or '없음'}")
        
        # 1. 파라미터 생성
        params = generate_params(
            user=user,
            day_num=day,
            start_accommodation=start,
            end_accommodation=end,
            exclude_ids=visited_ids.copy(),
            exclude_cells=visited_cells.copy()
        )
        
        if not params:
            print(f"{day}일차 실패")
            break
        
        print(f"\n생성된 파라미터:")
        print(json.dumps(params, ensure_ascii=False, indent=2))
        
        # 2. Cypher 쿼리 실행 (실제 Neo4j)
        places = execute_cypher(CYPHER_TEMPLATE, params)
        
        if not places:
            print(f"⚠️ {day}일차: 장소를 찾지 못했습니다.")
            places = []
        
        # 결과 출력
        print(f"\n추천 장소:")
        for p in places:
            # 키 이름 안전하게 처리
            place_id = p.get('result.id') or p.get('id', 'N/A')
            place_name = p.get('result.name') or p.get('name', 'N/A')
            place_label = p.get('result.label') or p.get('label', 'N/A')
            place_cost = p.get('result.cost') or p.get('cost', 0)
            place_score = p.get('result.score') or p.get('score', 0)
            
            print(f"  - {place_name} ({place_label}) | 비용: {place_cost}원 | 점수: {place_score}")
        
        # 3. TODO: 벡터 DB 필터링 (나중에 추가)
        # places = filter_with_vector_db(places, user_preferences)
        
        all_results.append({
            "day": day,
            "params": params,
            "places": places
        })
        
        # 4. 방문 기록 누적 (안전하게 처리)
        for p in places:
            place_id = p.get('result.id') or p.get('id')
            cell_key = p.get('result.cell_key') or p.get('cell_key')
            
            if place_id:
                visited_ids.append(place_id)
            if cell_key:
                visited_cells.append(cell_key)
        if end:
            visited_ids.append(end)
        
        print(f"\n완료: {len(places)}개 장소")
    
    print(f"\n{'='*60}")
    print(f"여행 종료! 총 {len(visited_ids)}개 장소 방문")
    print(f"{'='*60}")
    
    # Neo4j 연결 종료
    neo4j_conn.close()
    
    return all_results

# ===================== 테스트 =====================
if __name__ == "__main__":
    user = {
        "user_id": "U0001",
        "travel_style": "Healing",
        "budget": 2200000,
        "duration_days": 3,
        "start_date": "2025-08-16",
        "gender": "Male",
        "age": 19
    }
    
    accommodations = get_accommodation_ids(count=3)
    
    results = run_trip(user, accommodations)
    
    # 저장
    with open(f"trip_{user['user_id']}.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n결과 저장: trip_{user['user_id']}.json")