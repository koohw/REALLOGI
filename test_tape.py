import cv2
import numpy as np
import time
from PCA9685 import PCA9685

# --- 모터 제어 클래스 ---
class MotorDriver:
    def __init__(self):
        # 모터에 연결된 채널 번호 (예시)
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4

        self.pwm = PCA9685(0x40, debug=True)
        self.pwm.setPWMFreq(50)

    def MotorRun(self, motor, direction, speed):
        # speed 값은 0~100 사이 (최대 100)
        if speed > 100:
            speed = 100
        if motor == 0:  # 왼쪽 모터
            self.pwm.setDutycycle(self.PWMA, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.AIN1, 0)
                self.pwm.setLevel(self.AIN2, 1)
            else:
                self.pwm.setLevel(self.AIN1, 1)
                self.pwm.setLevel(self.AIN2, 0)
        else:  # 오른쪽 모터
            self.pwm.setDutycycle(self.PWMB, int(speed))
            if direction == 'forward':
                self.pwm.setLevel(self.BIN1, 0)
                self.pwm.setLevel(self.BIN2, 1)
            else:
                self.pwm.setLevel(self.BIN1, 1)
                self.pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor):
        if motor == 0:
            self.pwm.setDutycycle(self.PWMA, 0)
        else:
            self.pwm.setDutycycle(self.PWMB, 0)

# --- PID 컨트롤러 클래스 ---
class PID:
    def __init__(self, kp, ki, kd):
        self.kp = kp  # 비례 상수
        self.ki = ki  # 적분 상수
        self.kd = kd  # 미분 상수
        self.prev_error = 0
        self.integral = 0

    def update(self, error, dt):
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        output = self.kp * error + self.ki * self.integral + self.kd * derivative
        self.prev_error = error
        return output

# --- 빨간색 라인 검출 함수 ---
# 빨간색은 HSV에서 0~10도와 160~180도의 두 구간으로 나타납니다.
lower_red1 = np.array([0, 100, 100])
upper_red1 = np.array([10, 255, 255])
lower_red2 = np.array([160, 100, 100])
upper_red2 = np.array([180, 255, 255])

def detect_red_line(frame):
    """
    입력 영상에서 빨간색 영역(라인)을 검출하고,
    가장 큰 빨간색 영역의 중심 좌표(cx, cy)를 반환합니다.
    만약 검출되지 않으면 (False, None, mask)를 반환합니다.
    """
    # 전처리: 가우시안 블러로 노이즈 감소
    blurred = cv2.GaussianBlur(frame, (5, 5), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

    # 두 범위의 마스크 생성 후 결합
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # 형태학적 연산으로 노이즈 제거
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    # 윤곽선 검출
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        # 가장 큰 윤곽선 선택
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            return True, (cx, cy), mask
    return False, None, mask

# --- 라인 트래킹 및 주행 함수 ---
def line_following():
    motor = MotorDriver()
    cap = cv2.VideoCapture(0)  # 카메라 장치 (필요시 번호 조정)
    if not cap.isOpened():
        print("카메라를 열 수 없습니다.")
        return

    # 영상 크기 확인 (나중에 중심 좌표 계산에 사용)
    ret, frame = cap.read()
    if not ret:
        print("프레임을 읽을 수 없습니다.")
        return
    frame_height, frame_width = frame.shape[:2]
    frame_center = frame_width // 2

    # PID 제어기 초기화 (튜닝 필요)
    pid = PID(kp=0.1, ki=0.0, kd=0.01)
    base_speed = 30  # 기본 속도 (0~100)
    prev_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("프레임을 읽을 수 없습니다.")
                break

            # 빨간색 라인 검출
            detected, centroid, mask = detect_red_line(frame)

            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            if detected and centroid is not None:
                cx, cy = centroid
                # 영상에 검출된 중심과 기준선(영상 중앙)을 표시 (디버깅용)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                cv2.line(frame, (frame_center, 0), (frame_center, frame_height), (255, 0, 0), 2)
                cv2.putText(frame, f"Centroid: ({cx}, {cy})", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                # 에러 계산: 영상 중심과 라인 중심의 수평 오차 (픽셀 단위)
                error = cx - frame_center
                # PID를 통한 보정값 산출
                correction = pid.update(error, dt)

                # 보정에 따른 좌우 모터 속도 계산
                # (오차가 양수이면 라인이 오른쪽에 있으므로 오른쪽을 줄여서 우회전,
                #  오차가 음수이면 왼쪽에 있으므로 왼쪽 모터 속도를 줄여 좌회전)
                left_speed = base_speed + correction
                right_speed = base_speed - correction

                # 속도 범위 제한 (0~100)
                left_speed = max(0, min(100, left_speed))
                right_speed = max(0, min(100, right_speed))

                # 모터 제어 (양 모터 모두 전진)
                motor.MotorRun(0, 'forward', left_speed)
                motor.MotorRun(1, 'forward', right_speed)

                # 디버깅 정보 출력
                cv2.putText(frame, f"Error: {error:.2f}", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame, f"LSpeed: {left_speed:.1f} RSpeed: {right_speed:.1f}", (10, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                print(f"error: {error:.2f}, correction: {correction:.2f}, left_speed: {left_speed:.1f}, right_speed: {right_speed:.1f}")

            else:
                # 라인이 검출되지 않으면 모터 정지
                motor.MotorStop(0)
                motor.MotorStop(1)
                cv2.putText(frame, "Red line not detected", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                print("빨간 라인을 찾을 수 없습니다.")

            # 결과 영상 및 마스크 디스플레이
            cv2.imshow("Frame", frame)
            cv2.imshow("Mask", mask)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("종료합니다.")

    finally:
        motor.MotorStop(0)
        motor.MotorStop(1)
        cap.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    line_following()
