from flask import Flask, jsonify
import threading
import paho.mqtt.client as mqtt
import json
import time

BROKER = "broker.hivemq.com"
PORT = 1883
TOPIC_AGV_TO_SIMPY = "agv/status"
TOPIC_SIMPY_TO_AGV = "simpy/commands"

# AGV 상태 저장
agv_status = {
    'location': (0, 0),
    'obstacle': False,
    'qr_detected': False
}

# 명령 기록 저장
command_log = []

# Flask 앱 초기화
app = Flask(__name__)

@app.route('/status', methods=['GET'])
def get_status():
    """AGV 상태 정보를 JSON으로 반환"""
    return jsonify(agv_status)

@app.route('/commands', methods=['GET'])
def get_commands():
    """Simpy에서 보낸 명령 기록을 JSON으로 반환"""
    return jsonify(command_log)

# MQTT 콜백 함수
def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT Broker with result code {rc}")
    client.subscribe(TOPIC_AGV_TO_SIMPY)

def on_message(client, userdata, msg):
    global agv_status
    data = json.loads(msg.payload)
    agv_status.update(data)
    print(f"Received from AGV: {agv_status}")

# MQTT 클라이언트 설정
client = mqtt.Client(protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_message = on_message

# 브로커 연결
client.connect(BROKER, PORT, 60)

# Simpy 명령 전송 함수
def send_command(command, data=None):
    message = {'command': command, 'data': data}
    client.publish(TOPIC_SIMPY_TO_AGV, json.dumps(message))
    command_log.append(message)
    print(f"Sent command to AGV: {message}")

# Simpy 명령 전송 루프
def simpy_controller():
    while True:
        time.sleep(5)
        send_command('ROUTE', {'next_location': (5, 5)})
        if agv_status['obstacle']:
            send_command('STOP')
        elif agv_status['qr_detected']:
            send_command('RESUME')

# Flask 실행 함수
def run_flask():
    app.run(host='0.0.0.0', port=5000)

# 멀티스레드 실행
if __name__ == "__main__":
    # MQTT 클라이언트 루프 시작
    client.loop_start()

    # Flask와 Simpy 컨트롤러를 각각 스레드로 실행
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    try:
        simpy_controller()
    except KeyboardInterrupt:
        print("Stopping Simpy controller...")
        client.loop_stop()
        client.disconnect()
