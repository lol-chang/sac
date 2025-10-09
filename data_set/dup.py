import os
import pandas as pd

BASE_PATH = r"C:\Users\changjin\workspace\lab\pln\data_set\null_X"

def check_id_duplicates(base_path):
    print("=" * 80)
    print("🔍 CSV 파일별 id 중복 상세 검사 시작")
    print("=" * 80)

    files = [f for f in os.listdir(base_path) if f.endswith(".csv")]
    if not files:
        print("⚠️ CSV 파일이 없습니다.")
        return

    for file in files:
        file_path = os.path.join(base_path, file)
        print(f"\n📂 {file}")

        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f" ❌ 파일 읽기 오류: {e}")
            continue

        if 'id' not in df.columns:
            print(" ⚠️ 'id' 컬럼 없음 — 건너뜀")
            continue

        total_count = len(df)
        unique_count = df['id'].nunique()
        dup_count = total_count - unique_count

        print(f" - 총 행 수: {total_count}")
        print(f" - 고유 id 수: {unique_count}")

        if dup_count > 0:
            dup_df = df[df['id'].duplicated(keep=False)].copy()
            dup_df["duplicate_group_count"] = dup_df.groupby("id")["id"].transform("count")
            print(f" ❌ 중복 ID {dup_count}개 발견 — 상세 목록:")
            for dup_id, group in dup_df.groupby("id"):
                idx_list = group.index.tolist()
                count = len(idx_list)
                print(f"    ▶ ID {dup_id} ({count}회) → 행 위치: {idx_list}")
        else:
            print(" ✅ 중복 없음")

        if total_count > 0:
            print(f" - id 타입 예시: {type(df['id'].iloc[0])}")

    print("\n✅ 검사 완료")
    print("=" * 80)


if __name__ == "__main__":
    check_id_duplicates(BASE_PATH)
