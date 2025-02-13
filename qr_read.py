import cv2
from pyzbar.pyzbar import decode
import json
from collections import deque

# QR 코드 데이터 읽기 (프레임 전처리 포함)
def preprocess_frame(frame):
    """
    입력 프레임을 전처리하여 QR 코드 감지에 적합하게 만듭니다.
    """
    # 가우시안 블러를 사용하여 노이즈 제거
    blurred_frame = cv2.GaussianBlur(frame, (5, 5), 0)
    return blurred_frame

def read_qr_code_from_frame(frame, qr_data_buffer, buffer_size=5):
    """
    프레임에서 QR 코드를 읽고 멀티프레임 검증을 통해 데이터를 반환합니다.
    """
    # QR 코드 디코딩
    decoded_objects = decode(frame)

    for obj in decoded_objects:
        qr_data = obj.data.decode("utf-8")  # QR 코드 데이터
       
        # QR 코드 데이터 저장 및 버퍼 관리
        qr_data_buffer.append(qr_data)
        if len(qr_data_buffer) > buffer_size:
            qr_data_buffer.popleft()
       
        # 데이터 일관성 확인 (다수 프레임에서 동일 데이터 확인)
        if qr_data_buffer.count(qr_data) > buffer_size // 2:
            try:
                # JSON 데이터를 Python 딕셔너리로 변환
                data = json.loads(qr_data)
                return data
            except json.JSONDecodeError:
                print("QR 데이터가 JSON 형식이 아닙니다.")
                return None

    return None

# 라즈베리파이 카메라로 QR 코드 읽기
def read_qr_from_camera():
    cap = cv2.VideoCapture(0)  # 0번 카메라 사용 (USB 카메라 또는 Pi 카메라)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return None

    # QR 코드 데이터 버퍼 초기화
    qr_data_buffer = deque(maxlen=5)

    print("QR 코드를 카메라에 보여주세요.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("프레임을 읽을 수 없습니다.")
            break
       
        # 프레임 전처리
        processed_frame = preprocess_frame(frame)
       
        # 관심 영역 (ROI) 설정 (중앙 영역만 사용)
        height, width, _ = frame.shape
        roi = processed_frame[int(height * 0.3):int(height * 0.7), int(width * 0.3):int(width * 0.7)]

        # QR 코드 읽기
        data = read_qr_code_from_frame(roi, qr_data_buffer)
        if data:
            print(f"QR 코드 데이터: {data}")
            position = data.get("position", "알 수 없음")
            command = data.get("command", "알 수 없음")
            duration = data.get("duration", "알 수 없음")
           
            print(f"현재 위치: {position}")
            print(f"명령: {command}")
            print(f"주행 멈춤 시간: {duration}초")
            break

        # 디버깅용: 화면 출력 (ROI 표시)
        cv2.rectangle(frame, (int(width * 0.3), int(height * 0.3)),
                      (int(width * 0.7), int(height * 0.7)), (0, 255, 0), 2)
        cv2.imshow("Camera", frame)
       
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# 실행
read_qr_from_camera()

