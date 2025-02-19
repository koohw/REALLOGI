# from flask import Flask, Response, request, jsonify
# from flask_cors import CORS
# import json
# import time
# import threading
# from datetime import datetime
# from dotenv import load_dotenv
# import os 

# from simulation import shared_data, data_lock, simulation_main, mqtt_client, TOPIC_COMMAND_TO_DEVICE

# app = Flask(__name__)
# CORS(app, resources={
#     r"/moni/*": {
#         "origins": "*",
#         "allow_headers": ["Content-Type"],
#         "methods": ["GET", "POST", "OPTIONS"],
#         "expose_headers": ["Content-Type"],
#         "supports_credentials": True,
#         "max_age": 1728000
#     }
# })

# # 전역 변수: 시뮬레이션 시작 여부
# simulation_started = False

# def convert_agv_id(agv_str):
#     """
#     "AGV001" 형태 -> "AGV 1" 으로 변환
#     """
#     if agv_str.upper() == "ALL":
#         return "ALL"
#     try:
#         num = int(agv_str.replace("AGV", ""))
#         return f"AGV {num}"
#     except Exception:
#         return agv_str

# def compute_start_position(agv_key):
#     """
#     AGV의 시작 위치를 계산합니다.
#     시뮬레이션에서는 시작 위치가 (ROWS-1, col)이며,
#     예: AGV 1: (8, 0), AGV 2: (8, 2), AGV 3: (8, 4), AGV 4: (8, 6)
#     """
#     try:
#         index = int(agv_key.split()[1]) - 1
#     except Exception:
#         index = 0
#     col = (index * 2) % 7  # COLS가 7인 경우
#     return (8, col)

# def send_stop_command_to_agv(agv_key):
#     """
#     지정된 AGV(주로 AGV1)에 대해 MQTT로 STOP 명령을 전송합니다.
#     메시지는 {"command": "STOP"} 형태로 전송됩니다.
#     """
#     payload = {"command": "STOP"}
#     result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#     if result[0] == 0:
#         app.logger.info("[SIM] %s STOP 명령 전송 성공: %s", agv_key, payload)
#     else:
#         app.logger.error("[SIM] %s STOP 명령 전송 실패: %s", agv_key, payload)

# @app.route("/moni/agv/stop", methods=["POST"])
# def stop_agv():
#     """
#     AGV 정지 명령:
#       - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
#       - 해당 AGV의 상태를 "STOP"으로 변경하고,
#         만약 AGV1(실제 하드웨어)이 포함되어 있으면 MQTT로 {"command": "STOP"} 메시지를 전송합니다.
#     """
#     data = request.get_json()
#     agvIds = data.get("agvIds", [])
#     results = []
#     with data_lock:
#         if not agvIds or any(x.upper() == "ALL" for x in agvIds):
#             for agv_key in shared_data["positions"]:
#                 shared_data["statuses"][agv_key] = "STOP"
#                 results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
#                 if agv_key == "AGV 1":
#                     send_stop_command_to_agv(agv_key)
#         else:
#             for agv_id in agvIds:
#                 key = convert_agv_id(agv_id)
#                 if key in shared_data["positions"]:
#                     shared_data["statuses"][key] = "STOP"
#                     results.append({"agv_id": agv_id, "status": "success"})
#                     if key == "AGV 1":
#                         send_stop_command_to_agv(key)
#                 else:
#                     results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
#     return jsonify({"success": True, "message": "정지 명령이 전송되었습니다.", "results": results})

