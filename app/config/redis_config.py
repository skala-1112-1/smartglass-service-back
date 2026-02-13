"""
Redis 연결 설정 모듈

Redis 캐시 시스템과의 연결 및 설정을 관리합니다.
체크리스트 done 상태 캐싱에 주로 사용됩니다.
"""

import redis
from redis.exceptions import ConnectionError, TimeoutError
import os
from typing import Optional
from dotenv import load_dotenv
import logging

# 환경변수 로드
load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)


class RedisConfig:
    """Redis 연결 설정 클래스"""
    
    def __init__(self):
        """Redis 설정 초기화"""
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.db = int(os.getenv("REDIS_DB", 0))
        self.password = os.getenv("REDIS_PASSWORD", None)
        self.decode_responses = True  # 자동으로 bytes를 문자열로 디코딩
        self.socket_connect_timeout = 5
        self.socket_timeout = 5
        
    def get_connection_pool(self) -> redis.ConnectionPool:
        """Redis 연결 풀 생성"""
        return redis.ConnectionPool(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=self.decode_responses,
            socket_connect_timeout=self.socket_connect_timeout,
            socket_timeout=self.socket_timeout,
            retry_on_timeout=True,
            max_connections=20
        )
    
    def create_redis_client(self) -> redis.Redis:
        """Redis 클라이언트 생성"""
        try:
            pool = self.get_connection_pool()
            client = redis.Redis(connection_pool=pool)
            return client
        except Exception as e:
            logger.error(f"Redis 클라이언트 생성 실패: {e}")
            raise


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
        config = RedisConfig()
        _redis_client = config.create_redis_client()
        logger.info(f"Redis 연결 생성됨: {config.host}:{config.port}")
    
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


# 체크리스트 관련 Redis 키 패턴
class RedisKeys:
    """Redis 키 패턴 정의"""
    
    @staticmethod
    def checklist_done_status(checklist_id: int) -> str:
        """체크리스트 완료 상태 키"""
        return f"checklist:done:{checklist_id}"
    
    @staticmethod
    def checklist_detection_start_time(machine_id: str, item_index: int) -> str:
        """체크리스트 감지 시작 시간 키"""
        return f"detection:start:{machine_id}:{item_index}"
    
    @staticmethod
    def checklist_update_flag(machine_id: str, item_index: int) -> str:
        """체크리스트 DB 업데이트 플래그 키"""
        return f"detection:flag:{machine_id}:{item_index}"
    
    @staticmethod
    def checklist_cache(checklist_id: int) -> str:
        """체크리스트 캐시 키"""
        return f"checklist:cache:{checklist_id}"