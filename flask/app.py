"""
app.py
- Flask 서버 (HTTPS)
- 시뮬레이션(AGV 2,3,4) 단발성 실행
- MQTT(AGV 1) 스레드
- shared_data를 안전하게 업데이트하기 위한 콜백
"""

from flask import Flask, render_template, jsonify
import threading, os
from datetime import datetime

# simulation.py에서 공유 데이터, 락, 시뮬레이션 함수를 가져옴
from simulation import shared_data, data_lock, simulation_once

# MQTT(AGV 1) 코드
from mqtt_agv1 import run_mqtt_agv1_forever

app = Flask(__name__)

def agv1_update_callback(agv_id, position):
    """
    MQTT 스레드(AGV 1)에서 x+1 이동 시마다 호출.
    여기서 shared_data에 "실제 시각" 로그를 기록하여
    안전하게 AGV 1 상태 업데이트.
    """
    with data_lock:
        # AGV1 상태 및 위치 갱신
        shared_data["statuses"][agv_id] = "moving"
        shared_data["positions"][agv_id] = position

        # 로그 추가 (실제 시각)
        shared_data["logs"][agv_id].append({
            "time": datetime.now().isoformat(),
            "position": position,
            "state": "moving",
            "source": "mqtt"
        })

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/logs')
def get_logs():
    # 락을 잡고 데이터를 읽으면 더 안전
    # with data_lock:
    #     return jsonify(shared_data["logs"])
    # error 핸들링 추가
    try:
        with data_lock:
            return jsonify(shared_data["logs"])
    except Exception as e:
        return jsonify({"error" : str(e)}), 500

@app.route('/api/positions')
def get_positions():
    with data_lock:
        return jsonify(shared_data["positions"])

if __name__ == '__main__':
    # 1) AGV 2,3,4 단발성 시뮬레이션
    sim_thread = threading.Thread(target=simulation_once, daemon=True)
    sim_thread.start()

    # 2) AGV 1 (MQTT) 스레드
    mqtt_thread = threading.Thread(
        target=run_mqtt_agv1_forever,
        args=(agv1_update_callback,),
        daemon=True
    )
    mqtt_thread.start()

    # 3) HTTPS로 Flask 서버 실행
    ssl_cert_file = os.path.join(os.path.dirname(__file__), 'cert.pem')
    ssl_key_file = os.path.join(os.path.dirname(__file__), 'key.pem')

    app.run(
        host='0.0.0.0',
        port=5000,
        ssl_context=(ssl_cert_file, ssl_key_file)
    )
