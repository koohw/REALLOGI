// services/agvService.js

// 추후 aws에 배포할 때 API_BASE_URL을 변경해야 함
const API_BASE_URL = "http://localhost:2025/moni";

export const agvService = {
  // AGV 상태 스트림 받기
  getAgvStream: () => {
    return new EventSource(`${API_BASE_URL}/agv-stream`);
  },

  // AGV 정지 명령
  stopAgv: async (agvIds) => {
    return await fetch(`${API_BASE_URL}/agv/stop`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ agvIds }),
    }).then((res) => res.json());
  },

  // AGV 복귀 명령
  returnAgv: async (agvIds) => {
    return await fetch(`${API_BASE_URL}/agv/return`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ agvIds }),
    }).then((res) => res.json());
  },

  // AGV 재가동 명령
  restartAgv: async (agvIds) => {
    return await fetch(`${API_BASE_URL}/agv/restart`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ agvIds }),
    }).then((res) => res.json());
  },

  // AGV 작업 시작 명령 (단순 "start" 명령 전송)
  startAgv: async () => {
    return await fetch(`${API_BASE_URL}/agv/start`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ command: "start" }),
    }).then((res) => res.json());
  },
};
