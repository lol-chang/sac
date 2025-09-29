import json

# 경로 설정
INPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[8]llm_gen_likes.jsonl"
)
OUTPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[9]collect_likes.jsonl"
)


def merge_and_rename_keys(input_path, output_path):
    """
    1. reviews_attraction 내부의 likes/dislikes를 최상위로 병합
    2. like → likes, unlike → dislikes로 키 이름 변경
    """

    with open(input_path, "r", encoding="utf-8") as infile, open(
        output_path, "w", encoding="utf-8"
    ) as outfile:

        for line in infile:
            if not line.strip():
                continue

            data = json.loads(line)

            # 1단계: 최상위 필드가 없을 경우 초기화
            data.setdefault("like", [])
            data.setdefault("unlike", [])

            # Set으로 중복 제거하면서 병합
            like_set = set(data["like"])
            unlike_set = set(data["unlike"])

            # reviews_attraction 내부의 likes/dislikes 합치기
            for review in data.get("reviews_attraction", []):
                for like_item in review.get("likes", []):
                    like_set.add(like_item)
                for dislike_item in review.get("dislikes", []):
                    unlike_set.add(dislike_item)

            # 2단계: 키 이름 변경 및 업데이트
            data["likes"] = list(like_set)
            data["dislikes"] = list(unlike_set)

            # 기존 키 삭제
            if "like" in data:
                del data["like"]
            if "unlike" in data:
                del data["unlike"]

            # 결과 저장
            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"✅ 완료! 병합 및 키 변경된 파일 저장됨: {output_path}")


if __name__ == "__main__":
    merge_and_rename_keys(INPUT_PATH, OUTPUT_PATH)
