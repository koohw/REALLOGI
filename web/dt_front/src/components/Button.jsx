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
    primary:
      "bg-[#11263f] text-gray-200 hover:bg-[#0D1B2A] disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700",
    secondary:
      "bg-[#0D1B2A] text-gray-300 hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed border border-gray-700",
    danger:
      "bg-red-900 text-gray-200 hover:bg-red-800 disabled:opacity-50 disabled:cursor-not-allowed border border-red-700",
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
