// src/components/ProtectedRoute.js
import { useSelector } from "react-redux";
import { Navigate } from "react-router-dom";

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useSelector((state) => state.user);

  if (!isAuthenticated) {
    // 로그인되지 않은 사용자는 로그인 페이지로 리디렉션
    return <Navigate to="/login" />;
  }

  return children;
};

export default ProtectedRoute;
