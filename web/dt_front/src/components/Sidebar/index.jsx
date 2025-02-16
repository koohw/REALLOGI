import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import MenuItem from "./MenuItem";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const menuItems = [
    {
      title: "대시보드",
      subtitle: "현황 확인판",
      path: "/dashboard",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M3 10l9-7 9 7v10a2 2 0 01-2 2h-4a2 2 0 01-2-2V12H9v8a2 2 0 01-2 2H3a2 2 0 01-2-2V10z"
          />
        </svg>
      ),
    },
    {
      title: "모니터",
      subtitle: "실시간 모니터링",
      path: "/monitor",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9.75 17h4.5m-7.5 0h12a2.25 2.25 0 002.25-2.25V5.25A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25v9.5A2.25 2.25 0 005.25 17z"
          />
        </svg>
      ),
    },
    {
      title: "시뮬레이션",
      subtitle: "효율 예상/예측",
      path: "/simulation",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 19V6m4 13V10m4 9V4"
          />
        </svg>
      ),
    },
    {
      title: "AGV 등록",
      path: "/agv-register",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 4v16m8-8H4"
          />
        </svg>
      ),
    },
    {
      title: "관리자 정보 수정",
      path: "/modify-info",
      icon: (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-6 w-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l.814 2.497a1 1 0 00.95.69h2.634a1 1 0 01.592 1.806l-2.134 1.55a1 1 0 00-.364 1.118l.814 2.497a1 1 0 01-1.538 1.118l-2.134-1.55a1 1 0 00-1.176 0l-2.134 1.55a1 1 0 01-1.538-1.118l.814-2.497a1 1 0 00-.364-1.118L3.77 7.92a1 1 0 01.592-1.806h2.634a1 1 0 00.95-.69l.814-2.497z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      ),
    },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="flex flex-col w-64 h-full bg-[#0A1829] shadow-lg">
      <div className="p-6">
        <h1 className="text-3xl font-bold mb-6 text-center text-white">
          RealLogi
        </h1>
        {user && (
          <div className="flex items-center mb-6">
            <div className="w-10 h-10 rounded-full bg-gray-500 flex items-center justify-center mr-3">
              <span className="text-white font-bold">
                {user.userName ? user.userName.charAt(0) : "U"}
              </span>
            </div>
            <div className="text-white">
              <p className="font-medium">{user.userName || "User"}</p>
            </div>
          </div>
        )}
        <nav className="space-y-4">
          {menuItems.map((item, index) => (
            <MenuItem key={index} {...item} />
          ))}
        </nav>
      </div>
      <div className="mt-auto p-6">
        <button
          onClick={handleLogout}
          className="flex items-center justify-center w-full p-3 rounded-lg hover:bg-gray-700 transition-colors"
          title="로그아웃"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6 text-white"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h6a2 2 0 012 2v1"
            />
          </svg>
          <span className="ml-2 text-white font-medium">로그아웃</span>
        </button>
      </div>
    </div>
  );
}
