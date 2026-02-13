"""
Redis 클라이언트 관리 모듈

Redis 연결 생성, 관리 및 테스트 기능을 제공합니다.
"""

import redis
from redis.exceptions import ConnectionError, TimeoutError
from typing import Optional
import logging

from app.config.cache_config import cache_config

# 로깅 설정
logger = logging.getLogger(__name__)

# Redis 클라이언트 인스턴스 (싱글톤 패턴)
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Redis 클라이언트 인스턴스 반환 (싱글톤)
    
    Returns:
        redis.Redis: Redis 클라이언트 인스턴스
        
    Raises:
        ConnectionError: Redis 연결 실패시
    """
    global _redis_client
    
    if _redis_client is None:
        try:
            # 연결 풀 생성
            pool = redis.ConnectionPool(
                host=cache_config.redis_host,
                port=cache_config.redis_port,
                db=cache_config.redis_db,
                password=cache_config.redis_password,
                decode_responses=cache_config.decode_responses,
                socket_connect_timeout=cache_config.socket_connect_timeout,
                socket_timeout=cache_config.socket_timeout,
                retry_on_timeout=cache_config.retry_on_timeout,
                max_connections=cache_config.max_connections
            )
            
            _redis_client = redis.Redis(connection_pool=pool)
            logger.info(f"Redis 연결 생성됨: {cache_config.redis_host}:{cache_config.redis_port}")
            
        except Exception as e:
            logger.error(f"Redis 클라이언트 생성 실패: {e}")
            raise
    
    return _redis_client


def test_redis_connection() -> bool:
    """
    Redis 연결 테스트
    
    Returns:
        bool: 연결 성공 여부
    """
    try:
        client = get_redis_client()
        # PING 명령으로 연결 테스트
        response = client.ping()
        if response:
            logger.info("Redis 연결 테스트 성공")
            return True
        else:
            logger.error("Redis PING 응답 실패")
            return False
            
    except (ConnectionError, TimeoutError) as e:
        logger.error(f"Redis 연결 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"Redis 연결 테스트 중 예외 발생: {e}")
        return False


def close_redis_connection():
    """Redis 연결 종료"""
    global _redis_client
    
    if _redis_client:
        try:
            _redis_client.close()
            logger.info("Redis 연결 종료됨")
        except Exception as e:
            logger.error(f"Redis 연결 종료 중 오류: {e}")
        finally:
            _redis_client = None


def get_redis_info() -> dict:
    """Redis 서버 정보 조회"""
    try:
        client = get_redis_client()
        info = client.info()
        return {
            "version": info.get("redis_version"),
            "uptime": info.get("uptime_in_seconds"), 
            "memory_used": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "total_commands_processed": info.get("total_commands_processed")
        }
    except Exception as e:
        logger.error(f"Redis 정보 조회 실패: {e}")
        return {"error": str(e)}


def clear_cache(pattern: str = None) -> int:
    """
    캐시 데이터 삭제
    
    Args:
        pattern: 삭제할 키 패턴 (없으면 전체 삭제)
        
    Returns:
        int: 삭제된 키 개수
    """
    try:
        client = get_redis_client()
        
        if pattern:
            keys = client.keys(pattern)
        else:
            keys = client.keys("*")
            
        if keys:
            deleted = client.delete(*keys)
            logger.info(f"캐시 삭제 완료: {deleted}개 키")
            return deleted
        else:
            return 0
            
    except Exception as e:
        logger.error(f"캐시 삭제 실패: {e}")
        return 0