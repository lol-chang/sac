# ===================== Colab Flat Script (Budget-Max Version) =====================

import json
from typing import Dict

# --------------------------------------------------------------------
# PARAMS — 입력 파라미터 (설명)
# --------------------------------------------------------------------
# start_label / start_id : 출발 노드(Label, id)
# end_label / end_id     : 도착 노드(Label, id). 비어있으면 마지막 스텝에서도 도착지 패널티를 사용하지 않음
# transport              : 'car' | 'walk' (거리 패널티 방식)
# w_dist                 : 이동 거리 패널티 가중치
# w_branch               : 이름이 '…점'으로 끝나면 감점
# w_budget               : "스텝별 목표 예산에 가까울수록" 가산점의 가중치
# exclude_ids            : 이미 방문/배제할 id(place_id 등) 목록
# exclude_cells          : 이미 방문/배제할 cell_key 목록
# budget_per_day         : 1일 예산(숙소비 포함)
# travel_day             : '일'~'토' (영업시간 필터용)
#
# season                 : 'peak' | 'offpeak' (숙소비 계산에 사용)
# stay_is_weekend        : True/False/None — None이면 travel_day가 '금'/'토'이면 True
#   └ 숙소 노드 속성 가정:
#      - peak_weekend_price_avg, peak_weekday_price_avg
#      - offpeak_weekend_price_avg, offpeak_weekday_price_avg
#
# place_plan             : [{category, count, time}, ...]
#   └ category ∈ {'Restaurant','Cafe','Attraction'}
#   └ Cafe는 category/name에 '카페' 포함으로 판별
#   └ count: 각 스텝 후보 개수
#   └ time : 'HH:MM' (영업시간 필터에 사용)
# --------------------------------------------------------------------

PARAMS = {
  "start_label": "Accommodation",
  "start_id": "3013417",

  "end_label": "",          # 마지막 스텝 도착지 미지정이면 빈 문자열
  "end_id": "",

  "transport": "car",       # 'car' | 'walk'
  "w_dist": 1.0,
  "w_branch": 0.4,
  "w_budget": 0.8,

  "exclude_ids": ["37072842","1133159525","36541810"],
  "exclude_cells": [],

  "budget_per_day": 400000,
  "travel_day": "토",

  "season": "offpeak",
  "stay_is_weekend": None,  # None이면 '금','토' → True

  "place_plan": [
    {"category":"Restaurant","count":1,"time":"08:00"},
    {"category":"Cafe","count":1,"time":"10:00"},
    {"category":"Restaurant","count":1,"time":"12:00"},
    {"category":"Attraction","count":1,"time":"14:00"},
    {"category":"Cafe","count":1,"time":"16:00"},
    {"category":"Restaurant","count":1,"time":"18:00"}
  ]
}

# ---------- :param 블록 생성 ----------
def _cy(v):
    if v is None:
        return "null"
    if isinstance(v, str):
        return "'" + v.replace("'", "\\'") + "'"
    return json.dumps(v, ensure_ascii=False)

def to_param_block(p: Dict) -> str:
    keys = [
        "start_label","start_id","end_label","end_id",
        "transport","w_dist","w_branch","w_budget",
        "exclude_ids","exclude_cells",
        "budget_per_day","travel_day","season","stay_is_weekend",
    ]
    lines = [f":param {k} => {_cy(p.get(k))};" for k in keys]
    plan = "[" + ", ".join(
        [ "{category: " + _cy(s['category']) +
          ", count: " + str(s['count']) +
          ", time: " + _cy(s['time']) + "}" for s in p["place_plan"] ]
    ) + "]"
    lines.append(f":param place_plan => {plan};")
    return "\n".join(lines)

