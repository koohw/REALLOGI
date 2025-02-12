# import paho.mqtt.client as mqtt
# import json
# import time
# from simulation import map_data, ROWS, COLS, send_command_to_agv1, get_next_position, DEBUG_MODE  # simulation.py가 동일 디렉토리에 있어야 함

# # MQTT 브로커 및 토픽 설정
# BROKER = "broker.hivemq.com"
# PORT = 1883
# TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어가 상태/ACK 메시지를 송신하는 토픽
# TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 서버가 하드웨어로 명령을 송신하는 토픽

# # 초기 위치
# current_location = (8, 0)
# # 테스트 모드에서는 도착 상태를 (0,0)으로, 운영 모드에서는 도착지점 없이 계속 움직임
# if DEBUG_MODE:
#     target_location = (0, 0)
# else:
#     target_location = None

# PRINT_INTERVAL = 1.0
# last_print_time = 0

# comm_success = False
# mqtt_callback = None
# last_sent_command = None

# client = mqtt.Client(client_id="server_client", protocol=mqtt.MQTTv311)

# def on_connect(client, userdata, flags, rc):
#     if rc == 0:
#         print(f"[서버] MQTT 브로커와 연결 성공 (rc={rc}).")
#         print("[서버] 하드웨어와의 통신 대기중...")
#         client.subscribe(TOPIC_STATUS_FROM_DEVICE)
#     else:
#         print(f"[서버] MQTT 연결 실패, 반환 코드 {rc}")

# def on_message(client, userdata, msg):
#     global current_location, last_print_time, comm_success, mqtt_callback
#     try:
#         message = json.loads(msg.payload.decode())
#         current_time = time.time()
#         if current_time - last_print_time >= PRINT_INTERVAL:
#             if message.get("ack") is True:
#                 # 하드웨어의 첫 ACK 수신 시 "하드웨어 연결 성공" 메시지 출력
#                 if not comm_success:
#                     print("[서버] 하드웨어 연결 성공")
#                 comm_success = True
#                 new_location = tuple(message.get("location", current_location))
#                 current_location = new_location
#                 print(f"[서버] 하드웨어와 통신 성공: 이동 완료(ACK) 수신, 현재 위치: {new_location}")
#                 # ACK 수신 시 다음 명령 전송
#                 send_next_command()
#                 if mqtt_callback is not None:
#                     state = message.get("state", "moving")
#                     mqtt_callback(1, new_location, state)
#             else:
#                 if comm_success:
#                     status_state = message.get("state", "unknown")
#                     location = message.get("location", current_location)
#                     obstacle = message.get("obstacle", None)
#                     qr_detected = message.get("qr_detected", None)
#                     print(f"[서버] 상태 메시지 수신 - 위치: {location}, 상태: {status_state}", end="")
#                     if obstacle is not None:
#                         print(f", 장애물 감지: {obstacle}", end="")
#                     if qr_detected is not None:
#                         print(f", QR 인식: {qr_detected}", end="")
#                     print()
#             last_print_time = current_time
#     except Exception as e:
#         print(f"[서버] 메시지 처리 오류: {e}")

# client.on_connect = on_connect
# client.on_message = on_message

# print("[서버] MQTT 클라이언트 연결 시도 중...")
# client.connect(BROKER, PORT, 60)
# client.loop_start()

# def send_command(command, data=None):
#     payload = {"command": command}
#     if data is not None:
#         payload["data"] = data
#     result = client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#     if result[0] == 0:
#         print(f"[서버] 명령 전송 성공: {payload}")
#     else:
#         print(f"[서버] 명령 전송 실패: {payload}")

