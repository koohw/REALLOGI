import paho.mqtt.client as mqtt
import json
import time

# MQTT 브로커 및 토픽 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # ACK 및 상태 메시지 전송용 토픽
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 서버에서 명령 수신용 토픽

# 초기 위치 설정 (simulation.py와 일치해야 함)
current_position = [8, 0]

def on_connect(client, userdata, flags, rc):
    print(f"[가상 하드웨어] MQTT 브로커 연결 성공 (rc={rc})")
    client.subscribe(TOPIC_COMMAND_TO_DEVICE)

def on_message(client, userdata, msg):
    global current_position
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        if command == "PATH":
            full_path = payload.get("data", {}).get("full_path", [])
            if full_path:
                print(f"[가상 하드웨어] 전체 경로 명령 수신: {full_path}")
                # 전체 경로를 순차적으로 따라 이동 (각 좌표마다 1초 지연)
                for pos in full_path:
                    time.sleep(1)
                    current_position = pos
                    # 이동 완료 후 ACK 메시지 전송
                    ack_payload = {
                        "ack": True,
                        "location": current_position,
                        "state": "moving"
                    }
                    client.publish(TOPIC_STATUS_FROM_DEVICE, json.dumps(ack_payload))
                    print(f"[가상 하드웨어] 이동 완료, 현재 위치: {current_position}")
        elif command == "STOP":
            print("[가상 하드웨어] STOP 명령 수신, 이동 정지")
            ack_payload = {
                "ack": True,
                "location": current_position,
                "state": "stopped"
            }
            client.publish(TOPIC_STATUS_FROM_DEVICE, json.dumps(ack_payload))
        else:
            print(f"[가상 하드웨어] 미확인 명령 수신: {command}")
    except Exception as e:
        print(f"[가상 하드웨어] 메시지 처리 오류: {e}")

client = mqtt.Client(client_id="virtual_agv1")
client.on_connect = on_connect
client.on_message = on_message

print("[가상 하드웨어] MQTT 클라이언트 연결 시도 중...")
client.connect(BROKER, PORT, 60)
client.loop_forever()
