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
        :param update_callback: AGV 1 위치 변화 시 호출할 함수
        :param agv_id: AGV 식별자 (기본값 "AGV 1")
        """
        self.agv_id = agv_id
        self.position = (0, 0)
        self.client = mqtt.Client(client_id=self.agv_id)
        self.update_callback = update_callback

    def on_connect(self, client, userdata, flags, rc):
        print(f"[AGV1] Connected to MQTT broker (rc={rc})")
        client.subscribe(TOPIC_SUB)

    def on_message(self, client, userdata, msg):
        print(f"[AGV1] Received on {msg.topic}: {msg.payload.decode()}")

    def connect_and_run(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        self.client.connect(BROKER_URL, BROKER_PORT, 60)
        self.client.loop_start()

        while True:
            # 매 1초마다 x 좌표를 +1 (오른쪽 이동)
            x, y = self.position
            self.position = (x + 1, y)

            # 업데이트 콜백 호출: AGV 1은 항상 오른쪽("R")으로 이동하는 것으로 가정
            if self.update_callback:
                self.update_callback(self.agv_id, self.position)

            # MQTT Publish (가상 AGV 1 위치 전송)
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
