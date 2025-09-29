import json

INPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[12-1]entrance_fee.jsonl"
OUTPUT_PATH = r"/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[12-2]entrance_fee_fixed.jsonl"


def normalize_entrance_fee(entrance_fee):
    """entrance_fee 값 표준화 -> 무료는 null로 통일"""
    if not entrance_fee or entrance_fee == [] or entrance_fee is None:
        return None

    # 리스트 안에 무료 관련 표현이 있으면 null
    if all(fee in ["입장료: 무료", "관람료: 무료", "무료"] for fee in entrance_fee):
        return None

    # 무료 외 다른 값이 있으면 그대로 유지
    return entrance_fee


def process_jsonl(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as infile, open(
        output_path, "w", encoding="utf-8"
    ) as outfile:
        for line in infile:
            if not line.strip():
                continue
            data = json.loads(line)

            entrance_fee = data.get("entrance_fee")
            data["entrance_fee"] = normalize_entrance_fee(entrance_fee)

            # store_hours 필드 제거
            if "store_hours" in data:
                data.pop("store_hours")

            outfile.write(json.dumps(data, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    process_jsonl(INPUT_PATH, OUTPUT_PATH)