# ---------- Cypher 템플릿 (예산 소진 가산점 포함) ----------
CYPHER_TEMPLATE = """
// 1) 출발 노드
CALL apoc.cypher.run(
  'MATCH (n:' + $start_label + ' {id: $id}) RETURN n AS node',
  {id: $start_id}
) YIELD value
WITH value.node AS start

// 2) 도착 노드 (옵션)
CALL apoc.do.when(
  $end_id IS NULL OR $end_id = '',
  'RETURN null AS node',
  'MATCH (n:' + $end_label + ' {id: $id}) RETURN n AS node',
  {id: $end_id}
) YIELD value
WITH start, value.node AS dest,
     $place_plan AS steps,
     $exclude_ids AS prev_ids,
     $exclude_cells AS prev_cells,
     $transport AS transport,
     toFloat($w_dist)   AS w_dist,
     toFloat($w_branch) AS w_branch,
     toFloat($w_budget) AS w_budget,
     $budget_per_day AS budget_per_day,
     $travel_day AS day,
     $season AS season,
     $stay_is_weekend AS stay_weekend_raw

// 2-2) 주말 여부 확정
WITH start, dest, steps, prev_ids, prev_cells,
     transport, w_dist, w_branch, w_budget,
     budget_per_day, day, season,
     coalesce(stay_weekend_raw, day IN ['금','토']) AS stay_is_weekend

// 2-3) 숙소비 + idxs
WITH start, dest, steps, prev_ids, prev_cells,
     transport, w_dist, w_branch, w_budget,
     budget_per_day, day, season, stay_is_weekend,
     CASE
       WHEN 'Accommodation' IN labels(start) THEN
         CASE
           WHEN season = 'peak'    AND  stay_is_weekend THEN coalesce(toInteger(start.peak_weekend_price_avg), 0)
           WHEN season = 'peak'    AND NOT stay_is_weekend THEN coalesce(toInteger(start.peak_weekday_price_avg), 0)
           WHEN season = 'offpeak' AND  stay_is_weekend THEN coalesce(toInteger(start.offpeak_weekend_price_avg), 0)
           ELSE coalesce(toInteger(start.offpeak_weekday_price_avg), 0)
         END
       ELSE 0
     END AS lodging_cost,
     range(0, size(steps)-1) AS idxs

// 3) 반복
UNWIND idxs AS i
WITH i, steps[i] AS step, steps, start, dest, day,
     prev_ids, prev_cells, transport, w_dist, w_branch, w_budget,
     budget_per_day, lodging_cost

// 4) 추천 서브쿼리
CALL {
  WITH i, step, steps, start, dest, day,
       prev_ids, prev_cells, transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost

  MATCH (p)
  WHERE
    (
      // ✅ Cafe: sub_category에 "카페" 포함
      (step.category = 'Cafe' AND (
         p:Restaurant OR (p.category IS NOT NULL AND p.category CONTAINS '음식')
      ) AND (p.sub_category IS NOT NULL AND p.sub_category CONTAINS '카페'))

      OR

      // ✅ Restaurant: sub_category에 "카페" 없는 음식점
      (step.category = 'Restaurant' AND (
         p:Restaurant OR (p.category IS NOT NULL AND p.category CONTAINS '음식')
      ) AND (p.sub_category IS NULL OR NOT p.sub_category CONTAINS '카페'))

      OR

      // ✅ Attraction
      (step.category = 'Attraction' AND (
         p:Attraction OR
         (p.category IS NOT NULL AND (
            p.category CONTAINS '명소' OR
            p.category CONTAINS '관광' OR
            p.category CONTAINS '박물관' OR
            p.category CONTAINS '미술관' OR
            p.category CONTAINS '체험'
         ))
      ))
    )
    AND NOT coalesce(p.id, p.place_id, p.festival_title) IN prev_ids
    AND NOT p.cell_key IN prev_cells
    AND p.location IS NOT NULL

  // 영업시간 필터
  WITH p, i, step, steps, start, dest, day,
       transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost,
       [h IN coalesce(p.opening_hours, []) WHERE h STARTS WITH day + ':' AND h CONTAINS ' - '] AS day_rows
  WITH p, i, step, steps, start, dest, day,
       transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost,
       CASE WHEN size(day_rows)=0 THEN NULL ELSE split( split(day_rows[0], ': ')[1], ' - ') END AS hh
  WITH p, i, step, steps, start, dest, day,
       transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost,
       CASE WHEN hh IS NULL THEN NULL ELSE time(hh[0]) END AS open_t,
       CASE WHEN hh IS NULL THEN NULL ELSE time(hh[1]) END AS close_t
  WHERE open_t IS NULL OR (time(step.time) >= open_t AND time(step.time) <= close_t - duration('PT30M'))

  // 거리 계산 (start 기준)
  OPTIONAL MATCH (start)-[r1:NEAR]-(p) WHERE r1.bridge IS NULL
  WITH p, i, step, steps, transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost,
       CASE WHEN r1 IS NULL THEN 99999 ELSE r1.distance_m / 1000.0 END AS dist_from_start,
       coalesce(p.place_name, p.name) AS pname,
       p.sub_category AS sub_category,
       size(steps) AS total_steps,
       CASE
         WHEN step.category = 'Attraction' THEN coalesce(toInteger(p.entrance_fee), 0)
         WHEN step.category IN ['Restaurant','Cafe'] THEN
           CASE WHEN p.avg_price IS NULL THEN 0
                ELSE toInteger(round(toFloat(p.avg_price))) * 2 END
         ELSE 0
       END AS cost

  WHERE cost <= (budget_per_day - lodging_cost)

  // per-step cap
  WITH p, i, step, cost, dist_from_start, pname, sub_category,
       transport, w_dist, w_branch, w_budget,
       budget_per_day, lodging_cost, total_steps,
       (toFloat(budget_per_day - lodging_cost) / toFloat(total_steps)) AS per_step_cap

  WITH p, i, step, cost, dist_from_start, pname, sub_category,
       transport, w_dist, w_branch, w_budget, per_step_cap,
       abs(1.0 - (CASE WHEN per_step_cap > 0 THEN cost / per_step_cap ELSE 1.0 END)) AS budget_diff

  // 이동/지점 패널티 + 예산 보너스
  WITH p, i, step, cost, pname, sub_category,
       (CASE
         WHEN transport='walk' THEN w_dist*(dist_from_start^1.2)
         ELSE w_dist*CASE WHEN dist_from_start <= 7 THEN 0 ELSE (dist_from_start-7) END
       END) AS move_penalty,
       CASE WHEN pname IS NOT NULL AND trim(toString(pname)) ENDS WITH '점'
            THEN w_branch ELSE 0 END AS branch_penalty,
       (w_budget * (1.0 - budget_diff)) AS budget_bonus

  // 최종 점수
  WITH i, step, cost, p, sub_category,
       (budget_bonus - move_penalty - branch_penalty) AS score

  ORDER BY score DESC, cost DESC
  WITH step, collect({
    index: i,
    id: coalesce(p.place_id, p.id, p.festival_title),
    label: labels(p)[0],
    name: coalesce(p.place_name, p.name),
    cell_key: p.cell_key,
    cost: cost,
    score: score,
    sub_category: coalesce(sub_category, "")
  }) AS ranked
  RETURN ranked[0..toInteger(step.count)] AS selected
}

// 5) 결과
WITH apoc.coll.flatten(collect(selected)) AS raw_results
UNWIND raw_results AS result
RETURN
  result.index,
  result.id,
  result.label,
  result.name,
  result.cell_key,
  result.cost,
  round(result.score, 2) AS score,
  result.sub_category
ORDER BY result.index ASC

""".strip()

# ---------- 출력 ----------
param_block = to_param_block(PARAMS)
print("=== PARAM BLOCK ===")
print(param_block)
print("\n=== CYPHER QUERY ===\n")
print(CYPHER_TEMPLATE)

# ---- 실제 DB 실행은 원할 때만 (주석 해제) ----
# from neo4j import GraphDatabase
# driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j","password"))
# with driver.session() as sess:
#     res = sess.run(param_block + "\n" + CYPHER_TEMPLATE)
#     for r in res:
#         print(r)
