import cv2
import torch
import gc
from PIL import Image
from transformers import pipeline
from pathlib import Path

# 글로벌 모델 캐싱
_detector = None

def get_optimized_device():
    if torch.backends.mps.is_available(): return "mps"
    if torch.cuda.is_available(): return 0
    return -1

# detection_service.py 맨 아래에 추가
def process_video_detection(input_path: str, output_path: str):
    """기존 라우터와의 호환성을 위해 남겨두는 함수"""
    # 기존 로직이 비디오 파일을 처리하는 것이라면 제가 처음에 드린 
    # 수정 코드의 내용을 이 이름으로 맞추시면 됩니다.
    pass

def get_detector():
    global _detector
    if _detector is None:
        device = get_optimized_device()
        # 정밀도가 높은 owlvit-base-patch32 사용
        _detector = pipeline(
            "zero-shot-object-detection",
            model="google/owlvit-base-patch32",
            device=device
        )
        print(f"[MODEL] AI 모델 로드 완료 (Device: {device})")
    return _detector

def run_realtime_inspection(camera_index=0, checklist_items=None):
    """
    실제 카메라 영상을 실시간으로 분석하여 체크리스트 수행 여부 판단
    """
    detector = get_detector()
    # cv2.CAP_DSHOW를 추가하여 Windows의 직접 쇼 메커니즘을 사용합니다.
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    
    # 기본 체크리스트 설정 (정수기, 라벨 등)
    if checklist_items is None:
        checklist_items = [
            "water purifier", 
            "safety label on machine", 
            "control panel",
            "cup on the tray"
        ]

    print(f"[INFO] 실시간 점검 시작 (대상: {checklist_items})")
    print("종료하려면 'q'를 누르세요.")

    # 결과 저장용 상태 (한 번이라도 발견되면 Pass 처리)
    inspection_results = {item: False for item in checklist_items}

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        # AI 추론용 이미지 변환 (640 사이즈 최적화)
        display_frame = frame.copy()
        inf_frame = cv2.resize(frame, (640, 640))
        pil_img = Image.fromarray(cv2.cvtColor(inf_frame, cv2.COLOR_BGR2RGB))

        # AI 탐지
        results = detector(pil_img, candidate_labels=checklist_items)

        for res in results:
            score = res["score"]
            label = res["label"]
            
            if score > 0.15:  # 신뢰도 임계값
                # 점검 통과 업데이트
                inspection_results[label] = True
                
                # 박스 좌표 복구 (원본 해상도 기준)
                h, w, _ = frame.shape
                box = res["box"]
                x1 = int(box["xmin"] * w / 640)
                y1 = int(box["ymin"] * h / 640)
                x2 = int(box["xmax"] * w / 640)
                y2 = int(box["ymax"] * h / 640)

                # 시각화 (녹색: 탐지됨)
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display_frame, f"{label}: {score:.2f} [OK]", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 실시간 체크리스트 상태 표시 (화면 좌측 상단)
        y_offset = 30
        cv2.putText(display_frame, "--- CHECKLIST STATUS ---", (10, y_offset), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for item, status in inspection_results.items():
            y_offset += 25
            color = (0, 255, 0) if status else (0, 0, 255)
            text = f"{item}: {'PASS' if status else 'WAITING'}"
            cv2.putText(display_frame, text, (10, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        cv2.imshow("Smart Glass AI Inspection", display_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    gc.collect()

    return inspection_results