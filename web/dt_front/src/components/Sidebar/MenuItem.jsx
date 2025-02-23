import { useNavigate, useLocation } from "react-router-dom";

export default function MenuItem({ title, subtitle, path, icon }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = location.pathname === path;

  return (
    <div
      onClick={() => navigate(path)}
      className={`flex items-center p-4 rounded-lg cursor-pointer transition-all ${
        isActive
          ? "bg-[#1a3b66] text-white"
          : "text-gray-300 hover:bg-[#163152] hover:text-white"
      }`}
    >
      {icon && <div className="mr-3">{icon}</div>}
      <div>
        <h2 className="font-medium text-base">{title}</h2>
        {subtitle && (
          <p className={`text-sm ${isActive ? "text-gray-300" : "text-gray-400"}`}>
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
}
