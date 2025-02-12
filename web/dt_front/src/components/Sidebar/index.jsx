import { useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth"; // useAuth 훅을 가져옵니다.
import MenuItem from "./MenuItem";

export default function Sidebar() {
  const { logout } = useAuth(); // useAuth 훅에서 logout 함수 가져오기
  const navigate = useNavigate();

  const menuItems = [
    { title: "대시보드", subtitle: "현황 확인판", path: "/dashboard" },
    { title: "모니터", subtitle: "실시간 모니터링", path: "/monitor" },
    { title: "시뮬레이션", subtitle: "효율 예상/예측", path: "/simulation" },
    { title: "AGV 등록", path: "/agv-register" },
    { title: "관리자 정보 수정", path: "/modify-info" },
  ];

  const handleLogout = async () => {
    await logout(); // 로그아웃 처리
    navigate("/login"); // 로그인 페이지로 리디렉션
  };

  return (
    <div className="w-64 min-h-screen bg-white shadow-lg">
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-8">RealLogi</h1>
        <nav className="space-y-4">
          {menuItems.map((item, index) => (
            <MenuItem key={index} {...item} />
          ))}
        </nav>

        {/* 로그아웃 버튼 추가 */}
        <div className="mt-8">
          <button
            onClick={handleLogout}
            className="w-full p-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </div>
    </div>
  );
}
