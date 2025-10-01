import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import traceback
from weaviate.classes import query as wq

# --- 1. 환경 변수 로드 및 클라이언트 연결 ---
print("🔐 .env 환경변수 로딩 중...")
load_dotenv()

api_key = os.getenv("WEAVIATE_API_KEY")
cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")

client = weaviate.connect_to_weaviate_cloud(
    cluster_url=cluster_url,
    auth_credentials=AuthApiKey(api_key)
)
print("✅ Weaviate 클러스터 연결 완료\n")

try:
    # --- 2. 컬렉션 객체 로드 ---
    collection = client.collections.get("Place")
    print("📦 'Place' 컬렉션 불러오기 완료\n")

    # --- 3. 샘플 데이터 50개 중 카테고리별로 예시 찾기 ---
    print("🔎 카테고리별 대표 예시 추출 중 (관광지, 음식점, 숙소)...")
    sample_objs = collection.query.fetch_objects(limit=50).objects

    targets = {
        "관광지": None,
        "음식점": None,
        "Accommodation": None
    }

    for obj in sample_objs:
        cat = obj.properties["category"]
        if cat in targets and targets[cat] is None:
            targets[cat] = obj
        if all(targets.values()):
            break

    print("✅ 카테고리별 대표 예시 선택 완료:")
    for cat, obj in targets.items():
        print(f"  • {cat}: {obj.properties['name']} (place_id: {obj.properties['place_id']})")
    print()

    # --- 4. 유사도 추천 함수 정의 ---
    def recommend_similar_places(base_obj, category_name):
        print(f"\n📌 [{category_name}] '{base_obj.properties['name']}'와 유사한 장소 3개 추천")
        print(f"    place_id: {base_obj.properties['place_id']}")
        print(f"    sub_category: {base_obj.properties['sub_category']}")

        # 기준 객체의 벡터 가져오기
        base_vector_obj = collection.query.fetch_object_by_id(
            base_obj.uuid, include_vector=True
        )
        base_vector = base_vector_obj.vector.get("default")

        if not base_vector:
            print("⚠️ 벡터 정보 없음 - 스킵")
            return

        # 같은 카테고리 내에서만 유사 벡터 검색
        results = collection.query.near_vector(
            near_vector=base_vector,
            limit=6,  # 자기 자신 포함 가능성이 있으니 넉넉히
            return_metadata=["distance"],
            include_vector=True,
            filters=wq.Filter.by_property("category").equal(category_name)
        )

        count = 0
        for obj in results.objects:
            if obj.uuid == base_obj.uuid:
                continue  # 자기 자신은 제외
            count += 1
            print(f"\n[{count}] {obj.properties['name']}")
            print(f"    카테고리: {obj.properties['category']}")
            print(f"    sub_category: {obj.properties['sub_category']}")
            print(f"    place_id: {obj.properties['place_id']}")
            print(f"    📐 유사도 거리: {obj.metadata.distance:.4f}")

            # 직접 코사인 유사도 계산
            try:
                obj_vector = obj.vector["default"]
                sim = cosine_similarity([base_vector], [obj_vector])[0][0]
                print(f"    ✅ 코사인 유사도 (직접 계산): {sim:.4f}")
            except Exception as e:
                print(f"    ⚠️ 벡터 정보 없음 ({e})")

            if count >= 3:
                break

    # --- 5. 카테고리별 유사 장소 추천 실행 ---
    for cat, obj in targets.items():
        recommend_similar_places(obj, cat)

except Exception as e:
    print("\n❌ 에러 발생:")
    traceback.print_exc()

finally:
    client.close()
    print("\n🔒 연결 종료 완료")
