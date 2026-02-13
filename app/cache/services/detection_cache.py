"""
감지 상태 캐시 서비스

AI 감지 결과 및 상태 관리를 위한 Redis 캐싱 서비스
"""

import time
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from app.cache.client import get_redis_client  
from app.cache.keys import CacheKeys
from app.config.cache_config import cache_config
from app.database import get_db
from app.models import Checklist

logger = logging.getLogger(__name__)


class DetectionCacheService:
    """감지 상태 캐시 관리 서비스"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.detection_threshold = cache_config.detection_threshold  # 5초
    
    # === 감지 상태 관리 ===
    
    def process_detection(self, machine_id: str, item_index: int, is_detected: bool) -> dict:
        """
        AI 감지 결과 처리
        
        Args:
            machine_id: 기계 ID
            item_index: 체크리스트 아이템 인덱스  
            is_detected: 감지 결과 (True/False)
            
        Returns:
            dict: 처리 결과 상태
        """
        try:
            if is_detected:
                return self._handle_detection(machine_id, item_index)
            else:
                return self._handle_detection_clear(machine_id, item_index)
                
        except Exception as e:
            logger.error(f"감지 처리 오류: {e}")
            return {"status": "error", "message": str(e)}
    
    def _handle_detection(self, machine_id: str, item_index: int) -> dict:
        """감지 발생 처리"""
        start_time_key = CacheKeys.detection_start_time(machine_id, item_index)
        update_flag_key = CacheKeys.detection_update_flag(machine_id, item_index)
        
        # 이미 DB 업데이트가 완료된 상태인지 확인
        if self.redis_client.exists(update_flag_key):
            return {
                "status": "already_updated",
                "message": "이미 DB 업데이트 완료됨"
            }
        
        current_time = time.time()
        
        # 기존 start_time 확인
        stored_start_time = self.redis_client.get(start_time_key)
        
        if stored_start_time is None:
            # 첫 감지 - start_time 저장
            self.redis_client.set(start_time_key, current_time, ex=cache_config.detection_ttl)
            logger.info(f"첫 감지 기록: {machine_id}:{item_index}")
            return {
                "status": "first_detection",
                "message": "첫 감지 시간 기록됨",
                "start_time": current_time
            }
        else:
            # 기존 감지 있음 - 시간 차이 계산
            start_time = float(stored_start_time)
            elapsed_time = current_time - start_time
            
            logger.info(f"지속 감지: {machine_id}:{item_index}, 경과시간: {elapsed_time:.2f}초")
            
            if elapsed_time >= self.detection_threshold:
                # 5초 이상 지속 - DB 업데이트
                update_result = self._update_checklist_to_db(machine_id, item_index)
                
                if update_result["success"]:
                    # 중복 업데이트 방지 플래그 설정
                    self.redis_client.set(update_flag_key, "updated", ex=cache_config.update_flag_ttl)
                    # start_time 삭제
                    self.redis_client.delete(start_time_key)
                    
                    # 감지 로그 저장
                    self._log_detection_event(machine_id, item_index, elapsed_time, update_result)
                    
                    return {
                        "status": "db_updated", 
                        "message": f"DB 업데이트 완료 (지속시간: {elapsed_time:.2f}초)",
                        "checklist_id": update_result.get("checklist_id"),
                        "elapsed_time": elapsed_time
                    }
                else:
                    return {
                        "status": "update_failed",
                        "message": update_result.get("error", "DB 업데이트 실패")
                    }
            else:
                # 5초 미만 - 계속 대기
                remaining_time = self.detection_threshold - elapsed_time
                return {
                    "status": "waiting",
                    "message": f"지속 감지 중 (남은시간: {remaining_time:.2f}초)",
                    "elapsed_time": elapsed_time,
                    "remaining_time": remaining_time
                }
    
    def _handle_detection_clear(self, machine_id: str, item_index: int) -> dict:
        """감지 해제 처리"""
        start_time_key = CacheKeys.detection_start_time(machine_id, item_index)
        
        if self.redis_client.exists(start_time_key):
            self.redis_client.delete(start_time_key)
            logger.info(f"감지 해제: {machine_id}:{item_index}")
            return {
                "status": "detection_cleared",
                "message": "감지 상태 초기화됨"
            }
        else:
            return {
                "status": "no_detection",
                "message": "진행 중인 감지가 없음"
            }
    
    def _update_checklist_to_db(self, machine_id: str, item_index: int) -> dict:
        """체크리스트 DB 업데이트"""
        try:
            db = next(get_db())
            
            # 해당 체크리스트 항목 찾기
            checklist = db.query(Checklist).filter(
                Checklist.machine_id == machine_id,
                Checklist.item_index == item_index
            ).first()
            
            if not checklist:
                return {
                    "success": False,
                    "error": f"체크리스트를 찾을 수 없음: {machine_id}:{item_index}"
                }
            
            # done 상태 업데이트
            checklist.done = True
            db.commit()
            
            logger.info(f"DB 업데이트 성공: 체크리스트 ID {checklist.id}")
            
            return {
                "success": True,
                "checklist_id": checklist.id,
                "machine_id": machine_id,
                "item_index": item_index
            }
            
        except Exception as e:
            logger.error(f"DB 업데이트 실패: {e}")
            if 'db' in locals():
                db.rollback()
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if 'db' in locals():
                db.close()
    
    # === 상태 조회 ===
    
    def get_detection_status(self, machine_id: str, item_index: int) -> dict:
        """현재 감지 상태 조회"""
        start_time_key = CacheKeys.detection_start_time(machine_id, item_index)
        update_flag_key = CacheKeys.detection_update_flag(machine_id, item_index)
        
        # DB 업데이트 완료 여부 확인
        if self.redis_client.exists(update_flag_key):
            return {
                "status": "completed",
                "message": "DB 업데이트 완료됨"
            }
        
        # 현재 감지 상태 확인
        stored_start_time = self.redis_client.get(start_time_key)
        
        if stored_start_time:
            start_time = float(stored_start_time)
            elapsed_time = time.time() - start_time
            remaining_time = max(0, self.detection_threshold - elapsed_time)
            
            return {
                "status": "detecting",
                "elapsed_time": elapsed_time,
                "remaining_time": remaining_time,
                "progress_percent": min(100, (elapsed_time / self.detection_threshold) * 100)
            }
        else:
            return {
                "status": "idle",
                "message": "감지 대기 중"
            }
    
    # === 로그 관리 ===
    
    def _log_detection_event(self, machine_id: str, item_index: int, elapsed_time: float, update_result: dict):
        """감지 이벤트 로그"""
        try:
            date_str = datetime.now().strftime("%Y-%m-%d")
            log_key = CacheKeys.detection_logs(machine_id, date_str)
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "machine_id": machine_id,
                "item_index": item_index,
                "elapsed_time": elapsed_time,
                "checklist_id": update_result.get("checklist_id"),
                "success": update_result.get("success", False)
            }
            
            # 리스트에 로그 추가 (최대 1000개 유지)
            self.redis_client.lpush(log_key, json.dumps(log_entry))
            self.redis_client.ltrim(log_key, 0, 999)
            self.redis_client.expire(log_key, 86400 * 7)  # 7일 보관
            
        except Exception as e:
            logger.error(f"감지 로그 저장 실패: {e}")
    
    def get_detection_logs(self, machine_id: str, date: str = None) -> list:
        """감지 로그 조회"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            log_key = CacheKeys.detection_logs(machine_id, date)
            logs = self.redis_client.lrange(log_key, 0, -1)
            
            return [json.loads(log) for log in logs]
            
        except Exception as e:
            logger.error(f"감지 로그 조회 실패: {e}")
            return []
    
    # === 유틸리티 ===
    
    def clear_detection_flags(self, machine_id: str, item_index: int) -> dict:
        """감지 플래그 초기화"""
        try:
            start_time_key = CacheKeys.detection_start_time(machine_id, item_index)
            update_flag_key = CacheKeys.detection_update_flag(machine_id, item_index)
            
            deleted_count = 0
            for key in [start_time_key, update_flag_key]:
                if self.redis_client.exists(key):
                    self.redis_client.delete(key)
                    deleted_count += 1
            
            return {
                "status": "cleared",
                "message": f"{deleted_count}개 플래그 삭제됨"
            }
            
        except Exception as e:
            logger.error(f"플래그 초기화 실패: {e}")
            return {"status": "error", "message": str(e)}


# 서비스 인스턴스
detection_cache_service = DetectionCacheService()