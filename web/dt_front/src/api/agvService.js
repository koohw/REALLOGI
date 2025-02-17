// services/agvService.js
import axios from 'axios';
// 추후 aws에 배포할 때 API_BASE_URL을 변경해야 함
const API_BASE_URL = process.env.REACT_APP_API_URL;

const apiClient = axios.create({
  baseURL: API_BASE_URL,  // BASE_URL을 API_BASE_URL로 수정
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

const streamClient = axios.create({
  baseURL: API_BASE_URL,  // BASE_URL을 API_BASE_URL로 수정
  withCredentials: true,
  headers: {
    'Content-Type': 'text/event-stream'  // "stream"을 올바른 MIME 타입으로 수정
  }
});

export const agvService = {
  // AGV 상태 스트림 받기
  getAgvStream: () => {
    return streamClient.get('/montior/agv-stream', {
      responseType: 'stream'
    });
  },

  // AGV 정지 명령
  stopAgv: async (agvIds) => {
    return await apiClient.post('/monitor/agv/stop', { agvIds });
  },

  // AGV 복귀 명령
  returnAgv: async (agvIds) => {
    return await apiClient.post('/monitor/agv/return', { agvIds });
  },

  // AGV 재가동 명령
  restartAgv: async (agvIds) => {
    return await apiClient.post('/monitor/agv/restart', { agvIds });
  },
};