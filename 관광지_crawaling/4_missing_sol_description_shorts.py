import json
import os
import openai
from tqdm import tqdm
from dotenv import load_dotenv

# ----------------- 설정 -----------------
load_dotenv()

# API 키 확인
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY가 설정되지 않았습니다!")
    exit(1)

openai.api_key = api_key
print("✅ OpenAI API 키 로드됨")

# 파일 경로 확인
TARGET_JSONL = "./관광지_crawaling/[3]tour_places_summarized.jsonl"
SOURCE_JSONL = "./관광지_crawaling/[2]tour_places_with_description.jsonl"
OUTPUT_JSONL = "./관광지_crawaling/[4]tour_places_summarized_filled.jsonl"

for path, name in [(TARGET_JSONL, "TARGET"), (SOURCE_JSONL, "SOURCE")]:
    if not os.path.exists(path):
        print(f"❌ {name} 파일이 존재하지 않습니다: {path}")
        exit(1)
    print(f"✅ {name} 파일 확인: {path}")

# 매칭 키: 예시 포맷 기준 id 우선, 보조로 place_name+address
PRIMARY_KEY = "id"
AUX_KEYS = ["place_name", "address"]

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


def record_primary_key(rec: dict) -> str | None:
    v = rec.get(PRIMARY_KEY)
    if v is not None and str(v).strip():
        return str(v).strip()
    return None


def record_aux_key(rec: dict) -> str | None:
    """보조 키를 합쳐서 키로 사용 (place_name + '|' + address)"""
    name = rec.get("place_name")
    addr = rec.get("address")
    if name and str(name).strip() and addr and str(addr).strip():
        return f"{str(name).strip()}|{str(addr).strip()}"
    return None


def build_source_index(path: str):
    """소스 파일에서 id 및 (place_name|address) -> description 인덱스 생성"""
    by_id = {}
    by_aux = {}
    line_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_count += 1
            if not line.strip():
                continue

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 파싱 오류 (라인 {line_count}): {e}")
                continue

            desc = rec.get("description")
            if not desc or not str(desc).strip():
                continue

            # id 인덱스
            pk = record_primary_key(rec)
            if pk:
                by_id[pk] = str(desc).strip()
            # 보조 인덱스
            ak = record_aux_key(rec)
            if ak:
                by_aux[ak] = str(desc).strip()

    print(
        f"📚 소스 인덱스 로드 완료: 총 라인={line_count}, id={len(by_id)}건, aux={len(by_aux)}건"
    )
    return by_id, by_aux


def summarize(
    description: str, model: str = "gpt-4o", retry_count: int = 3
) -> tuple[str | None, str]:
    """요약 생성 (결과, 상태메시지) 반환"""

    for attempt in range(retry_count):
        try:
            print(f"🤖 API 호출 시도 {attempt + 1}/{retry_count}")

            resp = openai.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {
                        "role": "user",
                        "content": f"The original description is:\n{description.strip()}",
                    },
                ],
                temperature=0.3,
            )

            content = (resp.choices[0].message.content or "").strip()
            char_count = len(content)

            print(f"📝 생성된 요약 ({char_count}자): {content[:50]}...")

            # 완화된 검증 조건
            if content.endswith("입니다."):
                if 95 <= char_count <= 100:
                    return content, f"✅ 성공 ({char_count}자)"
                else:
                    # 길이가 조건에 맞지 않아도 일단 사용
                    return content, f"⚠️ 길이 부족/초과 ({char_count}자) - 그대로 사용"
            else:
                return content, f"⚠️ 형식 오류 (입니다로 끝나지 않음) - 그대로 사용"

        except Exception as e:
            error_msg = f"❌ API 오류 (시도 {attempt + 1}): {str(e)}"
            print(error_msg)
            if attempt == retry_count - 1:
                return None, error_msg

    return None, "❌ 모든 재시도 실패"


def is_null_or_empty(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def main():
    print("🚀 프로그램 시작")

    src_by_id, src_by_aux = build_source_index(SOURCE_JSONL)

    if not src_by_id and not src_by_aux:
        print("❌ 소스 파일에서 유효한 description을 찾을 수 없습니다!")
        return

    processed = 0
    filled = 0
    no_match = 0
    already = 0
    api_errors = 0

    print("📝 처리 시작...")

    with open(TARGET_JSONL, "r", encoding="utf-8") as infile, open(
        OUTPUT_JSONL, "w", encoding="utf-8"
    ) as outfile:

        lines = list(infile)
        print(f"📊 총 처리할 라인 수: {len(lines)}")

        for i, line in enumerate(tqdm(lines, desc="🧠 Filling null descriptions")):
            if not line.strip():
                continue

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON 파싱 오류 (라인 {i+1}): {e}")
                continue

            # description이 이미 있으면 그대로 복사
            if not is_null_or_empty(rec.get("description")):
                already += 1
                outfile.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue

            # 소스에서 원문 description 찾기
            pk = record_primary_key(rec)
            src_desc = None
            match_method = ""

            if pk and pk in src_by_id:
                src_desc = src_by_id[pk]
                match_method = f"ID매칭({pk})"
            else:
                ak = record_aux_key(rec)
                if ak and ak in src_by_aux:
                    src_desc = src_by_aux[ak]
                    match_method = f"이름+주소매칭({ak})"

            if not src_desc:
                no_match += 1
                print(f"⚠️ 매칭 실패 (라인 {i+1}): ID={pk}, AUX={record_aux_key(rec)}")
                outfile.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue

            print(f"\n🔍 처리중 (라인 {i+1}): {match_method}")
            print(f"📄 원문 길이: {len(src_desc)}자")

            # 요약 생성
            summary, status = summarize(src_desc)
            print(f"📋 결과: {status}")

            if summary:
                rec["description"] = summary
                filled += 1
            else:
                api_errors += 1

            processed += 1
            outfile.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("\n" + "=" * 50)
    print("✅ 완료! 저장 위치:", OUTPUT_JSONL)
    print(f"📊 최종 통계:")
    print(f"   - 처리 대상: {processed}건")
    print(f"   - 성공 채움: {filled}건")
    print(f"   - 이미 값 있음: {already}건")
    print(f"   - 매칭 실패: {no_match}건")
    print(f"   - API 오류: {api_errors}건")
    print("=" * 50)


if __name__ == "__main__":
    main()
