import paho.mqtt.client as mqtt
import json
import time
import random

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"      # AGV에서 보내는 상태 메시지 토픽
TOPIC_SIMPY_TO_AGV = "simpy/commands"  # AGV에 전달할 명령 메시지 토픽

# 수신 메시지 출력 간격 (초)
PRINT_INTERVAL = 1.0
last_print_time = 0  # 마지막으로 메시지를 출력한 시간

# MQTT 콜백 함수: 연결 시 실행
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[Controller] MQTT 브로커에 성공적으로 연결됨 (rc={rc})")
    else:
        print(f"[Controller] 연결 실패, 반환 코드 {rc}")
    client.subscribe(TOPIC_AGV_TO_SIMPY)  # AGV 상태 메시지를 구독

# MQTT 콜백 함수: 메시지 수신 시 실행
def on_message(client, userdata, msg):
    global last_print_time
    try:
        data = json.loads(msg.payload.decode())
        current_time = time.time()
        # 마지막 출력 이후 PRINT_INTERVAL 이상 경과한 경우에만 출력
        if current_time - last_print_time >= PRINT_INTERVAL:
            print(f"[Controller] 수신한 AGV 상태: {data}")
            last_print_time = current_time
    except Exception as e:
        print(f"[Controller] 메시지 디코딩 오류: {e}")

# MQTT 클라이언트 생성 및 설정
client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_start()

# 명령 발행 함수
def send_command(command, data=None):
    """
    command: "정지", "재개", "경로" 등
    data: 명령에 따른 추가 데이터 (예: {"next_location": (x, y)})
    """
    payload = {"command": command}
    if data is not None:
        payload["data"] = data
    result = client.publish(TOPIC_SIMPY_TO_AGV, json.dumps(payload))
    # publish()는 (result, mid)를 반환하며, result[0]==0이면 성공입니다.
    if result[0] == 0:
        print(f"[Controller] 명령 전송 성공: {payload}")
    else:
        print(f"[Controller] 명령 전송 실패: {payload}")

# 컨트롤러 메인 루프 (예시: 주기적으로 명령을 발행)
try:
    while True:
        # 예시 1: AGV에 정지 명령 전송
        send_command("정지")
        time.sleep(5)
        
        # 예시 2: AGV에 재개 명령 전송
        send_command("재개")
        time.sleep(5)
        
        # 예시 3: AGV에 경로 명령 전송 (새로운 위치로 이동)
        # 여기서는 랜덤 좌표를 예시로 사용합니다.
        new_location = (random.randint(0, 8), random.randint(0, 6))
        send_command("경로", {"next_location": new_location})
        time.sleep(5)

except KeyboardInterrupt:
    print("[Controller] KeyboardInterrupt 발생. 컨트롤러 클라이언트를 종료합니다...")
    client.loop_stop()
    client.disconnect()
