import json
from tqdm import tqdm

# ----------------- 설정 -----------------
INPUT_JSONL = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[5]tour_places_with_naver_info.jsonl"
OUTPUT_JSONL = "/Users/changjin/Desktop/Workspace/lab/sac/관광지_crawaling/[6]tour_places_with_review_urls.jsonl"


def replace_url_with_review_url(place_id):
    """place_id를 사용해서 리뷰 URL 생성"""
    if place_id:
        return f"https://m.place.naver.com/restaurant/{place_id}/review/visitor?entry=ple&reviewSort=recent"
    return None


def process_jsonl():
    """JSONL 파일의 URL을 리뷰 URL로 교체"""

    processed = 0
    updated = 0
    no_place_id = 0

    with open(INPUT_JSONL, "r", encoding="utf-8") as infile, open(
        OUTPUT_JSONL, "w", encoding="utf-8"
    ) as outfile:

        lines = list(infile)
        print(f"📊 총 처리할 항목: {len(lines)}개")

        for i, line in enumerate(tqdm(lines, desc="🔄 URL 교체 중")):
            if not line.strip():
                outfile.write(line)
                continue

            try:
                record = json.loads(line)
                place_id = record.get("place_id")
                place_name = record.get("place_name", "Unknown")

                if place_id:
                    # 새로운 리뷰 URL로 교체
                    new_url = replace_url_with_review_url(place_id)
                    old_url = record.get("url", "None")

                    record["url"] = new_url
                    updated += 1

                    print(f"✅ 교체됨 ({i+1}): {place_name}")
                    print(f"   🆔 place_id: {place_id}")
                    print(f"   📎 새 URL: {new_url}")

                else:
                    no_place_id += 1
                    print(f"⚠️ place_id 없음 ({i+1}): {place_name}")

                processed += 1

                # 수정된 레코드 저장
                outfile.write(json.dumps(record, ensure_ascii=False) + "\n")

            except json.JSONDecodeError as e:
                print(f"❌ JSON 파싱 오류 (라인 {i+1}): {e}")
                outfile.write(line)
            except Exception as e:
                print(f"❌ 처리 오류 (라인 {i+1}): {e}")
                outfile.write(line)

    print("\n" + "=" * 70)
    print("🎉 URL 교체 완료!")
    print(f"📊 결과 통계:")
    print(f"   - 총 처리: {processed}개")
    print(f"   - URL 교체 성공: {updated}개")
    print(f"   - place_id 없음: {no_place_id}개")
    print(f"📁 저장 위치: {OUTPUT_JSONL}")
    print("=" * 70)


def preview_changes():
    """변경사항 미리보기 (실제 파일 수정 없이)"""
    print("🔍 변경사항 미리보기 (처음 3개 항목):")
    print("=" * 70)

    with open(INPUT_JSONL, "r", encoding="utf-8") as infile:
        for i, line in enumerate(infile):
            if i >= 3:  # 처음 3개만
                break

            if not line.strip():
                continue

            try:
                record = json.loads(line)
                place_id = record.get("place_id")
                place_name = record.get("place_name", "Unknown")
                old_url = record.get("url", "None")

                print(f"\n📍 항목 {i+1}: {place_name}")
                print(f"🆔 place_id: {place_id}")
                print(f"🔗 현재 URL: {old_url}")

                if place_id:
                    new_url = replace_url_with_review_url(place_id)
                    print(f"✨ 새 URL: {new_url}")
                else:
                    print(f"❌ place_id가 없어서 URL 교체 불가")

            except Exception as e:
                print(f"❌ 오류: {e}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    print("🚀 네이버 플레이스 URL 교체기")
    print("=" * 70)

    # 사용자 선택
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        preview_changes()
    else:
        # 미리보기 후 실행 여부 확인
        preview_changes()

        user_input = input("\n위와 같이 변경됩니다. 계속 진행하시겠습니까? (y/N): ")
        if user_input.lower() in ["y", "yes"]:
            process_jsonl()
        else:
            print("❌ 취소되었습니다.")
