from sqlalchemy.orm import Session
from app.database import SessionLocal, create_tables
from app.models import Checklist

# CHECKLISTS 딕셔너리 데이터 (checklist_service.py에서 가져온 데이터)
CHECKLISTS = {
    "1": [  # 믹싱기
        {"index": 1, "todo": "믹서 커버 개방 시 즉각 정지가 작동하나요?", "done": False, "summary": "기계적 위험 통제"},
        {"index": 2, "todo": "유기 용제(NMP) 주입 배관의 연결부 누출 흔적이 없나요?", "done": False, "summary": "유해 물질 노출 방지"},
        {"index": 3, "todo": "국소배기장치의 풍속이 기준치 이상으로 유지되나요?", "done": False, "summary": "작업 환경 관리"},
        {"index": 4, "todo": "설비 외함 및 배관의 접지 상태가 양호한가요?", "done": False, "summary": "화재/폭발 리스크 평가"},
    ],
    "2": [  # 코터
        {"index": 1, "todo": "건조로 내부 온도 센서 및 과열 방지 장치가 정상인가요?", "done": False, "summary": "비상 대응 준비"},
        {"index": 2, "todo": "롤러 진입부에 방호 가드나 비상 정지 로프가 설치되었나요?", "done": False, "summary": "작업자 보호 장치"},
        {"index": 3, "todo": "NMP 농도 감지기가 정상 작동하며 알람이 울리나요?", "done": False, "summary": "실시간 모니터링"}
    ],
    "3": [  # 슬리터
        {"index": 1, "todo": "원형 칼날의 마모나 파손 상태가 없나요?", "done": False, "summary": "설비 무결성 유지"},
        {"index": 2, "todo": "칼날 교체 시 전원이 완전히 차단(LOTO)되었나요?", "done": False, "summary": "안전 작업 절차 준수"},
    ],
}

def init_database():
    """
    데이터베이스 테이블을 생성하고 초기 체크리스트 데이터를 저장합니다.
    """
    print("데이터베이스 테이블 생성 중...")
    create_tables()
    
    db = SessionLocal()
    try:
        # 기존 데이터가 있는지 확인
        existing_count = db.query(Checklist).count()
        if existing_count > 0:
            print(f"기존 체크리스트 데이터가 {existing_count}개 존재합니다.")
            choice = input("기존 데이터를 삭제하고 새로 생성하시겠습니까? (y/N): ")
            if choice.lower() != 'y':
                print("초기화를 취소했습니다.")
                return
            
            # 기존 데이터 삭제
            db.query(Checklist).delete()
            db.commit()
            print("기존 데이터를 삭제했습니다.")
        
        # CHECKLISTS 딕셔너리 데이터를 DB에 저장
        print("체크리스트 데이터 저장 중...")
        for machine_id, items in CHECKLISTS.items():
            for item in items:
                checklist = Checklist(
                    machine_id=machine_id,
                    item_index=item["index"],
                    todo=item["todo"],
                    done=item["done"],
                    summary=item["summary"]
                )
                db.add(checklist)
        
        db.commit()
        
        # 저장된 데이터 확인
        total_count = db.query(Checklist).count()
        print(f"데이터베이스 초기화 완료! 총 {total_count}개의 체크리스트 항목이 저장되었습니다.")
        
        # 각 machine_id별 데이터 개수 출력
        for machine_id in CHECKLISTS.keys():
            count = db.query(Checklist).filter(Checklist.machine_id == machine_id).count()
            print(f"  - Machine ID {machine_id}: {count}개 항목")
            
    except Exception as e:
        db.rollback()
        print(f"데이터베이스 초기화 중 오류가 발생했습니다: {e}")
    finally:
        db.close()

def get_checklist_from_db(machine_id: str, db: Session):
    """
    데이터베이스에서 특정 machine_id의 체크리스트를 조회합니다.
    """
    return db.query(Checklist).filter(Checklist.machine_id == machine_id).all()

def update_checklist_item_in_db(machine_id: str, item_index: int, done: bool, db: Session):
    """
    데이터베이스에서 특정 체크리스트 항목의 done 상태를 업데이트합니다.
    """
    item = db.query(Checklist).filter(
        Checklist.machine_id == machine_id,
        Checklist.item_index == item_index
    ).first()
    
    if item:
        item.done = done
        db.commit()
        return True
    return False

if __name__ == "__main__":
    # 스크립트로 실행될 때 초기화 진행
    init_database()