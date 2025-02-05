import smbus
import time
import math
import json
import numpy as np
import paho.mqtt.client as mqtt

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
        self.velocity += K * (position_error / dt)
        self.P = (1 - K) * self.P
        return self.X

class MPU6050:
    def __init__(self, bus, address=0x68):
        self.bus = bus
        self.address = address
        self.gyro_scale = 131.0  # LSB/(도/초)
        self.accel_scale = 16384.0  # LSB/g
        self.init_sensor()
        self.calibrate_sensor()  # 센서 캘리브레이션 추가

    def init_sensor(self):
        # 전원 관리 레지스터 설정
        self.bus.write_byte_data(self.address, 0x6B, 0x00)
        # 가속도계 설정 (±2g)
        self.bus.write_byte_data(self.address, 0x1C, 0x00)
        # 자이로스코프 설정 (±250°/s)
        self.bus.write_byte_data(self.address, 0x1B, 0x00)
        time.sleep(0.1)

    def calibrate_sensor(self):
        """센서 오프셋 캘리브레이션"""
        print("센서 캘리브레이션 중...")
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
        print("캘리브레이션 완료")

    def read_i2c_word(self, reg):
        high = self.bus.read_byte_data(self.address, reg)
        low = self.bus.read_byte_data(self.address, reg + 1)
        val = (high << 8) + low
        return -((65535 - val) + 1) if val >= 0x8000 else val

    def get_raw_accel_data(self):
        """보정되지 않은 가속도 데이터 읽기"""
        x = self.read_i2c_word(0x3B)
        y = self.read_i2c_word(0x3D)
        return {'x': x, 'y': y}

    def get_raw_gyro_data(self):
        """보정되지 않은 자이로스코프 데이터 읽기"""
        z = self.read_i2c_word(0x47)
        return {'z': z}

    def get_accel_data(self):
        """캘리브레이션이 적용된 가속도 데이터 반환"""
        raw = self.get_raw_accel_data()
        x = (raw['x'] - self.accel_offset_x) / self.accel_scale
        y = (raw['y'] - self.accel_offset_y) / self.accel_scale
        # 센서 방향에 따른 좌표계 변환
        return {'x': -y, 'y': x}  # 센서의 좌표계를 실제 움직임에 맞게 변환

    def get_gyro_data(self):
        """캘리브레이션이 적용된 자이로스코프 데이터 반환"""
        raw = self.get_raw_gyro_data()
        z = (raw['z'] - self.gyro_offset_z) / self.gyro_scale
        return {'z': -z}  # 회전 방향 보정

def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC_SIMPY_TO_AGV)

def on_message(client, userdata, msg):
    command = json.loads(msg.payload)
    print(f"Received command: {command}")
    if command['command'] == 'STOP':
        print("AGV stopping...")
    elif command['command'] == 'RESUME':
        print("AGV resuming...")

def main():
    # MQTT 클라이언트 설정
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    bus = smbus.SMBus(1)
    mpu = MPU6050(bus)
    
    kalman_x = KalmanFilter(Q=0.001, R=0.1)
    kalman_y = KalmanFilter(Q=0.001, R=0.1)
    
    position = np.array([0.0, 0.0])  # 초기 위치
    velocity = np.array([0.0, 0.0])  # 초기 속도
    angle = 0.0  # 초기 각도
    
    alpha = 0.1  # 로우패스 필터 계수
    gravity = 9.81  # 중력 가속도 (m/s²)
    prev_time = time.time()
    
    try:
        while True:
            current_time = time.time()
            dt = current_time - prev_time
            prev_time = current_time

            # 센서 데이터 읽기
            accel = mpu.get_accel_data()
            gyro = mpu.get_gyro_data()

            # 각도 업데이트 (역방향으로 회전하도록 수정)
            angle += gyro['z'] * dt

            # 가속도 데이터에 로우패스 필터 적용
            accel_x = alpha * accel['x'] + (1 - alpha) * 0
            accel_y = alpha * accel['y'] + (1 - alpha) * 0

            # 좌표계 변환: 센서 좌표계를 월드 좌표계로 변환
            accel_world_x = accel_x * math.cos(angle) - accel_y * math.sin(angle)
            accel_world_y = accel_x * math.sin(angle) + accel_y * math.cos(angle)

            # 속도 계산
            raw_vel_x = velocity[0] + accel_world_x * gravity * dt
            raw_vel_y = velocity[1] + accel_world_y * gravity * dt
            
            velocity[0] = kalman_x.update(raw_vel_x, dt)
            velocity[1] = kalman_y.update(raw_vel_y, dt)

            # 위치 업데이트
            position[0] += velocity[0] * dt
            position[1] += velocity[1] * dt

            # 정지 상태 감지 및 드리프트 보정
            if abs(accel_world_x) < 0.02 and abs(accel_world_y) < 0.02:
                velocity *= 0.95

            # 위치 데이터 전송
            position_data = {
                "x": round(float(position[0]), 2),
                "y": round(float(position[1]), 2),
                "angle": round(math.degrees(angle), 2)
            }
            
            client.publish(TOPIC_AGV_TO_SIMPY, json.dumps(position_data))
            print(f"위치: x={position_data['x']}, y={position_data['y']}, 각도={position_data['angle']}°")
            print(f"속도: vx={velocity[0]:.2f}, vy={velocity[1]:.2f}")
            print("-" * 50)

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nProgram stopped by user")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
