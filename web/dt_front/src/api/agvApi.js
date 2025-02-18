import axios from 'axios';

const BASE_URL = process.env.REACT_APP_API_URL;

const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

export const agvApi = {
  registerAgv: async (agvData) => {
    try {
      console.log('url:', BASE_URL);
      return await apiClient.post('/api/agvs/register', agvData);
    } catch (error) {
      throw new Error(error.message || 'AGV 등록 실패');
    }
  }
};