# def send_next_command():
#     global current_location, target_location, last_sent_command
#     next_location = get_next_position(current_location, target_location)
#     # 운영 모드에서는 target_location이 None이므로 항상 경로 명령 전송
#     if target_location is None:
#         if last_sent_command != tuple(next_location):
#             send_command("경로", {"next_location": list(next_location)})
#             last_sent_command = tuple(next_location)
#         else:
#             print("[서버] 동일한 '경로' 명령은 전송하지 않음.")
#     else:
#         if next_location == current_location:
#             if last_sent_command != "STOP":
#                 send_command("STOP")
#                 last_sent_command = "STOP"
#             else:
#                 print("[서버] 이미 도착 상태로 'STOP' 명령 전송됨.")
#         else:
#             if last_sent_command != tuple(next_location):
#                 send_command("경로", {"next_location": list(next_location)})
#                 last_sent_command = tuple(next_location)
#             else:
#                 print("[서버] 동일한 '경로' 명령은 전송하지 않음.")

# def run_server_mqtt(callback=None):
#     global mqtt_callback
#     mqtt_callback = callback
#     try:
#         send_next_command()
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         print("[서버] KeyboardInterrupt 발생. MQTT 클라이언트를 종료합니다...")
#         client.loop_stop()
#         client.disconnect()
#         print("[서버] 종료합니다.")

# if __name__ == "__main__":
#     run_server_mqtt()

import paho.mqtt.client as mqtt
import json
import time
from simulation import map_data, ROWS, COLS, send_command_to_agv1, get_next_position, DEBUG_MODE, production_route  
# production_route는 simulation.py에 정의됨

# MQTT 브로커 및 토픽 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 하드웨어가 상태/ACK 메시지를 송신하는 토픽
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 서버가 하드웨어로 명령을 송신하는 토픽

# 초기 위치 및 목표 설정
current_location = (8, 0)
# 테스트 모드(DEBUG_MODE=True)에서는 도착 상태를 (0,0)으로, 운영 모드에서는 production_route를 사용
if DEBUG_MODE:
    target_location = (0, 0)
else:
    target_location = production_route[0]

# 메시지 전송 주기 관련 설정
PRINT_INTERVAL = 1.0  # 상태 메시지 출력 간격 (초)
last_print_time = 0

# MQTT 통신 관련 플래그 및 콜백 변수들
comm_success = False      # 하드웨어와의 통신 성공 여부 플래그
mqtt_callback = None      # ACK 수신 시 호출할 콜백 함수
last_sent_command = None  # 마지막으로 전송한 명령 (중복 전송 방지용)

# 마지막으로 전송한 AGV1의 방향을 저장하는 전역 변수
last_direction = ""

# MQTT 클라이언트 생성 (client_id를 명시하여 고유하게 설정)
client = mqtt.Client(client_id="server_client", protocol=mqtt.MQTTv311)

# ----------------------------------------------------------------------------------
# on_connect: MQTT 브로커에 연결되었을 때 호출되는 콜백 함수
# ----------------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[서버] MQTT 브로커와 연결 성공 (rc={rc}).")
        print("[서버] 하드웨어와의 통신 대기중...")
        # 하드웨어가 메시지를 보내는 토픽을 구독합니다.
        client.subscribe(TOPIC_STATUS_FROM_DEVICE)
    else:
        print(f"[서버] MQTT 연결 실패, 반환 코드 {rc}")

