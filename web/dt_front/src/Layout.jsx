import { Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import { useAuth } from './hooks/useAuth';

export const ProtectedLayout = ({ children }) => {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div className="flex min-h-screen bg-white">
      <div className="w-80 border-r border-gray-200">
        <Sidebar />
      </div>
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
};