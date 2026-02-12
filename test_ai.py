import sys
from pathlib import Path

# 경로 설정
sys.path.append(str(Path(__file__).parent))

from app.services.detection_service import run_realtime_inspection

if __name__ == "__main__":
    print("=== AI 실시간 점검 테스트 시작 ===")
    print("카메라 창이 뜨면 사물을 비춰보세요. 종료는 'q'키입니다.")
    
    # 수정 포인트: 괄호 안을 비워주세요! 
    # 이제 함수가 알아서 핸드폰, 정수기, 텀블러를 찾습니다.
    final_report = run_realtime_inspection(camera_index=0)
    
    print("\n" + "="*30)
    print("      최종 점검 결과 보고서      ")
    print("="*30)
    for item, status in final_report.items():
        result_text = "✅ PASS" if status else "❌ WAITING"
        print(f"- {item}: {result_text}")
    print("="*30)