# @app.route("/moni/agv/resume", methods=["POST"])
# def resume_agv():
#     """
#     AGV 재시작(RESUME) 명령:
#       - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
#       - STOP 상태인 AGV에 대해 상태를 "RUNNING"으로 변경하고,
#         만약 AGV1(실제 하드웨어)이 포함되어 있다면 MQTT로 {"command": "RESUME"} 메시지를 전송합니다.
#     """
#     data = request.get_json()
#     agvIds = data.get("agvIds", [])
#     results = []
#     with data_lock:
#         if not agvIds or any(x.upper() == "ALL" for x in agvIds):
#             for agv_key in shared_data["positions"]:
#                 if shared_data["statuses"][agv_key] == "STOP":
#                     shared_data["statuses"][agv_key] = "RUNNING"
#                     results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
#                     if agv_key == "AGV 1":
#                         payload = {"command": "RESUME"}
#                         result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#                         if result[0] == 0:
#                             app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", agv_key, payload)
#                         else:
#                             app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", agv_key, payload)
#                 else:
#                     results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "error",
#                                     "error": f"{agv_key}가 STOP 상태가 아닙니다."})
#         else:
#             for agv_id in agvIds:
#                 key = convert_agv_id(agv_id)
#                 if key in shared_data["positions"]:
#                     if shared_data["statuses"][key] == "STOP":
#                         shared_data["statuses"][key] = "RUNNING"
#                         results.append({"agv_id": agv_id, "status": "success"})
#                         if key == "AGV 1":
#                             payload = {"command": "RESUME"}
#                             result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
#                             if result[0] == 0:
#                                 app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", key, payload)
#                             else:
#                                 app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", key, payload)
#                     else:
#                         results.append({"agv_id": agv_id, "status": "error", "error": "AGV가 정지 상태가 아닙니다."})
#                 else:
#                     results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
#     return jsonify({"success": True, "message": "재시작(RESUME) 명령이 전송되었습니다.", "results": results})

# @app.route("/moni/agv/start", methods=["POST"])
# def start_simulation():
#     """
#     AGV 시뮬레이션 시작 명령:
#       - 요청 데이터: { "command": "start" }
#       - 이 명령을 받으면 시뮬레이션을 백그라운드 스레드로 실행합니다.
#       - 웹의 start 버튼을 눌러야 이 라우트가 호출되어 시뮬레이션이 시작됩니다.
#     """
#     global simulation_started
#     data = request.get_json()
#     command = data.get("command", "").lower()
#     if command != "start":
#         return jsonify({"success": False, "message": "잘못된 명령입니다."}), 400

#     with data_lock:
#         if simulation_started:
#             return jsonify({"success": False, "message": "시뮬레이션이 이미 시작되었습니다."}), 400
#         else:
#             simulation_started = True
#             sim_thread = threading.Thread(target=simulation_main, daemon=True)
#             sim_thread.start()
#             return jsonify({"success": True, "message": "시뮬레이션이 시작되었습니다."})

# @app.route("/moni/agv-stream")
# def sse():
#     def event_stream():
#         default_keys = ["AGV 1", "AGV 2", "AGV 3", "AGV 4"]
#         while True:
#             with data_lock:
#                 overall_eff_sum = 0
#                 count = 0
#                 for key in default_keys:
#                     if shared_data["order_completed"][key] > 0:
#                         overall_eff_sum += shared_data["efficiency"].get(key, 0)
#                         count += 1
#                 overall_efficiency = overall_eff_sum / count if count else 0

#                 shared_data["overall_efficiency_history"] = [(datetime.now().isoformat(), overall_efficiency)]
#                 agv_list = []
#                 for key in default_keys:
#                     pos = shared_data["positions"].get(key)
#                     state = shared_data["statuses"].get(key, "")
#                     direction = shared_data["directions"].get(key, "")
#                     logs_list = shared_data["logs"].get(key, [])
#                     realtime = logs_list[-1].get("time", "") if logs_list and isinstance(logs_list[-1], dict) else ""
#                     try:
#                         agv_id = int(key.split()[-1])
#                     except Exception:
#                         agv_id = 0
#                     agv_name = f"agv{agv_id}"
#                     loc_x = pos[0] if pos else ""
#                     loc_y = pos[1] if pos else ""
#                     agv_data = {
#                         "agv_id": key.replace(" ", "0"),
#                         "agv_name": agv_name,
#                         "state": state,
#                         "issue": "",
#                         "location_x": loc_x,
#                         "location_y": loc_y,
#                         "direction": direction,
#                         "realtime": realtime,
#                         "efficiency": shared_data["efficiency"].get(key, 0)
#                     }
#                     agv_list.append(agv_data)

