from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime
from simulation import shared_data, data_lock, simulation_main, mqtt_client, TOPIC_COMMAND_TO_DEVICE

app = Flask(__name__)
CORS(app, resources={
    r"/moni/*": {
        "origins": "*",
        "allow_headers": ["Content-Type"],
        "methods": ["GET", "POST", "OPTIONS"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "max_age": 1728000
    }
})

# 전역 변수: 시뮬레이션 스레드 및 시작 여부 관리
simulation_thread = None
simulation_started = False

def convert_agv_id(agv_str):
    """
    "AGV001" 형태 -> "AGV 1" 으로 변환
    """
    if agv_str.upper() == "ALL":
        return "ALL"
    try:
        num = int(agv_str.replace("AGV", ""))
        return f"AGV {num}"
    except Exception:
        return agv_str

def compute_start_position(agv_key):
    """
    AGV의 시작 위치를 계산합니다.
    예: AGV 1은 (7,2), AGV 2: (11,2), AGV 3: (11,4), AGV 4: (11,6)
    """
    try:
        index = int(agv_key.split()[1])
    except Exception:
        index = 1
    if index == 1:
        return (7, 2)
    elif index == 2:
        return (11, 2)
    elif index == 3:
        return (11, 6)
    elif index == 4:
        return (11, 10)
    else:
        return (11, (index - 1) * 2 % 15)

@app.route("/moni/agv/start", methods=["POST"])
def start_simulation():
    """
    작업 시작: start 버튼을 누르면 시뮬레이션을 백그라운드 스레드로 실행합니다.
    """
    global simulation_started, simulation_thread
    data = request.get_json()
    command = data.get("command", "").lower()
    if command != "start":
        return jsonify({"success": False, "message": "잘못된 명령입니다."}), 400

    with data_lock:
        shared_data["stop_simulation"] = False

    if simulation_started:
        return jsonify({"success": False, "message": "시뮬레이션이 이미 시작되었습니다."}), 400
    else:
        simulation_thread = threading.Thread(target=simulation_main, daemon=True)
        simulation_thread.start()
        simulation_started = True
        return jsonify({"success": True, "message": "시뮬레이션이 시작되었습니다."})

@app.route("/moni/agv/initialize", methods=["POST"])
def initialize_agv():
    """
    작업 초기화: initialize 버튼을 누르면 모든 AGV가 즉시 정지하고, 
    초기 위치로 복귀한 후 시뮬레이션(simpy)이 종료됩니다.
    """
    global simulation_started, simulation_thread
    with data_lock:
        shared_data["stop_simulation"] = True
        # 각 AGV의 초기 위치 재설정 (AGV 1: (7,2), AGV 2: (11,2), AGV 3: (11,4), AGV 4: (11,6))
        initial_positions = {
            "AGV 1": (7, 2),
            "AGV 2": (11, 2),
            "AGV 3": (11, 6),
            "AGV 4": (11, 10)
        }
        for key, pos in initial_positions.items():
            shared_data["positions"][key] = pos
            shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": pos})
    if simulation_thread is not None:
        simulation_thread.join(timeout=2)
        simulation_thread = None
        simulation_started = False

    return jsonify({"success": True, "message": "작업이 초기화되었습니다."})

@app.route("/moni/agv-stream")
def sse():
    def event_stream():
        default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
        while True:
            with data_lock:
                overall_eff_sum = 0
                count = 0
                for key in default_keys:
                    if shared_data["order_completed"][key] > 0:
                        overall_eff_sum += shared_data["efficiency"].get(key, 0)
                        count += 1
                overall_efficiency = overall_eff_sum / count if count else 0

                shared_data["overall_efficiency_history"] = [(datetime.now().isoformat(), overall_efficiency)]
                agv_list = []
                for key in default_keys:
                    pos = shared_data["positions"].get(key)
                    state = shared_data["statuses"].get(key, "")
                    direction = shared_data["directions"].get(key, "")
                    logs_list = shared_data["logs"].get(key, [])
                    realtime = logs_list[-1].get("time", "") if logs_list and isinstance(logs_list[-1], dict) else ""
                    try:
                        agv_id = int(key.split()[-1])
                    except Exception:
                        agv_id = 0
                    agv_name = f"agv{agv_id}"
                    loc_x = pos[0] if pos else ""
                    loc_y = pos[1] if pos else ""
                    agv_data = {
                        "agv_id": key.replace(" ", "0"),
                        "agv_name": agv_name,
                        "state": state,
                        "issue": "",
                        "location_x": loc_x,
                        "location_y": loc_y,
                        "direction": direction,
                        "realtime": realtime,
                        "efficiency": shared_data["efficiency"].get(key, 0)
                    }
                    agv_list.append(agv_data)

                data = {
                    "success": True,
                    "agv_number": len(agv_list),
                    "agvs": agv_list,
                    "order_success": shared_data.get("order_completed", {}),
                    "overall_efficiency": overall_efficiency,
                    "overall_efficiency_history": shared_data["overall_efficiency_history"]
                }
            yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            time.sleep(1)
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers.update({
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
        'Access-Control-Allow-Origin': '*',
        'Content-Type': 'text/event-stream; charset=utf-8'
    })
    return response

if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=2025)
