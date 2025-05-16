import json
import os
from pathlib import Path

def migrate_data():
    """
    past_cooccurrence.json에서 참가자 목록을 추출하여 participants.json 파일을 생성합니다.
    """
    # 파일 경로 설정
    base_dir = Path(__file__).parent.parent
    cooccurrence_file = base_dir / "past_cooccurrence.json"
    participants_file = base_dir / "participants.json"
    
    # past_cooccurrence.json이 존재하는지 확인
    if not os.path.exists(cooccurrence_file):
        print(f"'{cooccurrence_file}' 파일이 존재하지 않습니다.")
        return
    
    # 파일에서 데이터 읽기
    with open(cooccurrence_file, "r", encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"'{cooccurrence_file}' 파일을 JSON으로 파싱할 수 없습니다.")
            return
    
    # 참가자 목록 추출
    participants = list(data.keys())
    
    # participants.json 파일에 저장
    with open(participants_file, "w", encoding='utf-8') as f:
        json.dump(participants, f, indent=2, ensure_ascii=False)
    
    print(f"'{participants_file}' 파일이 생성되었습니다.")
    print(f"총 {len(participants)}명의 참가자 정보가 마이그레이션되었습니다.")

if __name__ == "__main__":
    migrate_data() 