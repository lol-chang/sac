import json

INPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[12]llm_likes_results.jsonl"
OUTPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[13]data.jsonl"

def merge_likes_dislikes(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:

        for line in infile:
            if not line.strip():
                continue

            data = json.loads(line)

            # 최상위 필드가 없을 경우 초기화
            data.setdefault("like", [])
            data.setdefault("unlike", [])

            like_set = set(data["like"])
            unlike_set = set(data["unlike"])

            # reviews_attraction 내부의 likes/dislikes 합치기
            for review in data.get("reviews_attraction", []):
                for like_item in review.get("likes", []):
                    like_set.add(like_item)
                for dislike_item in review.get("dislikes", []):
                    unlike_set.add(dislike_item)

            data["like"] = list(like_set)
            data["unlike"] = list(unlike_set)

            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"✅ 완료! 병합된 파일 저장됨: {output_path}")

if __name__ == "__main__":
    merge_likes_dislikes(INPUT_PATH, OUTPUT_PATH)
