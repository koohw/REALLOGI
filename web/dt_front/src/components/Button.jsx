// components/Button.jsx
import React from "react";

const Button = ({
  children,
  onClick,
  disabled = false,
  variant = "primary",
  className = "",
}) => {
  const baseStyles =
    "px-4 py-2 rounded-md font-medium transition-colors duration-200 flex items-center justify-center";

  const variants = {
    primary: "bg-blue-500 text-white hover:bg-blue-600 disabled:bg-blue-300",
    secondary:
      "bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400",
    danger: "bg-red-500 text-white hover:bg-red-600 disabled:bg-red-300",
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
};

export default Button;
