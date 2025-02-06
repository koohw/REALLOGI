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
