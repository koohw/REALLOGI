// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { login } from "../features/userSlice";  // 로그인 액션 import
import LoginForm from "../components/LoginForm";
import { authApi } from "../api/authApi";

const LoginPage = () => {
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const dispatch = useDispatch();

  const handleLogin = async ({ email, password }) => {
    try {
      const response = await authApi.login(email, password);
      if (response.success) {
        // 로그인 성공 후 리덕스 상태에 사용자 정보 저장
        dispatch(login(response.data));
        navigate("/dashboard");  // 대시보드로 리디렉션
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError("Login failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col justify-center items-center">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md">
        <h1 className="text-4xl font-bold text-center mb-8">Login</h1>
        <LoginForm onSubmit={handleLogin} error={error} />
      </div>
    </div>
  );
};

export default LoginPage;
