import json
import statistics
from collections import defaultdict

# 입력/출력 파일 경로
INPUT_FILE  = r"C:\Users\changjin\workspace\lab\pln\[5-1]all_places_with_prices.jsonl"
OUTPUT_FILE = r"C:\Users\changjin\workspace\lab\pln\[5-2]all_places_for_category.jsonl"

def load_data(input_file):
    """jsonl 파일 읽어서 list로 반환"""
    data = []
    with open(input_file, "r", encoding="utf-8") as fin:
        for line in fin:
            try:
                obj = json.loads(line)
                data.append(obj)
            except Exception as e:
                print("JSON parse error:", e)
    return data

def build_category_stats(data):
    """카테고리별 avg_price 기반으로 평균 min/max/avg 계산"""
    cat_prices = defaultdict(list)

    for obj in data:
        cat = obj.get("category")
        avg_price = obj.get("avg_price")
        min_price = obj.get("min_price")
        max_price = obj.get("max_price")

        if cat and avg_price is not None:
            cat_prices[cat].append((min_price, max_price, avg_price))

    # 카테고리별 평균값 계산
    cat_stats = {}
    for cat, values in cat_prices.items():
        mins = [v[0] for v in values if v[0] is not None]
        maxs = [v[1] for v in values if v[1] is not None]
        avgs = [v[2] for v in values if v[2] is not None]

        if avgs:
            cat_stats[cat] = {
                "min_price": int(statistics.mean(mins)) if mins else None,
                "max_price": int(statistics.mean(maxs)) if maxs else None,
                "avg_price": int(statistics.mean(avgs))
            }

    return cat_stats

def fill_missing_prices(data, cat_stats):
    """all_prices가 null인 경우 category 평균값으로 대체"""
    for obj in data:
        if obj.get("all_prices") is None:
            cat = obj.get("category")
            if cat and cat in cat_stats:
                stats = cat_stats[cat]
                obj["min_price"] = stats["min_price"]
                obj["max_price"] = stats["max_price"]
                obj["avg_price"] = stats["avg_price"]
    return data

def save_data(data, output_file):
    """jsonl 파일로 저장"""
    with open(output_file, "w", encoding="utf-8") as fout:
        for obj in data:
            fout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    print(f"✅ 완료: {output_file} 에 저장됨")

if __name__ == "__main__":
    data = load_data(INPUT_FILE)
    cat_stats = build_category_stats(data)
    data_filled = fill_missing_prices(data, cat_stats)
    save_data(data_filled, OUTPUT_FILE)
