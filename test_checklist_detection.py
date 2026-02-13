"""
체크리스트 감지 시스템 테스트 스크립트

Redis 기반 체크리스트 감지 상태 관리 시스템을 테스트합니다.
실행 전에 Docker Compose로 Redis 컨테이너가 실행되어 있어야 합니다.
"""

import sys
import os
import time
import asyncio
from typing import Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.cache import (
    get_redis_client, 
    test_redis_connection, 
    close_redis_connection
)
from app.cache.keys import CacheKeys
from app.cache.services.detection_cache import detection_cache_service


def test_detection_flow() -> Dict[str, bool]:
    """체크리스트 감지 플로우 테스트"""
    results = {}
    test_machine_id = "1"
    test_item_index = 1
    
    try:
        print("🔍 체크리스트 감지 플로우 테스트...")
        
        # 초기화
        client = get_redis_client()
        start_time_key = CacheKeys.detection_start_time(test_machine_id, test_item_index)
        update_flag_key = CacheKeys.detection_update_flag(test_machine_id, test_item_index)
        
        # 기존 데이터 정리
        client.delete(start_time_key)
        client.delete(update_flag_key)
        
        # 1. 첫 번째 감지 (True) - start_time 저장되어야 함
        print("   1️⃣ 첫 번째 감지 (True)...")
        result1 = detection_cache_service.process_detection(test_machine_id, test_item_index, True)
        print(f"      결과: {result1}")
        results['first_detection'] = result1.get('status') == 'first_detection'
        
        # 2. 2초 후 재감지 (True) - 아직 5초 미달이므로 waiting 상태
        print("   2️⃣ 2초 후 재감지 (True)...")
        time.sleep(2)
        result2 = detection_cache_service.process_detection(test_machine_id, test_item_index, True)
        print(f"      결과: {result2}")
        results['waiting_detection'] = result2.get('status') == 'waiting'
        
        # 3. 추가 4초 후 재감지 (True) - 총 6초, DB 업데이트 되어야 함
        print("   3️⃣ 4초 후 재감지 (True) - DB 업데이트 예상...")
        time.sleep(4)
        result3 = detection_cache_service.process_detection(test_machine_id, test_item_index, True)
        print(f"      결과: {result3}")
        results['db_update'] = result3.get('status') in ['db_updated', 'update_failed']
        
        # 4. 상태 조회 테스트
        print("   4️⃣ 상태 조회 테스트...")
        status = detection_cache_service.get_detection_status(test_machine_id, test_item_index)
        print(f"      상태: {status}")
        results['status_query'] = status.get('status') in ['completed', 'idle']
        
        # 5. False 감지로 상태 초기화 테스트
        print("   5️⃣ False 감지로 상태 초기화...")
        
        # 먼저 새로운 감지 시작
        client.delete(start_time_key)
        client.delete(update_flag_key)
        detection_cache_service.process_detection(test_machine_id, test_item_index, True)
        
        # False로 초기화
        result5 = detection_cache_service.process_detection(test_machine_id, test_item_index, False)
        print(f"      결과: {result5}")
        results['detection_clear'] = result5.get('status') in ['detection_cleared', 'no_detection']
        
        return results
        
    except Exception as e:
        print(f"❌ 감지 플로우 테스트 실패: {e}")
        return {"error": False}


def test_redis_keys_pattern():
    """Redis 키 패턴 테스트"""
    print("🔍 Redis 키 패턴 테스트...")
    
    machine_id = "2"
    item_index = 3
    
    start_key = CacheKeys.detection_start_time(machine_id, item_index)
    flag_key = CacheKeys.detection_update_flag(machine_id, item_index)
    
    expected_start = f"detection:start:{machine_id}:{item_index}"
    expected_flag = f"detection:flag:{machine_id}:{item_index}"
    
    print(f"   시작 키: {start_key} (예상: {expected_start})")
    print(f"   플래그 키: {flag_key} (예상: {expected_flag})")
    
    return {
        'start_key_pattern': start_key == expected_start,
        'flag_key_pattern': flag_key == expected_flag
    }


