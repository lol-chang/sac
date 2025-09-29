import json
import csv

# -------------------
# 경로 설정
# -------------------
INPUT_MAIN = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[12-2]entrance_fee_fixed.jsonl"
INPUT_LIKES = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[999]each_place_likes.jsonl"
OUTPUT_PATH = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[13]place.csv"

# -------------------
# 제외할 필드들
# -------------------
EXCLUDE_FIELDS = {"id", "reviews_attraction", "rating", "likes", "dislikes"}

# -------------------
# 내가 원하는 필드 순서
# -------------------
PRIORITY_FIELDS = [
    "place_name",
    "place_id",
    "description",
    "category",
    "sub_category",
    "address",
    "latitude",
    "longitude",
    "url",
    "entrance_fee",
    "store_hours",
    "source",
    "visiter_review_count",
    "blog_review_count",
    "all_review_count",
    "like",
    "dislike",
]


def normalize_row(data: dict) -> dict:
    """store_hours 처리 및 불필요한 필드 제거"""
    row = {}
    for k, v in data.items():
        if k in EXCLUDE_FIELDS:
            continue
        if k == "store_hours" and isinstance(v, list):
            row[k] = " | ".join(v) if v else None
        elif k == "entrance_fee" and isinstance(v, list):  # 리스트 → 문자열
            row[k] = " | ".join(v) if v else None
        else:
            row[k] = v
    return row


def load_likes_map(filepath: str):
    """place_id → {like, dislike} 매핑"""
    mapping = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            pid = str(rec.get("place_id"))
            mapping[pid] = {
                "like": rec.get("like", []),
                "dislike": rec.get("dislike", []),
            }
    return mapping


def jsonl_to_csv(input_main, input_likes, output_path):
    rows = []
    all_keys = set()

    likes_map = load_likes_map(input_likes)

    with open(input_main, "r", encoding="utf-8") as infile:
        for line in infile:
            if not line.strip():
                continue
            data = json.loads(line)
            normalized = normalize_row(data)

            pid = str(normalized.get("place_id"))
            if pid in likes_map:
                # ✅ 리스트 그대로 JSON 문자열로 저장
                normalized["like"] = json.dumps(
                    likes_map[pid]["like"], ensure_ascii=False
                )
                normalized["dislike"] = json.dumps(
                    likes_map[pid]["dislike"], ensure_ascii=False
                )
            else:
                normalized["like"] = json.dumps([], ensure_ascii=False)
                normalized["dislike"] = json.dumps([], ensure_ascii=False)

            rows.append(normalized)
            all_keys.update(normalized.keys())

    remaining_fields = [k for k in sorted(all_keys) if k not in PRIORITY_FIELDS]
    fieldnames = PRIORITY_FIELDS + remaining_fields

    with open(output_path, "w", newline="", encoding="utf-8-sig") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"✅ CSV 저장 완료: {output_path}")


if __name__ == "__main__":
    jsonl_to_csv(INPUT_MAIN, INPUT_LIKES, OUTPUT_PATH)
