from PCA9685 import PCA9685
import time
import cv2
import numpy as np

# 모터 방향 상수
Dir = ['forward', 'backward']

# PCA9685 초기화
pwm = PCA9685(0x40, debug=True)
pwm.setPWMFreq(50)

# 모터 드라이버 클래스
class MotorDriver():
    def __init__(self):
        self.PWMA = 0
        self.AIN1 = 1
        self.AIN2 = 2
        self.PWMB = 5
        self.BIN1 = 3
        self.BIN2 = 4

    def MotorRun(self, motor, direction, speed):
        if speed > 100:
            return
        if motor == 0:
            pwm.setDutycycle(self.PWMA, speed)
            if direction == Dir[0]:
                pwm.setLevel(self.AIN1, 0)
                pwm.setLevel(self.AIN2, 1)
            else:
                pwm.setLevel(self.AIN1, 1)
                pwm.setLevel(self.AIN2, 0)
        else:
            pwm.setDutycycle(self.PWMB, speed)
            if direction == Dir[0]:
                pwm.setLevel(self.BIN1, 0)
                pwm.setLevel(self.BIN2, 1)
            else:
                pwm.setLevel(self.BIN1, 1)
                pwm.setLevel(self.BIN2, 0)

    def MotorStop(self, motor):
        if motor == 0:
            pwm.setDutycycle(self.PWMA, 0)
        else:
            pwm.setDutycycle(self.PWMB, 0)

# ------------------------------
# 라인트래킹 관련 함수들
# ------------------------------
def get_line_center(frame, threshold_value=123):
    """
    프레임을 받아서 그레이스케일, 블러, 이진화 및 형태학적 처리를 진행한 후
    가장 큰 외곽선의 중심 좌표 (cx, cy)를 반환합니다.
    mask는 디버깅용입니다.
    """
    # 그레이스케일 변환
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # 가우시안 블러 적용
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    # 이진화 (필요에 따라 THRESH_BINARY_INV도 고려)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 11, 2)

    # 형태학적 연산으로 노이즈 제거
    mask = cv2.erode(thresh, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)
    # 외곽선 찾기
    contours, hierarchy = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cx, cy = None, None
    if contours:
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M['m00'] != 0:
            cx = int(M['m10'] / M['m00'])
            cy = int(M['m01'] / M['m00'])
    return cx, cy, mask

def line_tracking_control(Motor, cx, frame_width):
    """
    단순 비례 제어(P control)로 라인의 중심(cx)과 화면 중앙 사이의 오차(error)를 계산하여
    모터 속도를 조정합니다.
    """
    if cx is None:
        # 라인이 검출되지 않으면 두 모터 정지
        Motor.MotorStop(0)
        Motor.MotorStop(1)
        return

    center = frame_width // 2
    error = cx - center
    threshold = 20    # 오차 허용범위 (픽셀 단위)
    base_speed = 50   # 기본 속도

    # 오차가 작으면 직진
    if abs(error) < threshold:
        Motor.MotorRun(0, 'forward', base_speed)
        Motor.MotorRun(1, 'forward', base_speed)
    # 오른쪽으로 치우친 경우 (라인이 오른쪽에 있으면 우측으로 보정)
    elif error > 0:
        # error 값에 비례하여 모터 속도 조정 (왼쪽 모터 속도를 낮춰서 회전)
        left_speed = max(base_speed - int(error/5), 0)
        right_speed = base_speed
        Motor.MotorRun(0, 'forward', left_speed)
        Motor.MotorRun(1, 'forward', right_speed)
    # 왼쪽으로 치우친 경우
    else:
        left_speed = base_speed
        right_speed = max(base_speed - int(-error/5), 0)
        Motor.MotorRun(0, 'forward', left_speed)
        Motor.MotorRun(1, 'forward', right_speed)

# ------------------------------
# 시나리오 함수들 (예시)
# ------------------------------
def scenario1(Motor):
    # 시나리오1 : 150m 이동 (여기서는 10초 전진)
    print("🚀 Scenario 1: Forward")
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'forward', 50)
    time.sleep(10)
    print("🛑 Stop")
    Motor.MotorStop(0)
    Motor.MotorStop(1)
    time.sleep(3)

def scenario2_turn_right(Motor):
    # 시나리오2 : 오른쪽 회전
    print("➡️ Scenario 2: Turn Right")
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'backward', 50)
    time.sleep(1.5)
    print("🛑 Stop")
    Motor.MotorStop(0)
    Motor.MotorStop(1)
    time.sleep(3)

def scenario3(Motor):
    # 시나리오3 : 150m 이동 (10초 전진)
    print("🚀 Scenario 3: Forward")
    Motor.MotorRun(0, 'forward', 50)
    Motor.MotorRun(1, 'forward', 50)
    time.sleep(10)
    print("🛑 Stop")
    Motor.MotorStop(0)
    Motor.MotorStop(1)
    time.sleep(3)

def scenario4_turn_left(Motor):
    # 시나리오4 : 왼쪽 회전
    print("⬅️ Scenario 4: Turn Left")
    Motor.MotorRun(0, 'backward', 50)
    Motor.MotorRun(1, 'forward', 50)
    time.sleep(1.5)
    print("🛑 Stop")
    Motor.MotorStop(0)
    Motor.MotorStop(1)
    time.sleep(3)

# 추가 시나리오는 필요에 따라 함수로 정의하세요.
# 예: scenario5, scenario6, ...

# ------------------------------
# 메인 루프 (상태 기반 실행)
# ------------------------------
def main():
    Motor = MotorDriver()
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # 초기 상태: 'tracking' (라인 트래킹) 상태
    state = 'tracking'
    # 시나리오들을 순차 실행 (리스트에 추가)
    scenarios = [scenario1, scenario2_turn_right, scenario3, scenario4_turn_left]
    scenario_index = 0
    # 마지막 시나리오 실행 후부터 다시 트래킹 시작하는 기준 시각
    last_scenario_time = time.time()

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 라인 트래킹 처리: 라인의 중심 좌표와 마스크 이미지 얻기
        cx, cy, mask = get_line_center(frame)
        
        # 디버깅용: 라인 중심과 화면 중앙에 선 그리기
        if cx is not None and cy is not None:
            cv2.line(frame, (cx, 0), (cx, frame.shape[0]), (255, 0, 0), 1)
            cv2.line(frame, (0, cy), (frame.shape[1], cy), (255, 0, 0), 1)
            cv2.putText(frame, f"cx: {cx}", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        
        cv2.imshow("Frame", frame)
        cv2.imshow("Mask", mask)

        # 키 입력 검사 (종료)
        key = cv2.waitKey(1)
        if key == ord('q'):
            break

        current_time = time.time()
        # 일정 시간(예: 20초) 동안 트래킹 후 시나리오로 전환하도록 함
        if state == 'tracking' and current_time - last_scenario_time > 20:
            state = 'scenario'

        if state == 'tracking':
            # 라인 트래킹 제어 함수 호출
            line_tracking_control(Motor, cx, frame.shape[1])
        elif state == 'scenario':
            # 시나리오 실행
            if scenario_index < len(scenarios):
                scenarios[scenario_index](Motor)
                scenario_index += 1
            else:
                # 모든 시나리오 실행 후 다시 처음부터 시작하거나, 원하는 동작 구현
                scenario_index = 0
            # 시나리오 실행 후 다시 트래킹 상태로 전환
            last_scenario_time = time.time()
            state = 'tracking'

    cap.release()
    cv2.destroyAllWindows()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Ctrl+C로 종료합니다.")
        Motor = MotorDriver()
        Motor.MotorStop(0)
        Motor.MotorStop(1)