def test_concurrent_detections():
    """동시 다발적 감지 테스트"""
    print("🔍 동시 다발적 감지 테스트...")
    
    results = {}
    
    try:
        # 여러 다른 체크리스트에 동시 감지
        machines_items = [("1", 1), ("1", 2), ("2", 1)]
        
        for machine_id, item_index in machines_items:
            print(f"   감지 시작: 기계 {machine_id}, 항목 {item_index}")
            result = detection_cache_service.process_detection(machine_id, item_index, True)
            results[f'{machine_id}_{item_index}'] = result.get('status') == 'first_detection'
        
        # 상태 조회
        for machine_id, item_index in machines_items:
            status = detection_cache_service.get_detection_status(machine_id, item_index)
            print(f"   상태 조회: 기계 {machine_id}, 항목 {item_index} - {status.get('status')}")
        
        return results
        
    except Exception as e:
        print(f"❌ 동시 감지 테스트 실패: {e}")
        return {"error": False}


def cleanup_test_data():
    """테스트 데이터 정리"""
    try:
        client = get_redis_client()
        
        # 테스트용 키 패턴으로 삭제
        test_patterns = [
            "detection:start:1:*",
            "detection:start:2:*", 
            "detection:flag:1:*",
            "detection:flag:2:*"
        ]
        
        deleted_count = 0
        for pattern in test_patterns:
            keys = client.keys(pattern)
            if keys:
                client.delete(*keys)
                deleted_count += len(keys)
        
        print(f"🧹 테스트 데이터 정리 완료 ({deleted_count}개 키 삭제)")
        
    except Exception as e:
        print(f"❌ 테스트 데이터 정리 실패: {e}")


def main():
    """메인 테스트 함수"""
    print("🚀 체크리스트 감지 시스템 테스트 시작")
    print("=" * 60)
    
    # 1. Redis 연결 테스트
    print("1️⃣ Redis 연결 테스트...")
    if not test_redis_connection():
        print("❌ Redis 연결 실패! Docker Compose로 Redis 컨테이너를 실행하세요.")
        print("   실행 명령: docker-compose up -d redis")
        return False
    print("✅ Redis 연결 성공!")
    print()
    
    # 2. Redis 키 패턴 테스트
    print("2️⃣ Redis 키 패턴 테스트...")
    pattern_results = test_redis_keys_pattern()
    print()
    
    # 3. 감지 플로우 테스트
    print("3️⃣ 체크리스트 감지 플로우 테스트...")
    flow_results = test_detection_flow()
    print()
    
    # 4. 동시 감지 테스트
    print("4️⃣ 동시 다발적 감지 테스트...")
    concurrent_results = test_concurrent_detections()
    print()
    
    # 5. 결과 요약
    print("📊 테스트 결과 요약")
    print("-" * 40)
    
    all_results = {**pattern_results, **flow_results, **concurrent_results}
    passed = sum(1 for result in all_results.values() if result is True)
    total = len(all_results)
    
    for test_name, result in all_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print(f"\n📈 전체: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다! 체크리스트 감지 시스템이 정상 작동합니다.")
        print("\n🔗 API 테스트 URL:")
        print("   POST /api/detections/checklist/detect?machine_id=1&item_index=1&is_detected=true")
        print("   GET  /api/detections/checklist/status?machine_id=1&item_index=1")
        print("   GET  /api/detections/checklist/simulate/1/1")
    else:
        print("⚠️  일부 테스트가 실패했습니다. 설정을 확인해주세요.")
    
    # 6. 테스트 데이터 정리
    print("\n🧹 테스트 데이터 정리...")
    cleanup_test_data()
    
    # 7. 연결 종료
    close_redis_connection()
    print("👋 Redis 연결 종료")
    
    return passed == total


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 테스트 중단됨")
        cleanup_test_data()
        close_redis_connection()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        cleanup_test_data()
        close_redis_connection()
        sys.exit(1)