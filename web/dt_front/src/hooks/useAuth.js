import { useState, useEffect } from "react";
import { authApi } from "../api/authApi";

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const response = await authApi.getCurrentUser();
      if (response.success && response.data) {
        setUser(response.data);
      } else {
        setUser(null);
      }
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const response = await authApi.logout();
      if (response.success) {
        setUser(null); // 로그아웃 시 user 상태 초기화
      }
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return { user, loading, logout, checkAuth };
};

