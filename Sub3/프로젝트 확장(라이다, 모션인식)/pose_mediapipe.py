#NOSE: 코
#LEFT_EYE_INNER, LEFT_EYE, LEFT_EYE_OUTER: 왼쪽 눈의 내측, 중심, 외측
#RIGHT_EYE_INNER, RIGHT_EYE, RIGHT_EYE_OUTER: 오른쪽 눈의 내측, 중심, 외측
#LEFT_EAR: 왼쪽 귀
#RIGHT_EAR: 오른쪽 귀
#MOUTH_LEFT: 입의 왼쪽 끝
#MOUTH_RIGHT: 입의 오른쪽 끝
#LEFT_SHOULDER: 왼쪽 어깨
#RIGHT_SHOULDER: 오른쪽 어깨
#LEFT_ELBOW: 왼쪽 팔꿈치
#RIGHT_ELBOW: 오른쪽 팔꿈치
#LEFT_WRIST: 왼쪽 손목
#RIGHT_WRIST: 오른쪽 손목
#LEFT_PINKY: 왼손 새끼손가락
#RIGHT_PINKY: 오른손 새끼손가락
#LEFT_INDEX: 왼손 검지손가락
#RIGHT_INDEX: 오른손 검지손가락
#LEFT_THUMB: 왼손 엄지손가락
#RIGHT_THUMB: 오른손 엄지손가락
#LEFT_HIP: 왼쪽 엉덩이
#RIGHT_HIP: 오른쪽 엉덩이
#LEFT_KNEE: 왼쪽 무릎
#RIGHT_KNEE: 오른쪽 무릎
#LEFT_ANKLE: 왼쪽 발목
#RIGHT_ANKLE: 오른쪽 발목
#LEFT_HEEL: 왼쪽 발뒤꿈치
#RIGHT_HEEL: 오른쪽 발뒤꿈치
#LEFT_FOOT_INDEX: 왼쪽 발가락 끝
#RIGHT_FOOT_INDEX: 오른쪽 발가락 끝
import cv2
import mediapipe as mp

# MediaPipe 초기화
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()
mp_drawing = mp.solutions.drawing_utils

# 웹캠 캡처 시작
cap = cv2.VideoCapture(0)

# CUDA 사용 가능한지 확인
use_cuda = cv2.cuda.getCudaEnabledDeviceCount() > 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    if use_cuda:
        # CUDA가 활성화된 경우 GPU에서 이미지 처리를 수행
        gpu_frame = cv2.cuda_GpuMat()
        gpu_frame.upload(frame)
        
        # 이미지를 RGB로 변환 (GPU에서)
        gpu_image_rgb = cv2.cuda.cvtColor(gpu_frame, cv2.COLOR_BGR2RGB)
        
        # GPU에서 CPU로 변환된 이미지를 다운로드
        image = gpu_image_rgb.download()
    else:
        # CUDA가 없으면 CPU에서 처리
        image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 포즈 추정
    results = pose.process(image)

    # 이미지에 포즈 랜드마크 그리기
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

    if results.pose_landmarks:
        mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        # 랜드마크 추출
        landmarks = results.pose_landmarks.landmark

        # 왼쪽 팔(어깨, 팔꿈치, 손목) 랜드마크 추출
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value]
        left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value]

        # 왼쪽 팔이 위로 올라갔는지 감지 (어깨보다 팔꿈치와 손목이 위에 있는 경우)
        if left_elbow.y < left_shoulder.y and left_wrist.y < left_elbow.y:
            cv2.putText(image, 'Left arm raised!', (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # 오른쪽 팔도 추가 가능
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW.value]
        right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST.value]

        if right_elbow.y < right_shoulder.y and right_wrist.y < right_elbow.y:
            cv2.putText(image, 'Right arm raised!', (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    # 결과 이미지 출력
    cv2.imshow('Pose Detection', image)

    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
