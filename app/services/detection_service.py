import cv2
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from transformers import OwlViTProcessor, OwlViTForObjectDetection
from transformers import CLIPProcessor, CLIPModel
from collections import deque

# --- 전역 모델 캐싱 (싱글톤 패턴) ---
_owl_processor = None
_owl_model = None
_clip_processor = None
_clip_model = None
_device = "cuda" if torch.cuda.is_available() else "cpu"

def load_models():
    """
    모델을 최초 1회만 로드하고, GPU 사용 시 FP16(반정밀도)을 적용해 속도를 극대화합니다.
    """
    global _owl_processor, _owl_model, _clip_processor, _clip_model

    if _owl_model is None:
        print(f"[SYSTEM] 모델 로딩 및 최적화 시작 (Device: {_device})...")
        
        # 1. OwlViT (탐지)
        _owl_processor = OwlViTProcessor.from_pretrained("google/owlvit-base-patch32")
        _owl_model = OwlViTForObjectDetection.from_pretrained("google/owlvit-base-patch32").to(_device)
        
        # 2. CLIP (상태 분류)
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(_device)

        # GPU 가속 (FP16 적용 - 속도 3배 향상)
        if _device == "cuda":
            _owl_model.half()
            _clip_model.half()
            print("[SYSTEM] GPU 가속(FP16) 활성화 완료.")
        else:
            print("[SYSTEM] CPU 모드로 실행됩니다. (속도가 느릴 수 있음)")

def analyze_screen_cv(pil_image):
    """
    전통적 CV 기법으로 밝기와 복잡도 분석
    Return: 'ON'일 확률 가산점 (0.0 ~ 0.3)
    """
    # PIL -> OpenCV (RGB -> BGR -> Gray)
    img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2GRAY)
    
    # 1. 분산(Variance) 체크: 화면이 켜져있으면 색 변화가 심함
    # 꺼진 화면은 전체적으로 어두워서 분산이 낮음
    variance = np.var(img)
    
    # 2. 엣지(Edge) 체크: 글자나 아이콘이 있는지
    edges = cv2.Canny(img, 100, 200)
    edge_score = np.count_nonzero(edges) / edges.size # 전체 픽셀 중 엣지 비율
    
    cv_score = 0.0
    
    # 임계값은 환경에 따라 조절 필요 (경험적 수치)
    if variance > 500: cv_score += 0.1
    if edge_score > 0.02: cv_score += 0.1 # 2% 이상이 엣지면 내용이 있다고 판단
    
    return cv_score

def get_monitor_status(pil_image, box):
    """
    CLIP을 사용하여 모니터의 화면이 켜져있는지(ON) 꺼져있는지(OFF) 판별합니다.
    Unknown을 방지하기 위해 시각적 묘사 프롬프트를 사용합니다.
    """
    width, height = pil_image.size
    x1, y1, x2, y2 = box
    x1, y1 = max(0, int(x1)), max(0, int(y1))
    x2, y2 = min(width, int(x2)), min(height, int(y2))
    
    if x2 <= x1 or y2 <= y1: return "OFF", 0.0

    cropped_img = pil_image.crop((x1, y1, x2, y2))
    
    # 프롬프트 앙상블
    positive_prompts = [
        "a computer screen showing windows desktop",
        "a glowing monitor displaying content",
        "a bright lcd screen with text"
    ]
    negative_prompts = [
        "a black blank monitor screen",
        "a dark glass surface",
        "a reflection on a turned off screen"
    ]
    
    all_prompts = positive_prompts + negative_prompts
    
    inputs = _clip_processor(text=all_prompts, images=cropped_img, return_tensors="pt", padding=True).to(_device)
    if _device == "cuda":
        inputs["pixel_values"] = inputs["pixel_values"].half()
        
    with torch.no_grad():
        outputs = _clip_model(**inputs)
        
    # 확률 계산 (Softmax)
    probs = outputs.logits_per_image.softmax(dim=1).cpu().float().numpy()[0]
    
    # 긍정 그룹 평균 vs 부정 그룹 평균
    avg_on_score = np.mean(probs[:3]) 
    avg_off_score = np.mean(probs[3:])
    
    
    cv_bonus = analyze_screen_cv(cropped_img)
    
    final_on_score = avg_on_score + cv_bonus
    
    # 최종 판단
    if final_on_score > avg_off_score:
        return "ON", final_on_score
    else:
        return "OFF", avg_off_score


