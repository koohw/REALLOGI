#WRIST: 손목
#THUMB_CMC: 엄지 기저부(손목과 연결된 관절)
#THUMB_MCP: 엄지 중간 관절 (MCP)
#THUMB_IP: 엄지 끝 관절 (IP)
#THUMB_TIP: 엄지 끝 (팁)
#INDEX_FINGER_MCP: 검지 손가락 중간 관절 (MCP)
#INDEX_FINGER_PIP: 검지 손가락 끝에서 두 번째 관절 (PIP)
#INDEX_FINGER_DIP: 검지 손가락 끝에서 첫 번째 관절 (DIP)
#INDEX_FINGER_TIP: 검지 손가락 끝 (팁)
#MIDDLE_FINGER_MCP: 중지 손가락 중간 관절 (MCP)
#MIDDLE_FINGER_PIP: 중지 손가락 끝에서 두 번째 관절 (PIP)
#MIDDLE_FINGER_DIP: 중지 손가락 끝에서 첫 번째 관절 (DIP)
#MIDDLE_FINGER_TIP: 중지 손가락 끝 (팁)
#RING_FINGER_MCP: 약지 손가락 중간 관절 (MCP)
#RING_FINGER_PIP: 약지 손가락 끝에서 두 번째 관절 (PIP)
#RING_FINGER_DIP: 약지 손가락 끝에서 첫 번째 관절 (DIP)
#RING_FINGER_TIP: 약지 손가락 끝 (팁)
#PINKY_MCP: 새끼 손가락 중간 관절 (MCP)
#PINKY_PIP: 새끼 손가락 끝에서 두 번째 관절 (PIP)
#PINKY_DIP: 새끼 손가락 끝에서 첫 번째 관절 (DIP)
#PINKY_TIP: 새끼 손가락 끝 (팁)

import cv2
import mediapipe as mp

# MediaPipe 초기화
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()
mp_drawing = mp.solutions.drawing_utils

# 웹캡 캡처 시작
cap = cv2.VideoCapture(0)

# CUDA 사용 여부 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if use_cuda:
        # CUDA가 활성화된 경우, GPU에서 이미지 처리를 수행
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(frame)

        # 이미지를 RGB로 변환 (GPU에서)
        gpu_image_rgb = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2RGB)

        # GPU에서 변환된 이미지를 CPU로 다운로드
        image = gpu_image_rgb.download()
    else:
        # CUDA가 없으면 CPU에서 이미지 처리
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 핸드 추정
    results = hands.process(image)

    # 이미지를 다시 BGR로 변환 (이미지를 출력하기 위해)
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    finger_count = 0

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # 랜드마크 그리기
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            # 각 손가락의 랜드마크
            landmarks = hand_landmarks.landmark

            # 엄지 손가락 (Tip - IP joint)
            if landmarks[mp_hands.HandLandmark.THUMB_TIP].x < landmarks[mp_hands.HandLandmark.THUMB_IP].x:
                finger_count += 1

            # 검지 손가락 (Tip - PIP joint)
            if landmarks[mp_hands.HandLandmark.INDEX_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.INDEX_FINGER_PIP].y:
                finger_count += 1

            # 중지 손가락 (Tip - PIP joint)
            if landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.MIDDLE_FINGER_PIP].y:
                finger_count += 1

            # 약지 손가락 (Tip - PIP joint)
            if landmarks[mp_hands.HandLandmark.RING_FINGER_TIP].y < landmarks[mp_hands.HandLandmark.RING_FINGER_PIP].y:
                finger_count += 1

            # 새끼 손가락 (Tip - PIP joint)
            if landmarks[mp_hands.HandLandmark.PINKY_TIP].y < landmarks[mp_hands.HandLandmark.PINKY_PIP].y:
                finger_count += 1

            # 손가락 개수 출력
            cv2.putText(image, f'Fingers: {finger_count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    # 결과 이미지 출력
    cv2.imshow('Hand Detection', image)

    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

