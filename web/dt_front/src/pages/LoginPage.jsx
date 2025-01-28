import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "../api/authApi";
import { useAuth } from "../hooks/useAuth"; // useAuth 추가
import LoginForm from "../components/LoginForm";

const LoginPage = () => {
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { checkAuth } = useAuth(); // useAuth에서 checkAuth 가져오기

  const handleLogin = async ({ email, password }) => {
    try {
      const response = await authApi.login(email, password);
      if (response.success) {
        await checkAuth(); // 로그인 성공 후 유저 상태 업데이트
        navigate("/dashboard");
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
