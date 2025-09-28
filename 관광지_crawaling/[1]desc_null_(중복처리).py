import json
import uuid
from fuzzywuzzy import fuzz
from tqdm import tqdm

INPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\tour_places.jsonl"
OUTPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\tour_places_cleaned.jsonl"

def is_similar(name1, name2, threshold=80):
    return fuzz.token_sort_ratio(name1, name2) >= threshold

def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def save_jsonl(data, path):
    with open(path, "w", encoding="utf-8") as f:
        for entry in data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def clean_data(entries):
    seen_names = []
    cleaned = []

    for entry in tqdm(entries, desc="🚀 중복 제거 및 정리 중"):
        name = entry.get("place_name", "").strip()

        if name in seen_names:
            continue

        for existing_name in seen_names:
            if is_similar(name, existing_name):
                print(f"🔍 유사한 이름 감지: '{name}' ≈ '{existing_name}'")
                break  # 유사하지만 저장은 허용 (완전 동일한 것만 제외)

        # ✅ 필드 정리
        entry["description"] = None  # 무조건 null
        seen_names.append(name)
        cleaned.append(entry)

    return cleaned

if __name__ == "__main__":
    entries = load_jsonl(INPUT_PATH)
    cleaned_entries = clean_data(entries)
    save_jsonl(cleaned_entries, OUTPUT_PATH)
    print(f"\n✅ 완료! 중복 제거 후 총 {len(cleaned_entries)}개 저장 → {OUTPUT_PATH}")
