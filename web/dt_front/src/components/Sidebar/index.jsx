import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import MenuItem from "./MenuItem";

export default function Sidebar() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const menuItems = [
    { title: "대시보드", subtitle: "현황 확인판", path: "/dashboard" },
    { title: "모니터", subtitle: "실시간 모니터링", path: "/monitor" },
    { title: "시뮬레이션", subtitle: "효율 예상/예측", path: "/simulation" },
    { title: "AGV 등록", path: "/agv-register" },
    { title: "관리자 정보 수정", path: "/modify-info" },
  ];

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="w-64 h-full bg-[#0A1829] shadow-lg">
      <div className="p-6">
        <h1 className="text-3xl font-bold mb-8 text-center text-white">
          RealLogi
        </h1>
        <nav className="space-y-4">
          {menuItems.map((item, index) => (
            <MenuItem key={index} {...item} />
          ))}
        </nav>

        <div className="mt-8 ml-4">
          <button
            onClick={handleLogout}
            className="w-1/2 p-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>
  );
}
