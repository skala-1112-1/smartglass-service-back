"""
캐시 키 패턴 정의 모듈

Redis에서 사용할 키 패턴들을 체계적으로 관리합니다.
"""

from typing import Union


class CacheKeys:
    """캐시 키 패턴 정의 클래스"""
    
    # === 체크리스트 관련 키 ===
    
    @staticmethod
    def checklist_item(checklist_id: int) -> str:
        """개별 체크리스트 항목 캐시"""
        return f"checklist:item:{checklist_id}"
    
    @staticmethod
    def checklist_list(machine_id: str) -> str:
        """기계별 체크리스트 목록 캐시"""
        return f"checklist:list:{machine_id}"
    
    @staticmethod
    def checklist_done_status(checklist_id: int) -> str:
        """체크리스트 완료 상태 캐시"""
        return f"checklist:done:{checklist_id}"
    
    @staticmethod
    def checklist_progress(machine_id: str) -> str:
        """기계별 체크리스트 진행률 캐시"""
        return f"checklist:progress:{machine_id}"
    
    # === 감지 시스템 관련 키 ===
    
    @staticmethod
    def detection_start_time(machine_id: str, item_index: int) -> str:
        """감지 시작 시간 키"""
        return f"detection:start:{machine_id}:{item_index}"
    
    @staticmethod
    def detection_update_flag(machine_id: str, item_index: int) -> str:
        """DB 업데이트 완료 플래그 키"""
        return f"detection:flag:{machine_id}:{item_index}"
    
    @staticmethod
    def detection_session(session_id: str) -> str:
        """감지 세션 정보 키"""
        return f"detection:session:{session_id}"
    
    @staticmethod
    def detection_logs(machine_id: str, date: str) -> str:
        """감지 로그 키 (날짜별)"""
        return f"detection:logs:{machine_id}:{date}"
    
    # === AI 모델 관련 키 ===
    
    @staticmethod
    def model_cache(model_name: str) -> str:
        """AI 모델 결과 캐시"""
        return f"model:cache:{model_name}"
    
    @staticmethod
    def model_stats(model_name: str, date: str) -> str:
        """AI 모델 성능 통계"""
        return f"model:stats:{model_name}:{date}"
    
    # === 시스템 관련 키 ===
    
    @staticmethod
    def system_config(config_name: str) -> str:
        """시스템 설정 캐시"""
        return f"system:config:{config_name}"
    
    @staticmethod
    def api_rate_limit(api_key: str) -> str:
        """API 속도 제한"""
        return f"api:rate:{api_key}"
    
    @staticmethod
    def session_data(session_id: str) -> str:
        """세션 데이터"""
        return f"session:{session_id}"
    
    # === 통계 관련 키 ===
    
    @staticmethod
    def daily_stats(date: str) -> str:
        """일일 통계"""
        return f"stats:daily:{date}"
    
    @staticmethod
    def machine_stats(machine_id: str, date: str) -> str:
        """기계별 통계"""
        return f"stats:machine:{machine_id}:{date}"
    
    # === 유틸리티 메소드 ===
    
    @staticmethod
    def get_pattern(prefix: str) -> str:
        """키 패턴 검색용"""
        return f"{prefix}:*"
    
    @staticmethod
    def parse_detection_key(key: str) -> tuple:
        """
        감지 키 파싱
        
        Args:
            key: 감지 관련 Redis 키
            
        Returns:
            tuple: (key_type, machine_id, item_index)
        """
        try:
            parts = key.split(":")
            if len(parts) >= 4 and parts[0] == "detection":
                key_type = parts[1]  # start, flag, session 등
                machine_id = parts[2]
                item_index = int(parts[3]) if parts[3].isdigit() else parts[3]
                return (key_type, machine_id, item_index)
            else:
                return (None, None, None)
        except (ValueError, IndexError):
            return (None, None, None)