# test_ai.py
import sys
from pathlib import Path

# 현재 경로를 시스템 경로에 추가하여 app 패키지를 인식하게 함
sys.path.append(str(Path(__file__).parent))

from app.services.detection_service import run_realtime_inspection

if __name__ == "__main__":
    # 1. 테스트할 체크리스트 항목 정의 (실제 사물 명칭)
    # 정수기라면 'water purifier', 라벨이라면 'warning label' 등을 넣으세요.
    target_items = ["water purifier", "laptop", "cell phone"]
    
    print("=== AI 실시간 점검 테스트 시작 ===")
    print("카메라 창이 뜨면 사물을 비춰보세요. 종료는 'q'키입니다.")
    
    # 2. 실시간 감지 함수 실행 (0은 기본 웹캠)
    final_report = run_realtime_inspection(camera_index=0, checklist_items=target_items)
    
    # 3. 최종 결과 출력
    print("\n" + "="*30)
    print("      최종 점검 결과 보고서      ")
    print("="*30)
    for item, status in final_report.items():
        result_text = "✅ 통과 (AI 확인됨)" if status else "❌ 미완료 (직접 확인 필요)"
        print(f"- {item}: {result_text}")
    print("="*30)