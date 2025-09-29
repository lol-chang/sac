import json

# 입력 및 출력 경로 설정
INPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[13]data.jsonl"
OUTPUT_PATH = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[13]data_updated.jsonl"

with open(INPUT_PATH, "r", encoding="utf-8") as infile, \
     open(OUTPUT_PATH, "w", encoding="utf-8") as outfile:

    for line in infile:
        data = json.loads(line)

        # 'like' → 'likes'
        if "like" in data:
            data["likes"] = data["like"]
            del data["like"]

        # 'unlike' → 'dislikes'
        if "unlike" in data:
            data["dislikes"] = data["unlike"]
            del data["unlike"]

        # 결과 쓰기
        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

print("✅ 키 변경 완료! 저장 경로:", OUTPUT_PATH)