#                 data = {
#                     "success": True,
#                     "agv_number": len(agv_list),
#                     "agvs": agv_list,
#                     "order_success": shared_data.get("order_completed", {}),
#                     "overall_efficiency": overall_efficiency,
#                     "overall_efficiency_history": shared_data["overall_efficiency_history"]
#                 }
#             yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
#             time.sleep(1)
#     response = Response(event_stream(), mimetype="text/event-stream")
#     response.headers.update({
#         'Cache-Control': 'no-cache',
#         'Connection': 'keep-alive',
#         'X-Accel-Buffering': 'no',
#         'Access-Control-Allow-Origin': '*',
#         'Content-Type': 'text/event-stream; charset=utf-8'
#     })
#     return response


# #event_stream(), content_type="text/event-stream")# 
# def start_background_threads():
#     sim_thread = threading.Thread(target=simulation_main, daemon=True)
#     sim_thread.start()

# if __name__ == '__main__':
#     start_background_threads()
#     app.run(debug=False, use_reloader=False, host='0.0.0.0',port=2025)







from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import json
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
import os 

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
    예: AGV 1은 (7, 0), 나머지는 simulation.py의 random_start_position() 로직에 따라 계산됨.
    여기서는 초기화 시 AGV 2~4의 위치를 (11,2), (11,4), (11,6)으로 고정합니다.
    """
    try:
        index = int(agv_key.split()[1])
    except Exception:
        index = 1
    if index == 1:
        return (7, 0)
    elif index == 2:
        return (11, 2)
    elif index == 3:
        return (11, 4)
    elif index == 4:
        return (11, 6)
    else:
        return (11, (index - 1) * 2 % 15)

def send_stop_command_to_agv(agv_key):
    """
    지정된 AGV(주로 AGV1)에 대해 MQTT로 STOP 명령을 전송합니다.
    메시지는 {"command": "STOP"} 형태로 전송됩니다.
    """
    payload = {"command": "STOP"}
    result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
    if result[0] == 0:
        app.logger.info("[SIM] %s STOP 명령 전송 성공: %s", agv_key, payload)
    else:
        app.logger.error("[SIM] %s STOP 명령 전송 실패: %s", agv_key, payload)

@app.route("/moni/agv/stop", methods=["POST"])
def stop_agv():
    """
    AGV 정지 명령:
      - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
      - 해당 AGV의 상태를 "STOP"으로 변경하고,
        만약 AGV1(실제 하드웨어)이 포함되어 있으면 MQTT로 {"command": "STOP"} 메시지를 전송합니다.
    """
    data = request.get_json()
    agvIds = data.get("agvIds", [])
    results = []
    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            for agv_key in shared_data["positions"]:
                shared_data["statuses"][agv_key] = "STOP"
                results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
                if agv_key == "AGV 1":
                    send_stop_command_to_agv(agv_key)
        else:
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    shared_data["statuses"][key] = "STOP"
                    results.append({"agv_id": agv_id, "status": "success"})
                    if key == "AGV 1":
                        send_stop_command_to_agv(key)
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
    return jsonify({"success": True, "message": "정지 명령이 전송되었습니다.", "results": results})

@app.route("/moni/agv/resume", methods=["POST"])
def resume_agv():
    """
    AGV 재시작(RESUME) 명령:
      - 요청 데이터: { "agvIds": ["AGV001", "AGV002", ...] }
      - STOP 상태인 AGV에 대해 상태를 "RUNNING"으로 변경하고,
        만약 AGV1(실제 하드웨어)이 포함되어 있다면 MQTT로 {"command": "RESUME"} 메시지를 전송합니다.
    """
    data = request.get_json()
    agvIds = data.get("agvIds", [])
    results = []
    with data_lock:
        if not agvIds or any(x.upper() == "ALL" for x in agvIds):
            for agv_key in shared_data["positions"]:
                if shared_data["statuses"][agv_key] == "STOP":
                    shared_data["statuses"][agv_key] = "RUNNING"
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "success"})
                    if agv_key == "AGV 1":
                        payload = {"command": "RESUME"}
                        result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
                        if result[0] == 0:
                            app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", agv_key, payload)
                        else:
                            app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", agv_key, payload)
                else:
                    results.append({"agv_id": agv_key.replace("AGV ", "AGV"), "status": "error",
                                    "error": f"{agv_key}가 STOP 상태가 아닙니다."})
        else:
            for agv_id in agvIds:
                key = convert_agv_id(agv_id)
                if key in shared_data["positions"]:
                    if shared_data["statuses"][key] == "STOP":
                        shared_data["statuses"][key] = "RUNNING"
                        results.append({"agv_id": agv_id, "status": "success"})
                        if key == "AGV 1":
                            payload = {"command": "RESUME"}
                            result = mqtt_client.publish(TOPIC_COMMAND_TO_DEVICE, json.dumps(payload))
                            if result[0] == 0:
                                app.logger.info("[SIM] %s RESUME 명령 전송 성공: %s", key, payload)
                            else:
                                app.logger.error("[SIM] %s RESUME 명령 전송 실패: %s", key, payload)
                    else:
                        results.append({"agv_id": agv_id, "status": "error", "error": "AGV가 정지 상태가 아닙니다."})
                else:
                    results.append({"agv_id": agv_id, "status": "error", "error": "지정된 AGV를 찾을 수 없습니다."})
    return jsonify({"success": True, "message": "재시작(RESUME) 명령이 전송되었습니다.", "results": results})

@app.route("/moni/agv/start", methods=["POST"])
def start_simulation():
    """
    AGV 시뮬레이션 시작 명령:
      - 요청 데이터: { "command": "start" }
      - 이 명령을 받으면 시뮬레이션을 백그라운드 스레드로 실행합니다.
      - 단, 이전에 초기화(initialize) 명령으로 시뮬레이션이 종료된 후여야 합니다.
    """
    global simulation_started, simulation_thread
    data = request.get_json()
    command = data.get("command", "").lower()
    if command != "start":
        return jsonify({"success": False, "message": "잘못된 명령입니다."}), 400

    with data_lock:
        # 초기화로 인해 중지된 상태라면 stop 플래그를 해제합니다.
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
    AGV 초기화 명령:
      - 요청 데이터는 아래와 같이 전달됩니다.
            {
              "success": true,
              "message": "작업이 초기화되었습니다."
            }
      - 이 명령이 내려지면 simulation.py 내부의 simpy 환경이 즉시 종료되도록 합니다.
      - 또한, 각 AGV를 원래의 초기 위치로 되돌립니다.
    """
    global simulation_started, simulation_thread
    with data_lock:
        # simpy 종료를 위한 플래그 설정 (simulation_main 내 모니터 프로세스가 이를 체크해야 함)
        shared_data["stop_simulation"] = True
        # 각 AGV를 초기 위치로 재설정 (여기서는 AGV 1: (7,0), AGV 2: (11,2), AGV 3: (11,4), AGV 4: (11,6))
        initial_positions = {
            "AGV 1": (7, 0),
            "AGV 2": (11, 2),
            "AGV 3": (11, 4),
            "AGV 4": (11, 6)
        }
        for key, pos in initial_positions.items():
            shared_data["positions"][key] = pos
            shared_data["logs"][key].append({"time": datetime.now().isoformat(), "position": pos})
    # 시뮬레이션 스레드가 실행 중이라면 종료될 때까지 기다립니다.
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
    # 시뮬레이션은 start 명령이 있을 때만 시작되도록 합니다.
    app.run(debug=False, use_reloader=False, host='0.0.0.0', port=2025)
