import json

# 경로 설정
INPUT_PATH = (
    r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[9]collect_likes.jsonl"
)
OUTPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[11]_data_with_all_count.jsonl"


def add_all_review_count(input_path, output_path):
    """visiter_review_count + blog_review_count = all_review_count 추가"""

    with open(input_path, "r", encoding="utf-8") as infile, open(
        output_path, "w", encoding="utf-8"
    ) as outfile:

        for line in infile:
            if not line.strip():
                continue

            data = json.loads(line)

            # 방문자 리뷰 수와 블로그 리뷰 수 가져오기
            visiter_count = data.get("visiter_review_count")
            blog_count = data.get("blog_review_count")

            # all_review_count 계산
            all_count = 0
            if visiter_count is not None and isinstance(visiter_count, (int, float)):
                all_count += int(visiter_count)
            if blog_count is not None and isinstance(blog_count, (int, float)):
                all_count += int(blog_count)

            # all_review_count 필드 추가
            data["all_review_count"] = all_count if all_count > 0 else None

            # 결과 저장
            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

    print(f"완료! all_review_count가 추가된 파일 저장됨: {output_path}")


if __name__ == "__main__":
    add_all_review_count(INPUT_PATH, OUTPUT_PATH)
