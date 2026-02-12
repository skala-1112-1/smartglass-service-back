import cv2
import torch
import gc
from PIL import Image
from transformers import pipeline

_detector = None

def get_detector():
    global _detector
    if _detector is None:
        # CPU 환경(Device: -1)에서도 최대한 효율적으로 작동하도록 설정
        _detector = pipeline(
            "zero-shot-object-detection",
            model="google/owlvit-base-patch32",
            device=-1 
        )
        print("[MODEL] 사물 인식 AI 로드 완료")
    return _detector

def run_realtime_inspection(camera_index=0):
    detector = get_detector()
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    
    # 탐지 대상 정의 (Monitor 상태 구분 추가)
    items_to_track = {
        "Cell Phone": "a mobile smartphone",
        "Water Purifier": "a water dispenser machine",
        "Tumbler": "a drinking tumbler",
        "Monitor": "a computer monitor screen" # 기본 모니터 탐지용
    }
    
    # 상태 판단용 프롬프트
    monitor_states = ["the screen of a monitor is turned on", "the screen of a monitor is turned off"]
    
    candidate_labels = list(items_to_track.values()) + monitor_states
    inspection_results = {key: "WAITING" for key in items_to_track.keys()}
    inspection_results["Monitor"] = "OFF" # 기본값은 OFF

    print(f"[INFO] 모니터 ON/OFF 포함 점검 시작")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break

        display_frame = frame.copy()
        inf_frame = cv2.resize(frame, (640, 640))
        pil_img = Image.fromarray(cv2.cvtColor(inf_frame, cv2.COLOR_BGR2RGB))

        results = detector(pil_img, candidate_labels=candidate_labels)

        # 이번 프레임에서 발견된 모니터들의 상태를 저장할 임시 리스트
        current_monitor_on = False

        for res in results:
            score = res["score"]
            label_desc = res["label"]
            
            if score > 0.12:
                # 1. 일반 사물 탐지 (폰, 정수기, 텀블러)
                for key, desc in items_to_track.items():
                    if label_desc == desc:
                        if key != "Monitor": # 모니터 외 사물은 PASS/WAITING
                            inspection_results[key] = "PASS"
                
                # 2. 모니터 상태 탐지
                if label_desc == "the screen of a monitor is turned on":
                    current_monitor_on = True
                    inspection_results["Monitor"] = "ON"
                elif label_desc == "the screen of a monitor is turned off" and not current_monitor_on:
                    # ON이 감지되지 않았을 때만 OFF로 유지
                    inspection_results["Monitor"] = "OFF"

                # 시각화 (화면 표시)
                h, w, _ = frame.shape
                box = res["box"]
                x1, y1 = int(box["xmin"] * w / 640), int(box["ymin"] * h / 640)
                x2, y2 = int(box["xmax"] * w / 640), int(box["ymax"] * h / 640)
                
                # 라벨 텍스트 가공 (너무 길면 보기 힘드므로 짧게 출력)
                display_label = label_desc if "monitor" not in label_desc else "Monitor"
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display_frame, f"{display_label} ({int(score*100)}%)", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # 좌측 상단 상태 메뉴 표시
        for i, (item, status) in enumerate(inspection_results.items()):
            color = (0, 255, 0) if status in ["PASS", "ON"] else (0, 0, 255)
            cv2.putText(display_frame, f"{item}: {status}", (20, 40 + (i*30)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.imshow("Smart Glass AI - Monitor Check", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
    cv2.destroyAllWindows()
    return inspection_results

def process_video_detection(input_path: str, output_path: str) -> dict:
    try:
        detector = get_detector()
        cap = cv2.VideoCapture(input_path)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # 탐지 라벨 및 상태 정의
        items_to_track = {
            "Cell Phone": "a mobile smartphone",
            "Water Purifier": "a water dispenser machine",
            "Tumbler": "a drinking tumbler",
            "Monitor": "a computer monitor screen"
        }
        monitor_states = ["the screen of a monitor is turned on", "the screen of a monitor is turned off"]
        candidate_labels = list(items_to_track.values()) + monitor_states
        
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            frame_count += 1

            if frame_count % 3 == 1:
                inf_frame = cv2.resize(frame, (640, 640))
                pil_img = Image.fromarray(cv2.cvtColor(inf_frame, cv2.COLOR_BGR2RGB))
                raw_results = detector(pil_img, candidate_labels=candidate_labels)
                last_results = [res for res in raw_results if res["score"] > 0.15]

            current_monitor_status = "OFF"
            # 모니터 ON 여부 우선 확인
            for res in last_results:
                if res["label"] == "the screen of a monitor is turned on":
                    current_monitor_status = "ON"

            for res in last_results:
                box = res["box"]
                score = res["score"]
                label_desc = res["label"]

                # 좌표 복구
                x1 = int(box["xmin"] * width / 640)
                y1 = int(box["ymin"] * height / 640)
                x2 = int(box["xmax"] * width / 640)
                y2 = int(box["ymax"] * height / 640)

                # 라벨 표시 로직
                if "monitor" in label_desc:
                    display_text = f"Monitor: {current_monitor_status}"
                else:
                    # 일반 사물 이름 찾기
                    display_text = next((k for k, v in items_to_track.items() if v == label_desc), "Object")

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(frame, f"{display_text} ({int(score*100)}%)", (x1, y1-10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            out.write(frame)
        
        cap.release()
        out.release()
        return {"status": "success", "processed_frames": frame_count, "message": "파일 분석 완료"}
        
    except Exception as e:
        return {"status": "error", "message": str(e)}