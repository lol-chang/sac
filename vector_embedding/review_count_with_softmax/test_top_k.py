import os
import json
import pickle
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes import query as wq

# ========== 1. 환경 변수 및 클라이언트 연결 ==========
print("🔐 환경 변수 로딩...")
load_dotenv()

api_key = os.getenv("WEAVIATE_API_KEY")
cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=AuthApiKey(api_key)
)
print("✅ Weaviate 연결 완료\n")

collection = client.collections.get("Place")

# ========== 2. 모델 로드 ==========
model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# ========== 3. 유저 데이터 로드 ==========
user_path = r"C:\Users\changjin\workspace\lab\pln\data_set\1_user_info.csv"
user_df = pd.read_csv(user_path)

user = user_df.iloc[0]  # 첫 번째 유저만 테스트
like_keywords = eval(user["like_keywords"])  # 문자열 -> 리스트 변환
dislike_keywords = eval(user["dislike_keywords"])

print("👤 User:", user["user_id"])
print("   👍 like:", like_keywords)
print("   👎 dislike:", dislike_keywords)

# 벡터화
user_like_vec = model.encode(" ".join(like_keywords), convert_to_numpy=True)
user_dislike_vecs = [model.encode(kw, convert_to_numpy=True) for kw in dislike_keywords]

# ========== 4. 추천 함수 ==========
def rerank_with_penalty(category_name, top_k=30, alpha=1.0, beta=0.5, dislike_threshold=0.75):
    print(f"\n🏷️ 카테고리: {category_name} (Top-{top_k})")

    # 1차 후보군 (like 기반)
    results = collection.query.near_vector(
        near_vector=user_like_vec.tolist(),
        limit=top_k*3,  # 여유있게 뽑음
        return_metadata=["distance"],
        include_vector=True,
        filters=wq.Filter.by_property("category").equal(category_name)
    )

    scored = []
    for obj in results.objects:
        like_sim = 1 - obj.metadata.distance  # 코사인 유사도

        # dislike 비교
        place_dislike_vec = obj.properties.get("dislike_embedding", [])
        max_dislike_sim = 0
        if place_dislike_vec:
            sims = [
                cosine_similarity([ud], [place_dislike_vec])[0][0]
                for ud in user_dislike_vecs if len(ud) > 0
            ]
            max_dislike_sim = max(sims) if sims else 0

        # 하드 필터링
        if max_dislike_sim > dislike_threshold:
            continue

        # 점수 계산 (like - dislike)
        final_score = alpha * like_sim - beta * max_dislike_sim
        scored.append((obj, final_score, like_sim, max_dislike_sim))

    # 점수순 정렬 후 Top-K
    scored.sort(key=lambda x: x[1], reverse=True)
    scored = scored[:top_k]

    # 출력
    for i, (obj, score, like_sim, dis_sim) in enumerate(scored, 1):
        print(f"[{i}] {obj.properties.get('name','')}")
        print(f"    place_id: {obj.properties.get('place_id')}")
        print(f"    sub_category: {obj.properties.get('sub_category')}")
        print(f"    👍 like_sim: {like_sim:.4f}, 👎 dislike_sim: {dis_sim:.4f}")
        print(f"    📊 final_score: {score:.4f}\n")

    return scored

# ========== 5. 카테고리별 추천 ==========
categories = ["Accommodation", "카페", "음식점", "관광지"]
results_by_cat = {}

for cat in categories:
    results_by_cat[cat] = rerank_with_penalty(cat, top_k=30)

# ========== 6. 연결 종료 ==========
client.close()
print("\n🔒 연결 종료 완료")
