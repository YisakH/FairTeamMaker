import json
import os
from pathlib import Path

# 이 스크립트는 과거의 past_cooccurrence.json 파일로부터 참가자 목록을 추출하여
# participants.json 파일을 생성/덮어쓰기 위한 일회성 마이그레이션 도구입니다.
# past_cooccurrence.json 파일은 이 스크립트와 동일한 레벨의 디렉토리 (app/ 디렉토리의 부모, 즉 프로젝트 루트)
# 에 위치하거나, 혹은 'data/' 폴더 내에 위치해야 할 수 있습니다.
# 현재 코드는 프로젝트 루트에 있다고 가정합니다.
# 만약 'data/past_cooccurrence.json' 이었다면 cooccurrence_file 경로를 수정해야 합니다.

DATA_DIR = "data"
OLD_COOCCURRENCE_FILENAME = "past_cooccurrence.json" # 과거 파일 이름
PARTICIPANTS_FILENAME = "participants.json"

def migrate_data_from_old_cooccurrence():
    """
    [DEPRECATED] 과거 'past_cooccurrence.json' (프로젝트 루트 가정)에서 참가자 목록을 추출하여 
    'data/participants.json' 파일을 생성/덮어쓰기합니다.
    이 함수는 과거 데이터 구조를 위한 것이며, 현재 시스템에서는 직접 사용되지 않을 수 있습니다.
    """
    # 프로젝트 루트 디렉토리 기준
    project_root = Path(__file__).parent.parent 
    
    # 입력 파일 경로 (과거 cooccurrence 파일)
    # 만약 data 폴더 안에 있었다면: project_root / DATA_DIR / OLD_COOCCURRENCE_FILENAME
    old_cooccurrence_file_path = project_root / OLD_COOCCURRENCE_FILENAME 
    
    # 출력 파일 경로 (참가자 목록 파일)
    output_data_dir = project_root / DATA_DIR
    participants_file_path = output_data_dir / PARTICIPANTS_FILENAME
    
    if not os.path.exists(old_cooccurrence_file_path):
        print(f"경고: 원본 데이터 파일 '{old_cooccurrence_file_path}'을(를) 찾을 수 없습니다. 마이그레이션을 건너니다.")
        return
    
    try:
        with open(old_cooccurrence_file_path, "r", encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"오류: '{old_cooccurrence_file_path}' 파일이 유효한 JSON 형식이 아닙니다. 마이그레이션에 실패했습니다.")
        return
    except IOError as e:
        print(f"오류: '{old_cooccurrence_file_path}' 파일을 읽는 중 I/O 오류 발생: {e}. 마이그레이션에 실패했습니다.")
        return
    
    if not isinstance(data, dict):
        print(f"오류: '{old_cooccurrence_file_path}' 파일의 최상위 데이터 구조가 dictionary가 아닙니다. 참가자 목록을 추출할 수 없습니다.")
        return

    participants = list(data.keys())
    participants.sort() # 이름순으로 정렬
    
    try:
        # 출력 디렉토리 생성 (없는 경우)
        os.makedirs(output_data_dir, exist_ok=True)
        
        with open(participants_file_path, "w", encoding='utf-8') as f:
            json.dump(participants, f, indent=2, ensure_ascii=False)
        
        print(f"성공: '{participants_file_path}' 파일에 참가자 목록을 저장했습니다.")
        print(f"총 {len(participants)}명의 참가자 정보가 마이그레이션되었습니다.")
    except IOError as e:
        print(f"오류: '{participants_file_path}' 파일에 저장하는 중 I/O 오류 발생: {e}. 마이그레이션에 실패했습니다.")
    except Exception as e:
        print(f"오류: 참가자 목록 저장 중 예기치 않은 오류 발생: {e}")

if __name__ == "__main__":
    print("데이터 마이그레이션 스크립트를 실행합니다...")
    # 함수의 이름 변경에 따라 호출도 변경
    migrate_data_from_old_cooccurrence() 