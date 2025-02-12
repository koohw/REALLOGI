# agv_client.py

import paho.mqtt.client as mqtt
import json
import time
from simulation import map_data, ROWS, COLS, send_command_to_agv1, get_next_position, DEBUG_MODE  # simulation.py가 동일 디렉토리에 있어야 함

# MQTT 브로커 및 토픽 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어가 상태/ACK 메시지를 송신하는 토픽
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 서버가 하드웨어로 명령을 송신하는 토픽

# 초기 위치
current_location = (8, 0)
# 테스트 모드에서는 도착 상태를 (0,0)으로, 운영 모드에서는 도착지점 없이 계속 움직임
if DEBUG_MODE:
    target_location = (0, 0)
else:
    target_location = None

PRINT_INTERVAL = 1.0
last_print_time = 0

comm_success = False
mqtt_callback = None
last_sent_command = None

client = mqtt.Client(client_id="server_client", protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[서버] MQTT 브로커와 연결 성공 (rc={rc}).")
        print("[서버] 하드웨어와의 통신 대기중...")
        client.subscribe(TOPIC_STATUS_FROM_DEVICE)
    else:
        print(f"[서버] MQTT 연결 실패, 반환 코드 {rc}")

def on_message(client, userdata, msg):
    global current_location, last_print_time, comm_success, mqtt_callback
    try:
        message = json.loads(msg.payload.decode())
        current_time = time.time()
        if current_time - last_print_time >= PRINT_INTERVAL:
            if message.get("ack") is True:
                # 하드웨어의 첫 ACK 수신 시 "하드웨어 연결 성공" 메시지 출력
                if not comm_success:
                    print("[서버] 하드웨어 연결 성공")
                comm_success = True
                new_location = tuple(message.get("location", current_location))
                current_location = new_location
                print(f"[서버] 하드웨어와 통신 성공: 이동 완료(ACK) 수신, 현재 위치: {new_location}")
                # ACK 수신 시 다음 명령 전송
                send_next_command()
                if mqtt_callback is not None:
                    state = message.get("state", "moving")
                    mqtt_callback(1, new_location, state)
            else:
                if comm_success:
                    status_state = message.get("state", "unknown")
                    location = message.get("location", current_location)
                    obstacle = message.get("obstacle", None)
                    qr_detected = message.get("qr_detected", None)
                    print(f"[서버] 상태 메시지 수신 - 위치: {location}, 상태: {status_state}", end="")
                    if obstacle is not None:
                        print(f", 장애물 감지: {obstacle}", end="")
                    if qr_detected is not None:
                        print(f", QR 인식: {qr_detected}", end="")
                    print()
            last_print_time = current_time
    except Exception as e:
        print(f"[서버] 메시지 처리 오류: {e}")

client.on_connect = on_connect
client.on_message = on_message

print("[서버] MQTT 클라이언트 연결 시도 중...")
client.connect(BROKER, PORT, 60)
client.loop_start()

def send_command(command, data=None):
    payload = {"command": command}
    if data is not None:
        payload["data"] = data
    result = client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        print(f"[서버] 명령 전송 성공: {payload}")
    else:
        print(f"[서버] 명령 전송 실패: {payload}")

def send_next_command():
    global current_location, target_location, last_sent_command
    next_location = get_next_position(current_location, target_location)
    # 운영 모드에서는 target_location이 None이므로 항상 경로 명령 전송
    if target_location is None:
        if last_sent_command != tuple(next_location):
            send_command("경로", {"next_location": list(next_location)})
            last_sent_command = tuple(next_location)
        else:
            print("[서버] 동일한 '경로' 명령은 전송하지 않음.")
    else:
        if next_location == current_location:
            if last_sent_command != "STOP":
                send_command("STOP")
                last_sent_command = "STOP"
            else:
                print("[서버] 이미 도착 상태로 'STOP' 명령 전송됨.")
        else:
            if last_sent_command != tuple(next_location):
                send_command("경로", {"next_location": list(next_location)})
                last_sent_command = tuple(next_location)
            else:
                print("[서버] 동일한 '경로' 명령은 전송하지 않음.")

def run_server_mqtt(callback=None):
    global mqtt_callback
    mqtt_callback = callback
    try:
        send_next_command()
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[서버] KeyboardInterrupt 발생. MQTT 클라이언트를 종료합니다...")
        client.loop_stop()
        client.disconnect()
        print("[서버] 종료합니다.")

if __name__ == "__main__":
    run_server_mqtt()










# def calculate_full_path(start, goal, obstacles=set()):
#     path = bfs_path(map_data, start, goal, obstacles)
#     if path is None:
#         logging.warning("경로 탐색 실패: 시작 %s, 목표 %s", start, goal)
#     return path





# def send_full_path(path):
#     payload = {"command": "PATH", "data": {"full_path": path}}
#     result = client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#     if result[0] == 0:
#         print(f"[서버] 전체 경로 전송 성공: {payload}")
#     else:
#         print(f"[서버] 전체 경로 전송 실패: {payload}")
