import cv2
from pathlib import Path
from PIL import Image
from transformers import pipeline
import torch
import gc

# Zero-shot 객체 탐지 모델 (글로벌 캐싱)
_detector = None

# === 기존 코드 (사용하지 않음) ===
# detector = None
# 
# def get_detector():
#     global detector
#     if detector is None:
#         # GPU 사용 가능 여부 확인
#         if torch.cuda.is_available():
#             device = 0  # NVIDIA GPU
#             device_name = "CUDA GPU"
#         elif torch.backends.mps.is_available():
#             device = "mps"  # Apple Silicon GPU
#             device_name = "Apple MPS GPU"
#         else:
#             device = -1  # CPU
#             device_name = "CPU"
#         
#         detector = pipeline(
#             task="zero-shot-object-detection",
#             model="google/owlvit-base-patch32",
#             device=device
#         )
#         
#         print(f"[INFO] Object detection model loaded on {device_name}")
#     return detector

def get_optimized_device():
    """최적화된 디바이스 선택 (Mac MPS 우선)"""
    if torch.backends.mps.is_available():
        return "mps"
    elif torch.cuda.is_available():
        return 0
    return -1

def get_detector():
    """모델을 한번만 로드하고 재사용"""
    global _detector
    if _detector is None:
        device = get_optimized_device()
        _detector = pipeline(
            "zero-shot-object-detection",
            model="google/owlvit-base-patch32",
            device=device
        )
        print(f"[MODEL] OWL-ViT 로드 완료 (Device: {device})")
    return _detector

def process_video_detection(input_path: str, output_path: str) -> dict:
    """
    가장자리 백색 기계 탐지에 최적화된 비디오 처리
    """
    try:
        detector = get_detector()
        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 가장자리 기계에 특화된 라벨
        candidate_labels = [
            "a photo of a large white rectangular machine",
            "white industrial automated equipment",
        ]

        frame_count = 0
        last_results = []
        total_detections = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            frame_count += 1

            # 5프레임마다 한 번만 탐지 (성능 최적화)
            if frame_count % 5 == 1:
                # OWL-ViT 최적 해상도인 640으로 리사이징
                inf_size = 640
                inf_frame = cv2.resize(frame, (inf_size, inf_size))
                pil_img = Image.fromarray(cv2.cvtColor(inf_frame, cv2.COLOR_BGR2RGB))
                
                raw_results = detector(pil_img, candidate_labels=candidate_labels)
                
                last_results = []
                for res in raw_results:
                    print(f"발견: {res['label']} (확신도: {res['score']:.4f})")

                    if res["score"] > 0.2: # 신뢰도 임계값
                        box = res["box"]
                        # 좌표 복구
                        x1 = int(box["xmin"] * width / inf_size)
                        y1 = int(box["ymin"] * height / inf_size)
                        x2 = int(box["xmax"] * width / inf_size)
                        y2 = int(box["ymax"] * height / inf_size)
                        
                        # 가장자리 필터링 로직
                        # 박스의 중심점이 영상 좌측 40% 또는 우측 40% 내에 있을 때만 채택
                        center_x = (x1 + x2) / 2
                        if center_x < (width * 0.4) or center_x > (width * 0.6):
                            last_results.append({
                                "box": (x1, y1, x2, y2),
                                "label": "Machine",
                                "score": res["score"]
                            })
                            total_detections += 1

            # 화면에 박스 그리기
            for det in last_results:
                x1, y1, x2, y2 = det["box"]
                # 더 굵고 명확한 선으로 기계 표시
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 4)
                cv2.putText(frame, f"status: Running / cheaklist: 2", (x1, y1-15), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            
            out.write(frame)
        
        cap.release()
        out.release()
        gc.collect()
        
        return {
            "status": "success",
            "processed_frames": frame_count,
            "total_detections": total_detections,
            "message": "Detection completed successfully"
        }
        
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Detection failed: {str(e)}"
        }

# === 기존 코드 (사용하지 않음) ===
# === 기존 코드 (사용하지 않음) ===
# def process_video_detection_old(video_path: str, output_path: str) -> list:
#     """
#     Zero-shot 객체 탐지를 사용하여 공장 기계를 탐지하고 박스를 그림
#     """
#     cap = cv2.VideoCapture(video_path)
#     if not cap.isOpened():
#         raise Exception("비디오 파일을 열 수 없습니다")
#     
#     fps = int(cap.get(cv2.CAP_PROP_FPS) or 30)
#     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#     out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
#     
#     # 탐지 모델 로드
#     det = get_detector()
#     
#     # 공장 기계 탐지용 라벨
#     candidate_labels = [
#         "manufacturing machine",
#         "machine tool",
#         "CNC machine",
#         "machining center",
#         "industrial equipment",
#     ]
#     
#     frame_idx = 0
#     frame_step = 2  # 2프레임마다 탐지 (속도 최적화)
#     last_detections = []
#     all_labels = []  # API 응답용
#     
#     # 화면 크기 기준 최소/최대 박스 크기 (화면 전체 탐지 방지)
#     min_box_area = (width * height) * 0.01  # 최소 1%
#     max_box_area = (width * height) * 0.6   # 최대 60% (화면 전체 방지)
#     
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
#         frame_idx += 1
#         
#         # frame_step 간격으로만 탐지
#         if frame_idx % frame_step == 0:
#             pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
#             predictions = det(pil_image, candidate_labels=candidate_labels)
#             
#             # score 필터링 (0.15 이상)
#             predictions = [p for p in predictions if p["score"] >= 0.15]
#             
#             # 박스 크기 필터링 (화면 전체 제외)
#             filtered_preds = []
#             for p in predictions:
#                 box = p["box"]
#                 box_width = box["xmax"] - box["xmin"]
#                 box_height = box["ymax"] - box["ymin"]
#                 box_area = box_width * box_height
#                 
#                 # 너무 작거나 너무 큰 박스 제외
#                 if min_box_area <= box_area <= max_box_area:
#                     filtered_preds.append(p)
#             
#             predictions = sorted(filtered_preds, key=lambda x: x["score"], reverse=True)[:5]
#             last_detections = predictions
#             
#             # 첫 프레임 결과를 API 응답용으로 저장
#             if frame_idx == frame_step and predictions:
#                 for p in predictions:
#                     box = p["box"]
#                     all_labels.append({
#                         "label": "machine",
#                         "confidence": round(p["score"], 2),
#                         "bbox": [int(box["xmin"]), int(box["ymin"]), 
#                                 int(box["xmax"]), int(box["ymax"])]
#                     })
#         
#         # 박스 그리기 (진한 파란색)
#         for p in last_detections:
#             box = p["box"]
#             score = p["score"]
#             x1, y1 = int(box["xmin"]), int(box["ymin"])
#             x2, y2 = int(box["xmax"]), int(box["ymax"])
#             
#             # 박스 (진한 파란색)
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 3)
#             
#             # 라벨 배경 (진한 파란색)
#             text = f"machine {score:.2f}"
#             (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
#             y0 = max(0, y1 - th - 12)
#             cv2.rectangle(frame, (x1, y0), (x1 + tw + 10, y0 + th + 12), (255, 0, 0), -1)
#             
#             # 라벨 텍스트 (흰색)
#             cv2.putText(frame, text, (x1 + 5, y0 + th + 6), 
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
#         
#         out.write(frame)
#     
#     cap.release()
#     out.release()
#     
#     # 탐지 결과가 없으면 mock 데이터 반환
#     if not all_labels:
#         all_labels = [
#             {"label": "machine", "confidence": 0.85, "bbox": [100, 100, 300, 300]}
#         ]
#     
#     return all_labels
