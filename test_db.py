#!/usr/bin/env python3
"""
PostgreSQL 연결 테스트 및 기본 사용법 스크립트
"""

from app.database import SessionLocal, create_tables
from app.models import Checklist
from app.init_db import init_database
from sqlalchemy import text

def test_connection():
    """데이터베이스 연결 테스트"""
    try:
        db = SessionLocal()
        # 간단한 쿼리로 연결 테스트
        result = db.execute(text("SELECT 1")).fetchone()
        print("✅ 데이터베이스 연결 성공!")
        
        # 현재 사용자 확인
        user_result = db.execute(text("SELECT current_user")).fetchone()
        print(f"✅ 현재 사용자: {user_result[0]}")
        
        # 데이터베이스 확인
        db_result = db.execute(text("SELECT current_database()")).fetchone()
        print(f"✅ 현재 데이터베이스: {db_result[0]}")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {e}")
        return False

def test_crud_operations():
    """기본적인 CRUD 작업 테스트"""
    db = SessionLocal()
    
    try:
        # Create - 테스트 데이터 추가
        test_item = Checklist(
            machine_id="test",
            item_index=999,
            todo="테스트 항목",
            done=False,
            summary="테스트용 체크리스트 항목"
        )
        db.add(test_item)
        db.commit()
        print("✅ 데이터 생성 성공!")
        
        # Read - 데이터 조회
        items = db.query(Checklist).filter(Checklist.machine_id == "test").all()
        print(f"✅ 데이터 조회 성공! 조회된 항목 수: {len(items)}")
        
        # Update - 데이터 수정
        if items:
            items[0].done = True
            db.commit()
            print("✅ 데이터 수정 성공!")
        
        # Delete - 테스트 데이터 삭제
        db.query(Checklist).filter(Checklist.machine_id == "test").delete()
        db.commit()
        print("✅ 데이터 삭제 성공!")
        
    except Exception as e:
        print(f"❌ CRUD 작업 중 오류 발생: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    print("=" * 50)
    print("PostgreSQL 연동 테스트 시작")
    print("=" * 50)
    
    # 1. 연결 테스트
    print("\n1. 데이터베이스 연결 테스트")
    if not test_connection():
        print("연결에 실패했습니다. PostgreSQL 서버와 .env 파일을 확인하세요.")
        return
    
    # 2. 테이블 생성
    print("\n2. 테이블 생성")
    try:
        create_tables()
        print("✅ 테이블 생성 완료!")
    except Exception as e:
        print(f"❌ 테이블 생성 실패: {e}")
        return
    
    # 3. CRUD 작업 테스트
    print("\n3. CRUD 작업 테스트")
    test_crud_operations()
    
    # 4. 기존 체크리스트 데이터 확인
    print("\n4. 기존 체크리스트 데이터 확인")
    db = SessionLocal()
    try:
        total_count = db.query(Checklist).count()
        print(f"현재 저장된 체크리스트 항목 수: {total_count}")
        
        if total_count == 0:
            print("\n초기 데이터를 저장하시겠습니까?")
            choice = input("초기 데이터를 저장하려면 'y'를 입력하세요 (y/N): ")
            if choice.lower() == 'y':
                db.close()  # Close before calling init_database
                init_database()
                return
    except Exception as e:
        print(f"데이터 확인 중 오류: {e}")
    finally:
        db.close()
    
    print("\n=" * 50)
    print("테스트 완료!")
    print("=" * 50)

if __name__ == "__main__":
    main()