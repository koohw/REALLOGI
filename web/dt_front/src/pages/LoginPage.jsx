// src/pages/LoginPage.jsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useDispatch } from "react-redux";
import { login } from "../features/userSlice"; // 로그인 액션 import
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
        dispatch(login(response.data));
        navigate("/dashboard");
      } else {
        setError(response.message);
      }
    } catch (err) {
      setError("Login failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen bg-[#0D1B2A] flex flex-col justify-center items-center">
      <div className="bg-[#11263f] p-8 rounded-lg shadow-lg w-full max-w-md border border-gray-700">
        <h1 className="text-4xl font-bold text-center mb-8 text-gray-200">
          Login
        </h1>
        <LoginForm onSubmit={handleLogin} error={error} />
      </div>
    </div>
  );
};

export default LoginPage;
