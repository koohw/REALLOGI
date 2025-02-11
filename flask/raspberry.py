# raspberry.py
import paho.mqtt.client as mqtt
import json
import time

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"

# 라즈베리파이에서 오는 가장 최신의 센서 데이터를 저장할 전역 변수
rasp_latest_data = {}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[Server] MQTT 브로커 연결 성공!")
    else:
        print(f"[Server] 연결 실패, 반환 코드: {rc}")

    # 라즈베리파이 측 코드가 publish하는 토픽 구독
    client.subscribe(TOPIC_AGV_TO_SIMPY)

def on_message(client, userdata, msg):
    global rasp_latest_data
    try:
        data = json.loads(msg.payload.decode())
        rasp_latest_data = data  # 최신 데이터 갱신
        print(f"[Server] 라즈베리 데이터 수신: {data}")
    except Exception as e:
        print("[Server] 메시지 처리 오류:", e)

def start_rasp_subscriber():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    try:
        while True:
            # 필요하다면 rasp_latest_data를 계속 확인하거나, 다른 처리 로직 수행
            time.sleep(1)
    except KeyboardInterrupt:
        print("[Server] KeyboardInterrupt -> MQTT 종료")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    start_rasp_subscriber()




# import paho.mqtt.client as mqtt
# import json
# import time

# BROKER = "broker.hivemq.com"
# PORT = 1883
# TOPIC_AGV_TO_SIMPY = "agv/status"

# # 라즈베리파이에서 오는 최신 센서 데이터를 저장할 전역 변수
# rasp_latest_data = {}

# def normalize_raspberry_data(raw_data):
#     """
#     원시 라즈베리 센서 데이터를 가상의 AGV 데이터 형식으로 변환합니다.
#     여기서는 예시로:
#       - x, y 값을 반올림하여 정수 좌표로 사용 (필요에 따라 스케일 조정 가능)
#       - speed 값이 0보다 크면 'moving', 아니면 'idle'
#       - realtime은 현재 time.time()을 사용
#     """
#     try:
#         x = raw_data.get("x", 0)
#         y = raw_data.get("y", 0)
#         speed = raw_data.get("speed", 0)
#         normalized = {
#             "agv_id": 1,               # 이 센서 데이터가 AGV1에 해당한다고 가정
#             "agv_name": "agv1",
#             "state": "moving" if speed > 0 else "idle",
#             "issue": "",
#             # 필요에 따라 스케일링 또는 좌표 변환을 적용합니다.
#             "location_x": int(round(x * 10)),  # 예: 소수점 데이터를 10배 확대 후 정수화
#             "location_y": int(round(y * 10)),
#             "direction": "",           # 추가 계산 가능하면 넣을 수 있음
#             "realtime": time.time()
#         }
#         return normalized
#     except Exception as e:
#         print("[Server] 정제 함수 오류:", e)
#         return raw_data

# def on_connect(client, userdata, flags, rc):
#     if rc == 0:
#         print("[Server] MQTT 브로커 연결 성공!")
#     else:
#         print(f"[Server] 연결 실패, 반환 코드: {rc}")
#     # 라즈베리파이에서 발행하는 토픽 구독
#     client.subscribe(TOPIC_AGV_TO_SIMPY)

# def on_message(client, userdata, msg):
#     global rasp_latest_data
#     try:
#         data = json.loads(msg.payload.decode())
#         # 받은 원시 데이터를 정제합니다.
#         normalized_data = normalize_raspberry_data(data)
#         rasp_latest_data = normalized_data  # 최신 데이터를 업데이트
#         print(f"[Server] 라즈베리 데이터 수신 (정제됨): {normalized_data}")
#     except Exception as e:
#         print("[Server] 메시지 처리 오류:", e)

# def start_rasp_subscriber():
#     client = mqtt.Client()
#     client.on_connect = on_connect
#     client.on_message = on_message
#     client.connect(BROKER, PORT, 60)
#     client.loop_start()

#     try:
#         while True:
#             # DataManager 같은 클래스를 사용해서 저장할 수도 있음.
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("[Server] KeyboardInterrupt -> MQTT 종료")
#         client.loop_stop()
#         client.disconnect()

# if __name__ == "__main__":
#     start_rasp_subscriber()
