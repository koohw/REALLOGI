import cv2
import torch
import numpy as np

# 모델 타입 설정 (실시간 성능을 고려해 MiDaS_small 사용 권장)
model_type = "MiDaS_small"

# MiDaS 모델 불러오기
midas = torch.hub.load("intel-isl/MiDaS", model_type)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
midas.to(device)
midas.eval()

# 전처리 변환 불러오기
midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
if model_type in ["DPT_Large", "DPT_Hybrid"]:
    transform = midas_transforms.dpt_transform
else:
    transform = midas_transforms.small_transform

# 웹캠 열기 (기본 카메라 사용)
cap = cv2.VideoCapture(2)
if not cap.isOpened():
    print("웹캠을 열 수 없습니다.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        break

    # BGR -> RGB 변환
    img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # 전처리: MiDaS 모델 입력에 맞게 변환
    input_batch = transform(img_rgb).to(device)

    # 깊이 추정 수행
    with torch.no_grad():
        prediction = midas(input_batch)
        # 원본 이미지 크기로 보간
        prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img_rgb.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    # 예측된 깊이 맵을 NumPy 배열로 변환 (상대 깊이 값)
    depth_map = prediction.cpu().numpy()

    # 깊이 맵 정규화 (0~1) 및 컬러맵 적용 (시각화용)
    depth_min = depth_map.min()
    depth_max = depth_map.max()
    depth_map_normalized = (depth_map - depth_min) / (depth_max - depth_min)
    depth_map_uint8 = (depth_map_normalized * 255).astype(np.uint8)
    depth_colormap = cv2.applyColorMap(depth_map_uint8, cv2.COLORMAP_JET)

    # 프레임 중앙의 상대 깊이 값 로그 출력
    center_y = depth_map.shape[0] // 2
    center_x = depth_map.shape[1] // 2
    center_depth = depth_map[center_y, center_x]
    print(f"중앙 상대 깊이 값: {center_depth:.2f}")

    # 결과 화면에 출력
    cv2.imshow("Webcam", frame)
    cv2.imshow("Depth Map", depth_colormap)

    # 'q' 키를 누르면 종료
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

