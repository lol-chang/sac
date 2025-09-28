# import json
# import re

# input_file = r"C:\Users\changjin\workspace\lab\pln\all_places.jsonl"
# output_file = r"C:\Users\changjin\workspace\lab\pln\all_places_clean.jsonl"

# # 메타 텍스트(프로필 줄) 판별: 리뷰 N, 사진 M, (팔로우 | 팔로워 K)가 모두 존재하면 제거
# def is_meta_review(text: str) -> bool:
#     if not text:
#         return False
#     t = re.sub(r'\s+', ' ', text).strip()
#     # 사이에 다른 단어가 껴도 허용 (.*), 팔로워 숫자 or 팔로우 키워드 허용
#     pattern = r'리뷰\s*\d[\d,]*.*사진\s*\d[\d,]*.*(팔로우|팔로워\s*\d[\d,]*)'
#     return re.search(pattern, t) is not None

# with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
#     for line in fin:
#         try:
#             obj = json.loads(line)
#         except Exception as e:
#             print("JSON parse error:", e)
#             continue

#         reviews = obj.get("reviews_attraction", [])
#         cleaned = [r for r in reviews if not is_meta_review(r.get("text", ""))]
#         obj["reviews_attraction"] = cleaned

#         fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

# print(f"✅ 완료: {output_file} 저장 (메타 리뷰 제거됨)")

# => 아래 코드로 업데이트 됨 (지금 프로젝트에 저장된 애들은 위 코드라서 제대로 안지워진 상태!)

import json
import re

input_file = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[6]data.jsonl"
output_file = r"C:\Users\changjin\workspace\lab\pln\review_crwaling\[7]data.jsonl"

# 프로필 메타 리뷰 판별
def is_meta_review(text: str) -> bool:
    if not text:
        return False
    t = re.sub(r'\s+', ' ', text).strip()
    # "리뷰 숫자" + ("팔로우" or "팔로워 + 숫자 + 팔로우") 패턴
    pattern = r'리뷰\s*\d[\d,]*.*(팔로우|팔로워\s*\d[\d,]*.*팔로우)'
    return re.search(pattern, t) is not None

with open(input_file, "r", encoding="utf-8") as fin, open(output_file, "w", encoding="utf-8") as fout:
    for line in fin:
        try:
            obj = json.loads(line)
        except Exception as e:
            print("JSON parse error:", e)
            continue

        reviews = obj.get("reviews_attraction", [])
        cleaned = [r for r in reviews if not is_meta_review(r.get("text", ""))]
        obj["reviews_attraction"] = cleaned

        fout.write(json.dumps(obj, ensure_ascii=False) + "\n")

print(f"✅ 완료: {output_file} 저장 (프로필 메타 리뷰 제거됨)")
