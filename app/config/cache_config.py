"""
캐시 관련 설정 모듈

Redis 연결 설정 및 환경변수 관리
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()


class CacheConfig:
    """캐시 시스템 설정 클래스"""
    
    def __init__(self):
        """캐시 설정 초기화"""
        # Redis 연결 설정
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_db = int(os.getenv("REDIS_DB", 0))
        self.redis_password = os.getenv("REDIS_PASSWORD", None)
        
        # Redis 연결 옵션
        self.decode_responses = True
        self.socket_connect_timeout = 5
        self.socket_timeout = 5
        self.retry_on_timeout = True
        self.max_connections = 20
        
        # 캐시 TTL 설정 (초)
        self.default_ttl = 3600                    # 1시간
        self.checklist_ttl = 1800                  # 30분
        self.detection_ttl = 60                    # 1분
        self.update_flag_ttl = 1800               # 30분
        
        # 감지 시스템 설정
        self.detection_threshold = 5               # 5초 지속 감지
        
    def get_redis_url(self) -> str:
        """Redis URL 생성"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def to_dict(self) -> dict:
        """설정을 딕셔너리로 반환"""
        return {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
            "password": "***" if self.redis_password else None,
            "decode_responses": self.decode_responses,
            "socket_connect_timeout": self.socket_connect_timeout,
            "socket_timeout": self.socket_timeout,
            "retry_on_timeout": self.retry_on_timeout,
            "max_connections": self.max_connections
        }


# 전역 설정 인스턴스
cache_config = CacheConfig()