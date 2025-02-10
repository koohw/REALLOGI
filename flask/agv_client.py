import paho.mqtt.client as mqtt
import json
import time
from simulation import shared_data, data_lock, send_command_to_agv1, get_next_position

# MQTT 브로커 및 토픽 설정
BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_STATUS_FROM_DEVICE = "agv/status"      # 잿슨(디바이스)가 상태/ACK 메시지를 송신하는 토픽
TOPIC_COMMAND_TO_DEVICE = "simpy/commands"    # 서버가 잿슨(디바이스)에게 명령을 송신하는 토픽

# 목표 위치 (시뮬레이터 기준)
target_location = (0, 0)

PRINT_INTERVAL = 1.0
last_print_time = 0

# 통신 성공 여부 플래그 (초기에는 False)
comm_success = False

# 전역 콜백 함수 변수 (MQTT ACK 메시지 처리 시 호출할 함수)
mqtt_callback = None

# MQTT 클라이언트 생성 (client_id를 명시하여 경고 해소에 도움)
client = mqtt.Client(client_id="server_client", protocol=mqtt.MQTTv311)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[서버] MQTT 브로커와 연결 성공 (rc={rc}).")
        print("[서버] 잿슨오린나노와의 통신 대기중...")
        client.subscribe(TOPIC_STATUS_FROM_DEVICE)
    else:
        print(f"[서버] MQTT 연결 실패, 반환 코드 {rc}")

def on_message(client, userdata, msg):
    """
    잿슨(디바이스)에서 송신한 상태/ACK 또는 돌발 상황 메시지를 처리합니다.
    - 메시지에 'ack' 키가 있으면 이동 완료(ACK)로 인식하고 통신 성공 플래그를 설정합니다.
    - 메시지에 "status": "emergency"가 있으면 AGV의 상태를 "EMERGENCY(STOPPED)"로 업데이트합니다.
    - 그 외 메시지는 통신 성공 후에만 출력합니다.
    """
    global last_print_time, comm_success, mqtt_callback
    try:
        message = json.loads(msg.payload.decode())
        current_time = time.time()
        if current_time - last_print_time >= PRINT_INTERVAL:
            if message.get("status") == "emergency":
                # 돌발 상황 신호 수신 시 상태를 "EMERGENCY(STOPPED)"로 업데이트
                print("[서버] 돌발상황 발생 신호 수신!")
                with data_lock:
                    shared_data["statuses"]["AGV 1"] = "EMERGENCY(STOPPED)"
            elif message.get("ack") is True:
                comm_success = True
                # AGV1의 현재 위치는 shared_data에서 읽어옴 (기본값 (8,0))
                new_location = tuple(message.get("location", shared_data["positions"].get("AGV 1", (8, 0))))
                with data_lock:
                    shared_data["positions"]["AGV 1"] = new_location
                print(f"[서버] 잿슨오린나노와 통신 성공: 이동 완료(ACK) 수신, 현재 위치: {new_location}")
                if mqtt_callback is not None:
                    state = message.get("state", "moving")
                    mqtt_callback(1, new_location, state)
            else:
                if comm_success:
                    status_state = message.get("state", "unknown")
                    location = message.get("location", shared_data["positions"].get("AGV 1", (8, 0)))
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
    """
    서버가 잿슨(디바이스)로 명령을 전송하는 함수입니다.
    예: '정지', '재개', '경로' 등의 명령을 전송
    """
    payload = {"command": command}
    if data is not None:
        payload["data"] = data
    result = client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        print(f"[서버] 명령 전송 성공: {payload}")
    else:
        print(f"[서버] 명령 전송 실패: {payload}")

def publish_path_command():
    """
    시뮬레이션을 기반으로 잿슨(디바이스)로 '경로' 명령을 주기적으로 전송합니다.
    - 현재 위치는 shared_data["positions"]["AGV 1"]에서 읽어오고,
      목표(target_location)를 바탕으로 get_next_position()을 호출하여
      다음 칸(next_location)을 계산합니다.
    - 만약 다음 칸이 현재 위치와 동일하면(즉, 더 이상 이동 불가능) '정지' 명령을 발행합니다.
    """
    global target_location
    while True:
        with data_lock:
            current_location = shared_data["positions"].get("AGV 1", (8, 0))
        next_location = get_next_position(current_location, target_location)
        if next_location == current_location:
            send_command("정지")
        else:
            send_command("경로", {"next_location": list(next_location)})
        time.sleep(5)

def run_server_mqtt(callback=None):
    """
    서버 측 MQTT 통신을 무한 실행합니다.
    callback: 잿슨(디바이스)에서 ACK 메시지 수신 시 호출할 함수.
              예) callback(agv_id, new_position, state)
    """
    global mqtt_callback
    mqtt_callback = callback
    try:
        publish_path_command()
    except KeyboardInterrupt:
        print("[서버] KeyboardInterrupt 발생. MQTT 클라이언트를 종료합니다...")
        client.loop_stop()
        client.disconnect()
        print("[서버] 종료합니다.")

if __name__ == "__main__":
    run_server_mqtt()
