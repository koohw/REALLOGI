# Jetson Nano Orin용 MPU6050 및 MQTT 센서 데이터 전송 코드
# 주의: 사용중인 I²C 버스 번호가 다를 수 있으니, 센서가 연결된 I²C 버스를 /dev/i2c-*에서 확인 후 수정하세요.
#
# 만약 smbus 라이브러리가 없다면 smbus2를 설치한 후 아래와 같이 import 구문을 변경하세요.
#   pip install smbus2
# 그리고 아래 import 구문을:
from smbus2 import SMBus
# 로 변경한 후, 코드 내 SMBus(7) 호출도 동일하게 사용하면 됩니다.

import time
import math
import json
import numpy as np
import paho.mqtt.client as mqtt

# Jetson 환경에서 I2C 통신을 위해 smbus2를 사용 (만약 smbus가 설치되어 있다면 아래와 같이 변경 가능)
try:
    import smbus
except ImportError:
    from smbus2 import SMBus

# MQTT 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

class KalmanFilter:
    def __init__(self, Q=0.001, R=0.1):
        self.Q = Q
        self.R = R
        self.P = 1.0
        self.X = 0.0
        self.velocity = 0.0

    def update(self, measurement, dt):
        predicted_position = self.X + self.velocity * dt
        self.P = self.P + self.Q
        K = self.P / (self.P + self.R)
        position_error = measurement - predicted_position
        self.X = predicted_position + K * position_error
        if dt > 0:
            self.velocity += K * (position_error / dt)
        self.P = (1 - K) * self.P
        return self.velocity

class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0
        self.accel_scale = 16384.0
        self.init_sensor()
        self.calibrate_sensor()

    def init_sensor(self):
        # MPU6050 초기화: 전원 관리 및 감도 설정
        self.bus.write_byte_data(self.address, 0x6B, 0x00)  # 전원 관리 1 레지스터: 슬립 모드 해제
        self.bus.write_byte_data(self.address, 0x1C, 0x00)  # 가속도 감도 설정
        self.bus.write_byte_data(self.address, 0x1B, 0x00)  # 자이로 감도 설정
        time.sleep(0.1)

    def calibrate_sensor(self):
        accel_sum = [0, 0]
        gyro_sum = 0
        samples = 100
        for _ in range(samples):
            accel = self.get_raw_accel_data()
            gyro = self.get_raw_gyro_data()
            accel_sum[0] += accel['x']
            accel_sum[1] += accel['y']
            gyro_sum += gyro['z']
            time.sleep(0.01)
        self.accel_offset_x = accel_sum[0] / samples
        self.accel_offset_y = accel_sum[1] / samples
        self.gyro_offset_z = gyro_sum / samples

    def read_i2c_word(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) + low
        return -((65535 - val) + 1) if val >= 0x8000 else val

    def get_raw_accel_data(self):
        x = self.read_i2c_word(0x3B)
        y = self.read_i2c_word(0x3D)
        return {'x': x, 'y': y}

    def get_accel_data(self):
        raw = self.get_raw_accel_data()
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        # 센서 장착 방향에 따른 좌표 변환 (내부: x, y → 출력: 앞쪽(-y), 뒤쪽(+y), 오른쪽(+x), 왼쪽(-x))
        return {'x': y, 'y': -x}

    def get_raw_gyro_data(self):
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_gyro_data(self):
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}

def on_connect(client, userdata, flags, rc):
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    command = json.loads(msg.payload)
    if command.get('command') == 'STOP':
        print("AGV 정지 명령 수신")
    elif command.get('command') == 'RESUME':
        print("AGV 재시작 명령 수신")

def main():
    # MQTT 클라이언트 설정
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    # Jetson Nano Orin에서는 연결된 I2C 버스 번호가 다를 수 있으니 확인 후 수정하세요.
    # 예시에서는 /dev/i2c-7에 연결된 것으로 가정합니다.
    bus = smbus.SMBus(7)
    mpu = MPU6050(bus)
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)
   
    # 내부 좌표계: index0 -> x, index1 -> y
    # 문제 설명에 따라 출발지는 (8, 0)로 설정 (출력 순서는 (y, x))
    position = np.array([0.0, 8.0])
    velocity = np.array([0.0, 0.0])
   
    # 시뮬레이션 상 각도 (자이로 데이터로 갱신)
    angle = 0.0  

    # 간단한 노이즈 필터링 계수 및 중력 상수 (m/s^2)
    alpha = 0.1
    gravity = 9.81
    prev_time = time.time()

    # =============================
    # [추가] 이동거리 계산을 위한 변수 초기화 (단위: m)
    distance_traveled = 0.0  
    prev_position = position.copy()
    # =============================

    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            # 센서값 획득
            accel = mpu.get_accel_data()    # 단위: g (보정 후)
            gyro = mpu.get_gyro_data()      # 단위: deg/s (센서에 따라 다름)

            # 자이로 데이터를 이용해 회전각(heading) 갱신
            angle += gyro['z'] * dt

            # 간단한 low-pass 필터 적용 (필요시 추가 오프셋 적용 가능)
            accel_x = alpha * accel['x']
            accel_y = alpha * accel['y']

            # 가속도 값을 월드 좌표계로 변환 (회전 보정)
            accel_world_x = accel_x * math.cos(angle) - accel_y * math.sin(angle)
            accel_world_y = accel_x * math.sin(angle) + accel_y * math.cos(angle)

            # 가속도를 m/s² 단위로 변환 (g → m/s²)
            accel_world_x *= gravity
            accel_world_y *= gravity

            # 원시 속도 추정 (적분)
            raw_vel_x = velocity[0] + accel_world_x * dt
            raw_vel_y = velocity[1] + accel_world_y * dt

            # 칼만 필터로 속도 보정 (m/s 단위)
            velocity[0] = kalman_x.update(raw_vel_x, dt)
            velocity[1] = kalman_y.update(raw_vel_y, dt)

            # 속도 적분으로 위치 추정 (단위: m)
            position[0] += velocity[0] * dt
            position[1] += velocity[1] * dt

            # 미세한 가속도에서는 마찰 효과로 속도 서서히 감소
            if abs(accel_world_x) < 0.02 and abs(accel_world_y) < 0.02:
                velocity *= 0.95

            # 속도를 cm/s 단위로 변환 (1 m/s = 100 cm/s)
            speed_cm_s = math.sqrt(velocity[0]**2 + velocity[1]**2) * 100

            # =============================
            # [추가] 이동거리 계산: 이전 위치와 현재 위치 사이의 이동 거리를 누적 (단위: m)
            delta = np.linalg.norm(position - prev_position)
            distance_traveled += delta
            prev_position = position.copy()
            # =============================

            # MQTT 전송 데이터 구성 (출력 순서: y, x)
            # 이동거리는 cm 단위 (1 m = 100 cm)
            position_data = {
                "y": round(float(position[1]), 2),
                "x": round(float(position[0]), 2),
                "speed": round(speed_cm_s, 2),
                "distance": round(distance_traveled * 100, 2)
            }

            client.publish(TOPIC_AGV_TO_SIMPY, json.dumps(position_data))
            print(f"현재 위치: y={position_data['y']}, x={position_data['x']}, 속도={position_data['speed']} cm/s, 이동거리={position_data['distance']} cm")

            time.sleep(1)

    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
        print("프로그램 종료")

if __name__ == "__main__":
    main()
