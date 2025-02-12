// services/agvService.js

const API_BASE_URL = "http://localhost:5000/api";

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
};
