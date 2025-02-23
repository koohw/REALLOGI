import axios from "axios";
// 추후 aws에 배포할 때 API_BASE_URL을 변경해야 함
const API_BASE_URL = process.env.REACT_APP_API_URL;

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export const agvService = {
  // AGV 상태 스트림 받기
  getAgvStream: () => {
    const streamUrl = API_BASE_URL + "/moni/agv-stream";
    return new EventSource(streamUrl, {
      withCredentials: true,
    });
  },

  // AGV 정지 명령
  stopAgv: async (agvIds) => {
    return await apiClient.post("/moni/agv/stop", { agvIds });
  },

  // AGV 복귀 명령
  returnAgv: async (agvIds) => {
    return await apiClient.post("/moni/agv/return", { agvIds });
  },

  // AGV 재가동 명령
  restartAgv: async (agvIds) => {
    return await apiClient.post("/moni/agv/restart", { agvIds });
  },

  // AGV 작업 시작 명령
  startAgv: async () => {
    return await apiClient.post("/moni/agv/start", { command: "start" });
  },

  // AGV 작업 초기화 명령
  initializeAgv: async () => {
    return await apiClient.post("/moni/agv/initialize");
  },
};
