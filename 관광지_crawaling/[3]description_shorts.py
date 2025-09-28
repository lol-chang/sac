import json
import os
import openai
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
# 🔧 OpenAI API 설정
openai.api_key = os.getenv("Gpt_API_KEY")
# 📁 경로 설정
INPUT_JSONL = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\[2]tour_places_with_description.jsonl"
OUTPUT_JSONL = r"C:\Users\changjin\workspace\lab\pln\관광지_crawaling\[3]tour_places_summarized.jsonl"

# 📌 시스템 프롬프트
SYSTEM_MSG = (
    "<|begin_of_text|><|start_header_id|>system<|end_header_id|>"
    "You are a Korean-speaking assistant specializing in summarizing long descriptions of tourist spots.\n"
    "You must generate ONE **natural Korean summary** (95–100 characters).\n\n"
    "📌 Summary Guidelines:\n"
    "- Focus on concrete, location-specific details tourists will experience on-site.\n"
    "- Mention distinctive facilities (e.g. foot baths, trails), activities (e.g. camping, forest bathing), or scenery (e.g. pine forests, sea views).\n"
    "- Avoid generic expressions like 'great for walking' or 'good for families'. Be specific.\n"
    "- Do NOT include history, founding dates, or administrative info unless directly relevant.\n"
    "- Must end with '~입니다.'\n"
    "- Do NOT include any header, tag, markdown, or label. Return only one sentence.\n"
    "- Summary must be between **95 to 100 Korean characters (including spaces)**.\n\n"
    "Respond with ONLY the final sentence.\n"
    "<|eot_id|><|start_header_id|>assistant<|end_header_id|>"
)

# 🧠 요약 생성 함수
def get_summary(description: str, model: str = "gpt-4o") -> str:
    user_msg = f"The original description is:\n{description.strip()}"
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_MSG},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.3,
        )
        content = response.choices[0].message.content.strip()
        if content and content.endswith("입니다."):
            return content
        return None
    except Exception as e:
        print("⚠️ API 요청 오류:", e)
        return None

# 🔁 전체 처리 루프
with open(INPUT_JSONL, "r", encoding="utf-8") as infile, \
     open(OUTPUT_JSONL, "w", encoding="utf-8") as outfile:

    for line in tqdm(infile, desc="🔍 Summarizing and Replacing Description"):
        data = json.loads(line)
        desc = data.get("description")

        if not desc or desc.strip() == "":
            data["description"] = None
        else:
            summary = get_summary(desc)
            data["description"] = summary

        outfile.write(json.dumps(data, ensure_ascii=False) + "\n")

print("✅ description 필드에 요약 완료! 저장 위치:", OUTPUT_JSONL)