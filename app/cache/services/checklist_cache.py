"""
체크리스트 캐시 서비스

체크리스트 데이터의 Redis 캐싱을 관리합니다.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.cache.client import get_redis_client
from app.cache.keys import CacheKeys
from app.config.cache_config import cache_config

logger = logging.getLogger(__name__)


class ChecklistCacheService:
    """체크리스트 캐싱 서비스"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
    
    # === 개별 체크리스트 캐싱 ===
    
    def cache_checklist_item(self, checklist_id: int, data: dict, ttl: int = None) -> bool:
        """개별 체크리스트 항목 캐시"""
        try:
            key = CacheKeys.checklist_item(checklist_id)
            ttl = ttl or cache_config.checklist_ttl
            
            cache_data = {
                **data,
                "cached_at": datetime.now().isoformat(),
                "ttl": ttl
            }
            
            self.redis_client.set(
                key, 
                json.dumps(cache_data, ensure_ascii=False),
                ex=ttl
            )
            
            logger.info(f"체크리스트 캐시됨: ID {checklist_id}")
            return True
            
        except Exception as e:
            logger.error(f"체크리스트 캐싱 실패: {e}")
            return False
    
    def get_cached_checklist_item(self, checklist_id: int) -> Optional[dict]:
        """캐시된 체크리스트 항목 조회"""
        try:
            key = CacheKeys.checklist_item(checklist_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                return json.loads(cached_data)
            else:
                return None
                
        except Exception as e:
            logger.error(f"체크리스트 캐시 조회 실패: {e}")
            return None
    
    # === 체크리스트 목록 캐싱 ===
    
    def cache_checklist_list(self, machine_id: str, checklist_data: List[dict], ttl: int = None) -> bool:
        """기계별 체크리스트 목록 캐시"""
        try:
            key = CacheKeys.checklist_list(machine_id)
            ttl = ttl or cache_config.checklist_ttl
            
            cache_data = {
                "machine_id": machine_id,
                "checklists": checklist_data,
                "total_count": len(checklist_data),
                "cached_at": datetime.now().isoformat()
            }
            
            self.redis_client.set(
                key,
                json.dumps(cache_data, ensure_ascii=False),
                ex=ttl
            )
            
            logger.info(f"체크리스트 목록 캐시됨: 기계 {machine_id} ({len(checklist_data)}개)")
            return True
            
        except Exception as e:
            logger.error(f"체크리스트 목록 캐싱 실패: {e}")
            return False
    
    def get_cached_checklist_list(self, machine_id: str) -> Optional[List[dict]]:
        """캐시된 체크리스트 목록 조회"""
        try:
            key = CacheKeys.checklist_list(machine_id)
            cached_data = self.redis_client.get(key)
            
            if cached_data:
                data = json.loads(cached_data)
                return data.get("checklists", [])
            else:
                return None
                
        except Exception as e:
            logger.error(f"체크리스트 목록 캐시 조회 실패: {e}")
            return None
    
    # === 완료 상태 캐싱 ===
    
    def cache_done_status(self, checklist_id: int, is_done: bool, additional_data: dict = None) -> bool:
        """체크리스트 완료 상태 캐시"""
        try:
            key = CacheKeys.checklist_done_status(checklist_id)
            
            cache_data = {
                "checklist_id": checklist_id,
                "done": is_done,
                "updated_at": datetime.now().isoformat(),
                **(additional_data or {})
            }
            
            self.redis_client.hset(key, mapping=cache_data)
            self.redis_client.expire(key, cache_config.checklist_ttl)
            
            logger.info(f"완료 상태 캐시됨: ID {checklist_id}, done={is_done}")
            return True
            
        except Exception as e:
            logger.error(f"완료 상태 캐싱 실패: {e}")
            return False
    
    def get_done_status(self, checklist_id: int) -> Optional[dict]:
        """캐시된 완료 상태 조회"""
        try:
            key = CacheKeys.checklist_done_status(checklist_id)
            return self.redis_client.hgetall(key)
            
        except Exception as e:
            logger.error(f"완료 상태 조회 실패: {e}")
            return None
    
    # === 진행률 캐싱 ===
    
    def cache_progress(self, machine_id: str, progress_data: dict) -> bool:
        """
        기계별 체크리스트 진행률 캐시
        
        Args:
            machine_id: 기계 ID
            progress_data: 진행률 데이터
            
        Returns:
            bool: 캐시 성공 여부
        """
        try:
            key = CacheKeys.checklist_progress(machine_id)
            
            cache_data = {
                "machine_id": machine_id,
                "updated_at": datetime.now().isoformat(),
                **progress_data
            }
            
            self.redis_client.hset(key, mapping=cache_data)
            self.redis_client.expire(key, cache_config.checklist_ttl)
            
            return True
            
        except Exception as e:
            logger.error(f"진행률 캐싱 실패: {e}")
            return False
    
    def get_progress(self, machine_id: str) -> Optional[dict]:
        """
        캐시된 진행률 조회
        
        Args:
            machine_id: 기계 ID
            
        Returns:
            dict: 진행률 데이터 또는 None
        """
        try:
            key = CacheKeys.checklist_progress(machine_id)
            return self.redis_client.hgetall(key)
            
        except Exception as e:
            logger.error(f"진행률 조회 실패: {e}")
            return None

# 서비스 인스턴스
checklist_cache_service = ChecklistCacheService()