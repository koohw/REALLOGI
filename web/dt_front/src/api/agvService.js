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

// const streamClient = axios.create({
//   baseURL: API_BASE_URL,  // BASE_URL을 API_BASE_URL로 수정
//   withCredentials: true,
//   headers: {
//     'Content-Type': 'text/event-stream'  // "stream"을 올바른 MIME 타입으로 수정
//   }
// });

export const agvService = {
  // AGV 상태 스트림 받기
  // getAgvStream: () => {
  //   console.log('getAgvStream');
  //   return streamClient.get('/moni/agv-stream', {
  //     responseType: 'stream'
  //   });
  // },
  getAgvStream: () => {
    // URL이 올바르게 구성되었는지 확인을 위한 로깅
    const streamUrl = `${API_BASE_URL}/moni/agv-stream`.replace(/\/+/g, '/');
    console.log('Stream URL:', streamUrl);
    
    return new EventSource(streamUrl, {
        withCredentials: true
    });
},

  // AGV 정지 명령
  stopAgv: async (agvIds) => {
    return await apiClient.post('/moni/agv/stop', { agvIds });
  },

  // AGV 복귀 명령
  returnAgv: async (agvIds) => {
    return await apiClient.post('/moni/agv/return', { agvIds });
  },

  // AGV 재가동 명령
  restartAgv: async (agvIds) => {
    return await apiClient.post('/moni/agv/restart', { agvIds });
  },
};