# ---------------------------------------------------------
# 1. 실시간 카메라 연동 함수
# ---------------------------------------------------------
def run_realtime_inspection(camera_index=0):
    """
    웹캠을 열어 실시간으로 탐지하고, 'q'를 누르면 종료 시점의 결과(Dict)를 반환합니다.
    """
    load_models()
    
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    
    # 탐지 설정
    texts = [["a mobile smartphone", "a water dispenser", "a tumbler", "a computer monitor"]]
    labels_map = ["Cell Phone", "Water Purifier", "Tumbler", "Monitor"]
    
    # 최종 반환할 결과 데이터
    final_results = {key: "WAITING" for key in labels_map}
    final_results["Monitor"] = "OFF"
    
    print("[INFO] 실시간 점검 시작 (화면의 'q'를 누르면 종료하고 결과를 전송합니다)")

    frame_count = 0
    skip_frames = 2  # 성능 최적화를 위한 프레임 스킵
    last_detections = [] 

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        frame_count += 1
        display_frame = frame.copy()

        # --- 추론 (3프레임당 1회) ---
        if frame_count % (skip_frames + 1) == 0:
            last_detections = []
            h, w, _ = frame.shape
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(rgb_frame)

            inputs = _owl_processor(text=texts, images=pil_img, return_tensors="pt").to(_device)
            if _device == "cuda":
                inputs["pixel_values"] = inputs["pixel_values"].half()

            with torch.no_grad():
                outputs = _owl_model(**inputs)

            target_sizes = torch.Tensor([[h, w]]).to(_device)
            results = _owl_processor.post_process_object_detection(outputs, threshold=0.1, target_sizes=target_sizes)[0]

            found_monitor = False
            
            for box, score, label_idx in zip(results["boxes"], results["scores"], results["labels"]):
                label_text = labels_map[label_idx]
                box_cpu = box.tolist()
                
                status_suffix = ""
                color = (255, 255, 0) # 기본 노란색
                
                # 1. 모니터 상태 확인
                if label_text == "Monitor":
                    status, conf = get_monitor_status(pil_img, box_cpu)
                    final_results["Monitor"] = status # 결과 업데이트
                    status_suffix = f": {status}"
                    color = (0, 255, 0) if status == "ON" else (0, 0, 255)
                    found_monitor = True
                
                # 2. 일반 사물 확인
                else:
                    final_results[label_text] = "PASS" # 발견되면 PASS 처리
                
                last_detections.append({
                    "box": box_cpu,
                    "label": label_text,
                    "suffix": status_suffix,
                    "score": score.item(),
                    "color": color
                })

        # --- 그리기 (매 프레임) ---
        for det in last_detections:
            x1, y1, x2, y2 = map(int, det["box"])
            text = f"{det['label']}{det['suffix']} ({det['score']:.2f})"
            cv2.rectangle(display_frame, (x1, y1), (x2, y2), det["color"], 2)
            cv2.putText(display_frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, det["color"], 2)

        # 상태 패널 UI
        for i, (k, v) in enumerate(final_results.items()):
            c = (0, 255, 0) if v in ["PASS", "ON"] else (0, 0, 255)
            if v == "WAITING": c = (180, 180, 180)
            cv2.putText(display_frame, f"{k}: {v}", (10, 30 + i*30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, c, 2)

        cv2.imshow("Real-time Inspection (Press 'q' to save & exit)", display_frame)
        
        # 'q'를 누르면 루프 종료하고 현재 상태 반환
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    
    # 라우터로 최종 결과 딕셔너리 반환
    return final_results


# ---------------------------------------------------------
# 2. 영상 파일 처리 함수
# ---------------------------------------------------------
def process_video_detection(input_path: str, output_path: str) -> dict:
    """
    업로드된 비디오 파일을 읽어 분석 후 결과 영상을 저장합니다.
    (실시간 탐지와 동일한 최적화 로직 적용)
    """
    try:
        load_models() # 모델 로드
        
        cap = cv2.VideoCapture(input_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        
        # 코덱 설정
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        texts = [["a mobile smartphone", "a water dispenser", "a tumbler", "a computer monitor"]]
        labels_map = ["Cell Phone", "Water Purifier", "Tumbler", "Monitor"]
        
        total_detections_count = 0
        frame_count = 0
        last_detections = [] # 그리기용 캐시

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            frame_count += 1
            
            # 파일 처리는 2프레임마다 1번 추론 (속도/품질 타협)
            if frame_count % 2 == 1:
                last_detections = []
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                
                inputs = _owl_processor(text=texts, images=pil_img, return_tensors="pt").to(_device)
                if _device == "cuda":
                    inputs["pixel_values"] = inputs["pixel_values"].half()
                
                with torch.no_grad():
                    outputs = _owl_model(**inputs)
                
                target_sizes = torch.Tensor([[height, width]]).to(_device)
                results = _owl_processor.post_process_object_detection(outputs, threshold=0.1, target_sizes=target_sizes)[0]
                
                for box, score, label_idx in zip(results["boxes"], results["scores"], results["labels"]):
                    if score < 0.12: continue
                    
                    label_text = labels_map[label_idx]
                    box_cpu = box.tolist()
                    status_suffix = ""
                    color = (0, 255, 0)
                    
                    if label_text == "Monitor":
                        status, _ = get_monitor_status(pil_img, box_cpu)
                        status_suffix = f": {status}"
                        color = (0, 255, 0) if status == "ON" else (0, 0, 255)
                    
                    last_detections.append({
                        "box": box_cpu,
                        "text": f"{label_text}{status_suffix}",
                        "color": color
                    })
                    total_detections_count += 1

            # 그리기
            for det in last_detections:
                x1, y1, x2, y2 = map(int, det["box"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), det["color"], 3)
                cv2.putText(frame, det["text"], (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, det["color"], 2)

            out.write(frame)

        cap.release()
        out.release()
        
        return {
            "status": "success",
            "message": "영상 분석 완료",
            "processed_frames": frame_count,
            "total_detections": total_detections_count
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}