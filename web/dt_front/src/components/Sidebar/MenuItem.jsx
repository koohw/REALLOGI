import { useNavigate, useLocation } from 'react-router-dom';

export default function MenuItem({ title, subtitle, path }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isActive = location.pathname === path;

  return (
    <div 
      onClick={() => navigate(path)}
      className={`p-4 rounded-lg cursor-pointer transition-all ${
        isActive ? 'bg-gray-100' : 'hover:bg-gray-50'
      }`}
    >
      <h2 className="font-medium text-base">{title}</h2>
      {subtitle && (
        <p className="text-sm text-gray-500">{subtitle}</p>
      )}
    </div>
  );
}