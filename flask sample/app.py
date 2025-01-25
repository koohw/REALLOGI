from flask import Flask, render_template, jsonify
import threading

# 시뮬레이션(AGV 2,3,4)에서 사용하는 shared_data, 실행 함수
from simulation import shared_data, run_simulation_forever

# AGV 1 MQTT 실행 함수
from mqtt_agv1 import run_mqtt_agv1_forever

app = Flask(__name__)

# -------------------------
# 1) MQTT -> Flask 콜백
# -------------------------
def agv1_update_callback(agv_id, position):
    """
    AGV 1의 위치가 갱신될 때마다 호출됨.
    여기서 simulation.py의 shared_data에 반영.
    """
    # 상태를 moving으로 가정 (필요 시 로직 보강)
    shared_data["statuses"][agv_id] = "moving"
    shared_data["positions"][agv_id] = position

    # 로그에 기록 (source="mqtt")
    shared_data["logs"][agv_id].append({
        "time": "mqtt",  # SimPy env.now를 못쓰므로 임의로 "mqtt" 표시
        "position": position,
        "state": "moving",
        "source": "mqtt"
    })

# -------------------------
# 2) Flask 라우트
# -------------------------
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/logs', methods=['GET'])
def get_logs():
    """ 모든 AGV(1~4)의 이동 로그 반환 """
    return jsonify(shared_data["logs"])

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """ 모든 AGV(1~4)의 현재 좌표 반환 """
    return jsonify(shared_data["positions"])

# -------------------------
# 3) 앱 실행
# -------------------------
if __name__ == '__main__':
    # (1) SimPy 시뮬레이션 스레드 (AGV 2,3,4)
    sim_thread = threading.Thread(target=run_simulation_forever, daemon=True)
    sim_thread.start()

    # (2) MQTT 스레드 (AGV 1)
    mqtt_thread = threading.Thread(
        target=run_mqtt_agv1_forever, 
        args=(agv1_update_callback,),
        daemon=True
    )
    mqtt_thread.start()

    # (3) Flask 서버
    app.run(host='0.0.0.0', port=5000)
