import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL;

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // You can add custom logic here (e.g., adding auth tokens)
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    const customError = {
      message: error.response?.data?.message || "An error occurred",
      status: error.response?.status,
      data: error.response?.data,
    };
    return Promise.reject(customError);
  }
);

export const authApi = {
  login: async (email, password) => {
    try {
      return await apiClient.post("/api/users/login", { email, password });
    } catch (error) {
      throw new Error(error.message || "Login failed");
    }
  },

  logout: async () => {
    try {
      return await apiClient.post("/api/users/logout");
    } catch (error) {
      throw new Error(error.message || "Logout failed");
    }
  },

  getCurrentUser: async () => {
    try {
      return await apiClient.get("/api/users/current");
    } catch (error) {
      throw new Error(error.message || "Failed to get current user");
    }
  },

  checkEmail: async (email) => {
    try {
      return await apiClient.get("/api/users/check-email", {
        params: { email },
      });
    } catch (error) {
      throw new Error(error.message || "Email check failed");
    }
  },

  signup: async (userData) => {
    try {
      return await apiClient.post("/api/users/signup", userData);
    } catch (error) {
      throw new Error(error.message || "Signup failed");
    }
  },

  updateUserInfo: async (updateData) => {
    try {
      return await apiClient.put("/api/users/update", updateData);
    } catch (error) {
      throw new Error(error.message || "Update failed");
    }
  },

  getCompanies: async () => {
    try {
      return await apiClient.get("/api/companies");
    } catch (error) {
      throw new Error(error.message || "Failed to fetch companies");
    }
  },

  getWarehouses: async (companyId) => {
    try {
      return await apiClient.get(`/api/users/warehouses/${companyId}`);
    } catch (error) {
      throw new Error(error.message || "Failed to fetch warehouses");
    }
  },
};

// Usage example:
// import { authApi } from './services/api';
// const response = await authApi.login(email, password);
