import { useState } from "react";
import { Link } from "react-router-dom";

const LoginForm = ({ onSubmit, error }) => {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const handleForgotPassword = (e) => {
    e.preventDefault();
    alert("비밀번호를 찾아주세요 기능은 준비중입니다.");
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="space-y-2">
        <label htmlFor="email" className="block text-gray-300 text-lg">
          Email
        </label>
        <input
          id="email"
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          className="w-full p-3 border border-gray-600 rounded-md bg-[#0D1B2A] text-gray-200 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="Enter your email"
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="block text-gray-300 text-lg">
          Password
        </label>
        <input
          id="password"
          type="password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          className="w-full p-3 border border-gray-600 rounded-md bg-[#0D1B2A] text-gray-200 
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                   placeholder-gray-500"
          placeholder="Enter your password"
          required
        />
      </div>

      {error && (
        <div className="text-red-400 text-sm bg-red-900 bg-opacity-50 p-2 rounded">
          {error}
        </div>
      )}

      <button
        type="submit"
        className="w-full bg-blue-900 text-gray-200 p-3 rounded-md hover:bg-blue-800 
                 transition-colors border border-gray-600"
      >
        Sign In
      </button>

      <div className="flex justify-between pt-4">
        <button
          onClick={handleForgotPassword}
          className="text-gray-400 hover:text-gray-200 underline"
        >
          Forgot password?
        </button>
        <Link
          to="/signup"
          className="text-gray-400 hover:text-gray-200 underline"
        >
          Join
        </Link>
      </div>
    </form>
  );
};

export default LoginForm;
