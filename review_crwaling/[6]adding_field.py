import json
import uuid  # PK 생성용

# 입력/출력 파일 경로
INPUT_FILE  = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[5-2]all_places_for_category copy.jsonl"
OUTPUT_FILE = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[6]data.jsonl"

def enhance_jsonl(input_file, output_file):
    """category → sub_category 교체 및 새 필드 추가"""
    with open(input_file, "r", encoding="utf-8") as fin, \
         open(output_file, "w", encoding="utf-8") as fout:

        for line in fin:
            try:
                obj = json.loads(line)

                # 1. category → sub_category
                if "category" in obj:
                    obj["sub_category"] = obj.pop("category")

                # 2. 기본 category 값 넣기
                obj["category"] = "음식점"

                # 3. 출처 (영문)
                obj["source"] = "Naver"

                # 4. all_review_count = visiter_review_count + blog_review_count
                v_cnt = obj.get("visiter_review_count") or 0
                b_cnt = obj.get("blog_review_count") or 0
                obj["all_review_count"] = int(v_cnt) + int(b_cnt)

                # 5. url
                pid = obj.get("place_id")
                if pid:
                    obj["url"] = f"https://m.place.naver.com/restaurant/{pid}/review/visitor?entry=ple&reviewSort=recent"
                else:
                    obj["url"] = None

                # 6. like/unlike
                obj["like"] = []
                obj["unlike"] = []

                # 7. 주소, 위도, 경도
                obj["address"] = None
                obj["latitude"] = None
                obj["longitude"] = None

                # 8. PK (uuid 사용)
                obj["id"] = str(uuid.uuid4())

                # 저장
                fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

            except Exception as e:
                print("JSON parse error:", e)

    print(f"✅ 완료: {output_file} 에 저장됨")


# 실행
if __name__ == "__main__":
    enhance_jsonl(INPUT_FILE, OUTPUT_FILE)
