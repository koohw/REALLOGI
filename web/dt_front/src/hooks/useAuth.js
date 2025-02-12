import { useState, useEffect } from "react";
import { useDispatch } from "react-redux";
import { authApi } from "../api/authApi";
import { logout as logoutAction } from "../features/userSlice"; // 이름 변경

export const useAuth = () => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const dispatch = useDispatch();

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
        dispatch(logoutAction()); // 액션명 변경
      }
    } catch (error) {
      setUser(null);
      dispatch(logoutAction()); // 액션명 변경
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      const response = await authApi.logout();
      if (response.success) {
        setUser(null);
      }
    } catch (error) {
      console.error("Logout failed:", error);
    }
  };

  return { user, loading, logout, checkAuth };
};
