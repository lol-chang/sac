import json

# 파일 경로
input_file = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[8-2]data_with_address_retry.jsonl"

total = 0
null_count = 0

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        try:
            obj = json.loads(line)
            total += 1
            addr = obj.get("address")
            if addr in (None, "", "null"):
                null_count += 1
        except:
            continue

print(f"총 레코드: {total}")
print(f"address == null 인 레코드: {null_count}")