# ----------------------------------------------------------------------------------
# on_message: 브로커로부터 메시지를 수신할 때 호출되는 콜백 함수
# - ACK 메시지인 경우: 하드웨어와 통신 성공, 위치 업데이트, 방향 변화에 따른 정지 명령 처리, 다음 명령 전송
# - ACK가 아닌 상태 메시지인 경우: 상태 정보 출력
# ----------------------------------------------------------------------------------
def on_message(client, userdata, msg):
    global current_location, last_print_time, comm_success, mqtt_callback, last_direction, target_location
    try:
        # 수신한 메시지를 JSON 디코딩
        message = json.loads(msg.payload.decode())
        current_time = time.time()
        # 출력 주기 제한: PRINT_INTERVAL 초마다 처리
        if current_time - last_print_time >= PRINT_INTERVAL:
            # ACK 메시지인 경우
            if message.get("ack") is True:
                # 최초 ACK 수신 시 하드웨어 연결 성공 메시지 출력
                if not comm_success:
                    print("[서버] 하드웨어 연결 성공")
                comm_success = True
                # 하드웨어 측에서 전송한 현재 위치를 업데이트
                new_location = tuple(message.get("location", current_location))
                current_location = new_location

                # 새 방향 정보: 메시지에 "direction" 키가 있으면 그 값을 사용
                new_direction = message.get("direction", "")
                # 이전에 전송한 방향과 비교하여 변화가 있으면
                if new_direction != last_direction:
                    # QR 인식 여부에 따라 정지 명령 전송 여부 결정
                    if not message.get("qr_detected", False):
                        print("[서버] 방향 변경 감지됨: QR 미인식 상태 -> 정지 명령 미전송")
                    else:
                        print("[서버] QR 인식됨. 정지 명령 전송")
                        send_command("STOP")
                # 마지막 전송 방향 업데이트
                last_direction = new_direction

                print(f"[서버] 하드웨어와 통신 성공: 이동 완료(ACK) 수신, 현재 위치: {new_location}")
                # 운영 모드일 경우, 도착한 위치가 목표(target_location)와 같으면 production_route에서 다음 목표로 업데이트
                if not DEBUG_MODE:
                    if new_location == target_location:
                        try:
                            idx = production_route.index(target_location)
                            target_location = production_route[(idx + 1) % len(production_route)]
                        except Exception:
                            target_location = production_route[0]
                # 다음 명령 전송
                send_next_command()
                # 등록된 콜백이 있다면 호출 (예: AGV1 상태 업데이트)
                if mqtt_callback is not None:
                    state = message.get("state", "moving")
                    mqtt_callback(1, new_location, state)
            else:
                # ACK가 아닌 상태 메시지 처리 (예: 장애물, QR 인식 정보 등)
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

# MQTT 클라이언트에 콜백 함수 등록
client.on_connect = on_connect
client.on_message = on_message

# ----------------------------------------------------------------------------------
# MQTT 클라이언트 연결 및 루프 시작
# ----------------------------------------------------------------------------------
print("[서버] MQTT 클라이언트 연결 시도 중...")
client.connect(BROKER, PORT, 60)
client.loop_start()

# ----------------------------------------------------------------------------------
# send_command: 서버가 하드웨어로 명령을 전송하는 함수
# - command: 전송할 명령 (예: "경로", "STOP" 등)
# - data: 명령에 포함할 추가 데이터 (예: 다음 좌표)
# ----------------------------------------------------------------------------------
def send_command(command, data=None):
    payload = {"command": command}
    if data is not None:
        payload["data"] = data
    result = client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        print(f"[서버] 명령 전송 성공: {payload}")
    else:
        print(f"[서버] 명령 전송 실패: {payload}")

# ----------------------------------------------------------------------------------
# send_next_command: 현재 위치와 목표(target_location)에 따라 다음 좌표를 계산해 "경로" 명령을 전송
# ----------------------------------------------------------------------------------
def send_next_command():
    global current_location, target_location, last_sent_command
    next_location = get_next_position(current_location, target_location)
    # 중복 전송을 방지하기 위해 이전에 전송한 명령과 비교
    if last_sent_command != tuple(next_location):
        send_command("경로", {"next_location": list(next_location)})
        last_sent_command = tuple(next_location)
    else:
        print("[서버] 동일한 '경로' 명령은 전송하지 않음.")

# ----------------------------------------------------------------------------------
# run_server_mqtt: MQTT 클라이언트 루프를 실행하는 함수
# - 선택적으로 ACK 수신 시 호출할 콜백(callback)을 등록할 수 있음
# ----------------------------------------------------------------------------------
def run_server_mqtt(callback=None):
    global mqtt_callback
    mqtt_callback = callback
    try:
        # 초기 명령 전송
        send_next_command()
        # 무한 루프: 1초마다 대기 (MQTT 클라이언트는 백그라운드에서 동작)
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[서버] KeyboardInterrupt 발생. MQTT 클라이언트를 종료합니다...")
        client.loop_stop()
        client.disconnect()
        print("[서버] 종료합니다.")

# ----------------------------------------------------------------------------------
# 메인 실행부
# ----------------------------------------------------------------------------------
if __name__ == "__main__":
    run_server_mqtt()
