import os
from dotenv import load_dotenv
import weaviate
from weaviate.auth import AuthApiKey
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import traceback
from weaviate.classes import query as wq


# ===============================
# 1. 환경 설정 및 클라이언트 연결
# ===============================
def connect_weaviate():
    """Weaviate 클러스터 연결"""
    print("🔐 .env 환경변수 로딩 중...")
    load_dotenv()

    api_key = os.getenv("WEAVIATE_API_KEY")
    cluster_url = os.getenv("WEAVIATE_CLUSTER_URL")

    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=cluster_url,
        auth_credentials=AuthApiKey(api_key)
    )
    print("✅ Weaviate 클러스터 연결 완료\n")
    return client


# ===============================
# 2. 대표 샘플 객체 선택
# ===============================
def pick_representatives(collection, categories=("관광지", "음식점", "Accommodation")):
    """샘플 데이터에서 카테고리별 대표 객체 추출"""
    print("🔎 카테고리별 대표 예시 추출 중...")
    sample_objs = collection.query.fetch_objects(limit=50).objects

    targets = {cat: None for cat in categories}
    for obj in sample_objs:
        cat = obj.properties["category"]
        if cat in targets and targets[cat] is None:
            targets[cat] = obj
        if all(targets.values()):
            break

    print("✅ 카테고리별 대표 예시 선택 완료:")
    for cat, obj in targets.items():
        print(f"  • {cat}: {obj.properties['name']} "
              f"(place_id: {obj.properties['place_id']}, sub_category: {obj.properties['sub_category']})")
    print()
    return targets


# ===============================
# 3. 유사 장소 추천
# ===============================
def recommend_similar_places(collection, base_obj, category_name):
    """같은 카테고리 + 같은 서브카테고리 내에서 유사 장소 추천"""
    base_subcat = base_obj.properties['sub_category']

    print(f"\n📌 [{category_name}] '{base_obj.properties['name']}'와 동일한 서브카테고리('{base_subcat}') 내 유사한 장소 추천")
    print(f"    • place_id: {base_obj.properties['place_id']}")
    print(f"    • sub_category: {base_subcat}")

    # 기준 객체 벡터 가져오기
    base_vector_obj = collection.query.fetch_object_by_id(
        base_obj.uuid, include_vector=True
    )
    base_vector = base_vector_obj.vector.get("default")
    if not base_vector:
        print("⚠️ 기준 벡터 정보 없음 - 스킵")
        return

    # 필터: 같은 카테고리 + 같은 서브카테고리
    filters = (
        wq.Filter.by_property("category").equal(category_name)
        & wq.Filter.by_property("sub_category").equal(base_subcat)
    )

    # 유사도 검색
    results = collection.query.near_vector(
        near_vector=base_vector,
        limit=6,  # 자기 자신 포함될 수 있어 넉넉히
        return_metadata=["distance"],
        include_vector=True,
        filters=filters
    )

    # 결과 출력
    count = 0
    for obj in results.objects:
        if obj.uuid == base_obj.uuid:  # 자기 자신 제외
            continue
        count += 1

        name = obj.properties['name']
        subcat = obj.properties['sub_category']
        place_id = obj.properties['place_id']
        dist = obj.metadata.distance

        print(f"\n[{count}] {name}")
        print(f"    • 카테고리: {category_name}")
        print(f"    • sub_category: {subcat}")
        print(f"    • place_id: {place_id}")
        print(f"    • 📐 유사도 거리: {dist:.4f}")

        # 직접 코사인 유사도 계산
        try:
            obj_vector = obj.vector["default"]
            sim = cosine_similarity([base_vector], [obj_vector])[0][0]
            print(f"    • ✅ 코사인 유사도 (직접 계산): {sim:.4f}")
        except Exception as e:
            print(f"    • ⚠️ 벡터 정보 없음 ({e})")

        if count >= 3:
            break


# ===============================
# 4. 실행
# ===============================
if __name__ == "__main__":
    client = connect_weaviate()
    try:
        collection = client.collections.get("Place")
        print("📦 'Place' 컬렉션 불러오기 완료\n")

        # 카테고리별 대표 장소 선택
        targets = pick_representatives(collection)

        # 카테고리별 추천 실행
        for cat, obj in targets.items():
            recommend_similar_places(collection, obj, cat)

    except Exception as e:
        print("\n❌ 에러 발생:")
        traceback.print_exc()

    finally:
        client.close()
        print("\n🔒 연결 종료 완료")
