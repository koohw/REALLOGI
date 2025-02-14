import cv2
import torch
from ultralytics import YOLO

# YOLOv8 모델 로드
model = YOLO('yolov8n.pt')

# CUDA가 사용 가능한지 확인
device = 'cuda' if torch.cuda.is_available() else 'cpu'
model.to(device)

# 카메라 설정 (예: /dev/video0)
cap = cv2.VideoCapture(0)

# OpenCV에서 CUDA 사용 여부 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0

while True:
    ret, frame = cap.read()  # 프레임 읽기
    if not ret:
        print("Error: Could not read frame.")
        break

    if use_cuda:
        # 프레임을 GPU로 업로드하여 CUDA 가속 사용
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(frame)

        # CUDA에서 이미지를 처리할 때는 보통 그레이스케일 또는 RGB 변환 작업을 수행
        gpu_frame_rgb = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2RGB)

        # GPU에서 처리한 프레임을 다시 다운로드 (CPU로 복사)
        frame = gpu_frame_rgb.download()

    else:
        # CUDA가 없는 경우 CPU에서 처리
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    results = model(frame)  # YOLOv8 객체 감지 수행

    # 다시 BGR로 변환 (OpenCV는 BGR 사용)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    for result in results:  # 감지된 객체를 프레임에 표시
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()  # [0] 인덱스를 추가하여 값 추출
            confidence = box.conf[0].item()  # [0] 인덱스를 추가하여 값 추출
            class_id = box.cls[0].item()  # [0] 인덱스를 추가하여 값 추출
            label = f'{model.names[int(class_id)]}: {confidence:.2f}'  # class_id: 사물 이름 / confidence: 정확도
            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (0, 255, 0), 2)

    # 결과 프레임 표시
    cv2.imshow('YOLOv8 Detection', frame)

    # 'q' 키를 눌러 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# 리소스 해제
cap.release()
cv2.destroyAllWindows()
