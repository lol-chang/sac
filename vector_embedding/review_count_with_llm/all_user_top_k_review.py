import os
import json
import numpy as np
import pandas as pd
import re
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes import query as wq
from tqdm import tqdm  # 🔹 진행률 표시

# ========== CONFIG ==========
CONFIG = {
    "USER_FILE": r"C:\\Users\\changjin\\workspace\\lab\\pln\\data_set\\1_user_info.csv",
    "DATA_DIR": r"C:\\Users\\changjin\\workspace\\lab\\pln\\data_set\\null_X",
    "OUTPUT_DIR": r"C:\\Users\\changjin\\workspace\\lab\\pln\\vector_embedding\\review_count_with_llm\\user_results",
    "TOP_K": 30
}

CATEGORY_FILES = {
    "Accommodation": "accommodations_fixed.csv",
    "카페": "cafe_fixed.csv",
    "음식점": "restaurants_fixed.csv",
    "관광지": "attractions_fixed.csv"
}

CATEGORY_TRANSLATE = {
    "Accommodation": "Accommodation",
    "카페": "Cafe",
    "음식점": "Restaurant",
    "관광지": "Attraction"
}

# ========== 1. 환경 변수 및 클라이언트 연결 ==========
load_dotenv()
api_key = os.getenv("WEAVIATE_API_KEY")
cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")
openai_key = os.getenv("OPENAI_API_KEY")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=AuthApiKey(api_key)
)
collection = client.collections.get("Place")
openai_client = OpenAI(api_key=openai_key)

print("✅ Weaviate 및 OpenAI 클라이언트 연결 완료\n")

# ========== 2. 모델 로드 ==========
print("🔧 SentenceTransformer 모델 로딩 중...")
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")
print("✅ 모델 로딩 완료\n")


# ========== 3. 후보 산출 ==========
def rerank_with_penalty(user_like_vec, user_dislike_vecs, category_name,
                        top_k=30, alpha=1.0, beta=0.5, dislike_threshold=0.75):
    print(f"🔍  {category_name} 후보 검색 중 (Weaviate near_vector)...")
    results = collection.query.near_vector(
        near_vector=user_like_vec.tolist(),
        limit=top_k * 4,
        return_metadata=["distance"],
        include_vector=True,
        filters=wq.Filter.by_property("category").equal(category_name),
        return_properties=["place_id", "name", "dislike_embedding"]
    )

    scored = []
    for obj in results.objects:
        like_sim = 1 - obj.metadata.distance
        place_dislike_vec = obj.properties.get("dislike_embedding", [])
        max_dislike_sim = 0
        if place_dislike_vec:
            sims = [
                cosine_similarity([ud], [place_dislike_vec])[0][0]
                for ud in user_dislike_vecs if len(ud) > 0
            ]
            max_dislike_sim = max(sims) if sims else 0

        if max_dislike_sim > dislike_threshold:
            continue

        sim_score = alpha * like_sim - beta * max_dislike_sim
        scored.append({
            "id": obj.properties.get("place_id"),
            "name": obj.properties.get("name"),
            "like_sim": float(like_sim),
            "dislike_sim": float(max_dislike_sim),
            "sim_score": float(sim_score)
        })

    print(f"✅  {category_name} 후보 {len(scored)}개 수집 완료\n")
    scored.sort(key=lambda x: x["sim_score"], reverse=True)
    return scored[:top_k]


# ========== 4. GPT 정렬 ==========
def gpt_sort_with_reviews(user_like, user_dislike, category_name, candidates, review_dict):
    print(f"🤖  GPT 순위 재정렬 요청 중... ({category_name})")

    data_for_gpt = []
    for c in candidates:
        rid = c["id"]
        rc = review_dict.get(rid, 0)

        # ✅ NaN 안전 처리
        if pd.isna(rc):
            rc = 0

        data_for_gpt.append({
            "id": rid,
            "name": c["name"],
            "like_sim": round(c["like_sim"], 4),
            "dislike_sim": round(c["dislike_sim"], 4),
            "review_count": int(rc)
        })

    prompt = f"""
You are a ranking assistant for travel places.

User preferences:
- Likes: {user_like}
- Dislikes: {user_dislike}

Each place below has:
- a like similarity score (higher = better match)
- a dislike similarity score (higher = worse match)
- a review count (higher = more popular)

Re-rank these places **only by order**, without changing or generating new fields.
Sort from most to least suitable for the user.

Return ONLY a JSON array of IDs, like this:
[3013409, 10062156, 10045242, 3003412]

Here are the candidates:
{json.dumps(data_for_gpt, ensure_ascii=False, indent=2)}
"""

    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",  # ✅ 빠르고 저렴한 모델
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    content = response.choices[0].message.content.strip()
    json_match = re.search(r"\[.*\]", content, re.DOTALL)

    if json_match:
        try:
            sorted_ids = json.loads(json_match.group(0))
        except Exception:
            sorted_ids = []
    else:
        sorted_ids = []

    if not sorted_ids:
        print("⚠️ GPT 응답 파싱 실패 — 원문 출력 ↓")
        print(content[:500])
    else:
        print(f"✅ GPT 정렬 완료 ({len(sorted_ids)}개)\n")

    return sorted_ids


# ========== 5. 유저별 전체 처리 ==========
user_df = pd.read_csv(CONFIG["USER_FILE"])
os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

for idx, user in enumerate(user_df.itertuples(), start=1):
    user_id = user.user_id
    like_keywords = eval(user.like_keywords)
    dislike_keywords = eval(user.dislike_keywords)

    print("=" * 60)
    print(f"👤 Processing User {idx}/{len(user_df)} → {user_id}")
    print(f"   👍 like: {like_keywords}")
    print(f"   👎 dislike: {dislike_keywords}")
    print("-" * 60)

    user_like_vec = model.encode(" ".join(like_keywords), convert_to_numpy=True)
    user_dislike_vecs = [model.encode(kw, convert_to_numpy=True) for kw in dislike_keywords]

    results_by_cat = {}

    for cat in CATEGORY_FILES.keys():
        candidates = rerank_with_penalty(user_like_vec, user_dislike_vecs, cat, top_k=CONFIG["TOP_K"])

        df = pd.read_csv(os.path.join(CONFIG["DATA_DIR"], CATEGORY_FILES[cat]))
        review_col = "review_count" if cat == "Accommodation" else "all_review_count"
        review_dict = dict(zip(df["id"], df[review_col]))

        sorted_ids = gpt_sort_with_reviews(
            like_keywords, dislike_keywords,
            CATEGORY_TRANSLATE[cat], candidates, review_dict
        )

        results_by_cat[CATEGORY_TRANSLATE[cat]] = [
            {"id": pid, "category": CATEGORY_TRANSLATE[cat]} for pid in sorted_ids
        ]

    out_path = os.path.join(CONFIG["OUTPUT_DIR"], f"{user_id}_recommendations.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results_by_cat, f, ensure_ascii=False, indent=2)

    print(f"💾 {user_id} 결과 저장 완료 → {out_path}\n")

client.close()
print("\n🔒 전체 유저 처리 완료 & 연결 종료")
