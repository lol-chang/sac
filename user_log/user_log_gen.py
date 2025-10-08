# generate_users_with_keywords.py
import os
import csv
import time
from tqdm import tqdm
from dotenv import load_dotenv
from openai import OpenAI

# -----------------------------
# 0. 환경 설정
# -----------------------------
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# -----------------------------
# 1. 프롬프트 템플릿
# -----------------------------

PROMPT_TEMPLATE = """
Generate one fictional travel user profile in CSV format.

Columns (in order):
user_id, companion, travel_style, budget, duration_days, keywords, crowd_tolerance, age, gender

Guidelines:
- user_id: always "UXXXX" (placeholder, replaced later)
- companion: ["solo", "couple", "friends"]
- travel_style: ["Healing", "Cultural", "Activity", "Foodie"]
- budget: integer in KRW, varied by companion type:
  * Solo: 200000–800000 (often lower range)
  * Couple: 400000–1200000 (spread across full range, not always round numbers)
  * Friends: 500000–1500000 (some high budgets)
  Ensure variation: some low, some mid, some high.
- duration_days: integer 1–5 
  (about 50% 2–3, 30% 1–2, 20% 4–5)
- crowd_tolerance: float 0.0–1.0 (MUST vary, not always the same).
- age: 18–65
- gender: Male / Female

Keywords (MOST IMPORTANT):
- Generate 5–8 concise English keywords (1–3 words each).
- Must include ≥1 lodging, ≥1 attraction, ≥1 restaurant keyword.
- Lodging examples: Clean rooms, Comfortable bedding, Ocean view, Budget-friendly
- Attraction examples: Scenic views, Walking trails, Cultural heritage, Festival atmosphere
- Restaurant examples: Street food, Seafood specialties, Dessert cafés, Friendly service
- Avoid generic words ("good", "nice").
- Do not repeat the same few keywords across profiles; introduce varied terms (e.g., hot spring bath, eco-lodge, rooftop terrace, craft beer, hiking trails, sunset views).

Diversity:
- Each profile must feel distinct.
- Vary companion, style, budget, duration, age, gender, and keywords.
- Avoid duplicate combinations.

⚠️ Output rules (very strict):
- Output ONE CSV row only.
- NO code block, NO triple quotes, NO extra text.
- Keywords must be inside double quotes and separated by semicolons.

Output format example:
UXXXX,couple,Cultural,750000,3,"Scenic views; Local markets; Clean rooms; Seafood specialties",0.42,30,Female
"""



# -----------------------------
# 2. LLM 호출
# -----------------------------
def generate_user_with_llm(user_id: int) -> str:
    """LLM 호출하여 한 명 사용자 생성"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PROMPT_TEMPLATE}],
        temperature=0.9,
        top_p=0.95,
        frequency_penalty=0.4,
        presence_penalty=0.6,
    )
    row = response.choices[0].message.content.strip()
    return row.replace("UXXXX", f"U{user_id:04d}")

# -----------------------------
# 3. CSV 저장
# -----------------------------
def generate_users_csv(output_file: str, n: int = 20):
    header = [
        "user_id",
        "companion",
        "travel_style",
        "budget",
        "duration_days",
        "keywords",
        "crowd_tolerance",
        "age",
        "gender",
    ]
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)

        for user_id in tqdm(range(1, n + 1), desc="Generating users"):
            try:
                row_str = generate_user_with_llm(user_id)
                row = [c.strip() for c in row_str.split(",")]
                writer.writerow(row)
                time.sleep(0.4)
            except Exception as e:
                print(f"[ERROR] user {user_id} 생성 실패: {e}")

    print(f"[INFO] {n} users generated → {output_file}")

# -----------------------------
# 4. 실행
# -----------------------------
if __name__ == "__main__":
    generate_users_csv("synthetic_users3.csv", n=5)
