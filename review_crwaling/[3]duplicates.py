import json
from collections import Counter
from pathlib import Path


def check_duplicates(file_path: str):
    """
    JSONL 파일에서 place_id 중복 여부 확인
    """
    place_ids = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                pid = obj.get("place_id")
                if pid:
                    place_ids.append(pid)
            except Exception as e:
                print("JSON parse error:", e)

    counter = Counter(place_ids)
    duplicates = {pid: cnt for pid, cnt in counter.items() if cnt > 1}

    print(f"총 place_id 개수: {len(place_ids)}")
    print(f"고유 place_id 개수: {len(counter)}")
    print(f"중복된 place_id 개수: {len(duplicates)}")

    if duplicates:
        print("중복 목록:")
        for pid, cnt in duplicates.items():
            print(f"  {pid}: {cnt}회")

    return duplicates


def remove_duplicates(input_file: str, output_file: str = None):
    """
    JSONL 파일에서 중복된 place_id 제거 후 새 파일 저장
    (최초 등장한 것만 남김)
    """
    if output_file is None:
        output_file = str(Path(input_file).with_name(Path(input_file).stem + "_dedup.jsonl"))

    seen = set()
    count = 0

    with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
        for line in fin:
            try:
                obj = json.loads(line)
                pid = obj.get("place_id")
                if pid not in seen:
                    seen.add(pid)
                    fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
                    count += 1
            except Exception as e:
                print("JSON parse error:", e)

    print(f"완료 ✅ : {output_file} 에 {count}개의 고유 place_id 저장됨")
    return output_file


# -----------------------------
# 사용 예시
# -----------------------------
# duplicates = check_duplicates("all_places.jsonl")
# remove_duplicates("all_places.jsonl", "all_places_중복제거.jsonl")
