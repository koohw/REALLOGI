import time
import json
import paho.mqtt.client as mqtt

BROKER_URL = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC_PUB = "my/agv1/position"
TOPIC_SUB = "my/agv1/control"

class AGV1MqttClient:
    def __init__(self, update_callback=None, agv_id="AGV 1"):
        """
        :param update_callback: AGV1 위치 변화 시 호출할 함수
        :param agv_id: AGV 식별자 (기본값 "AGV 1")
        """
        self.agv_id = agv_id
        self.position = (0, 0)
        self.client = mqtt.Client(client_id=self.agv_id)
        self.update_callback = update_callback

    def on_connect(self, client, userdata, flags, rc):
        print(f"[AGV1] Connected to MQTT broker (rc={rc})")
        client.subscribe(TOPIC_SUB)  # 제어 명령 구독 (필요한 경우)

    def on_message(self, client, userdata, msg):
        print(f"[AGV1] Received on {msg.topic}: {msg.payload.decode()}")
        # 필요 시, 메시지를 파싱해 self.position 조정 가능

    def connect_and_run(self):
        """
        브로커 연결 + 매초 x+1 증가 → publish
        update_callback을 통해 Flask 측 shared_data에 로그 추가
        """
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(BROKER_URL, BROKER_PORT, 60)
        self.client.loop_start()

        while True:
            # 단순 예시: x좌표 +1
            x, y = self.position
            self.position = (x + 1, y)

            # Flask 쪽 콜백. 여기서 shared_data 반영 & 로그 기록 수행
            if self.update_callback:
                self.update_callback(self.agv_id, self.position)

            # MQTT Publish (가상 AGV 1 위치)
            data = {
                "agv_id": self.agv_id,
                "position": self.position
            }
            self.client.publish(TOPIC_PUB, json.dumps(data))
            print(f"[AGV1] Published position: {self.position}")

            time.sleep(1)

def run_mqtt_agv1_forever(update_callback):
    agv1_client = AGV1MqttClient(update_callback=update_callback)
    agv1_client.connect_and_run()
