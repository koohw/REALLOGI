import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import MenuItem from "./MenuItem";

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // 대시보드 아이콘: 제공해주신 SVG 적용 (React JSX 형식으로 변환)
  const dashboardIcon = (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 128 128"
      className="h-6 w-6"
      fill="currentColor"
    >
      <path d="M127.12,60.22,115.46,48.56h0L69,2.05a7,7,0,0,0-9.9,0L12.57,48.53h0L.88,60.22a3,3,0,0,0,4.24,4.24l6.57-6.57V121a7,7,0,0,0,7,7H46a7,7,0,0,0,7-7V81a1,1,0,0,1,1-1H74a1,1,0,0,1,1,1v40a7,7,0,0,0,7,7h27.34a7,7,0,0,0,7-7V57.92l6.54,6.54a3,3,0,0,0,4.24-4.24ZM110.34,121a1,1,0,0,1-1,1H82a1,1,0,0,1-1-1V81a7,7,0,0,0-7-7H54a7,7,0,0,0-7,7v40a1,1,0,0,1-1,1H18.69a1,1,0,0,1-1-1V51.9L63.29,6.29a1,1,0,0,1,1.41,0l45.63,45.63Z" />
    </svg>
  );

  const menuItems = [
    {
      title: "대시보드",
      subtitle: "현황 확인판",
      path: "/dashboard",
      icon: dashboardIcon,
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
        <h1 className="text-3xl font-bold text-center text-white">RealLogi</h1>
        <p className="text-[#a0a0a0] text-center mb-6">Remote AGV RMS System</p>
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
