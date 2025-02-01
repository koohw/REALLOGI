import Dashboard from "../components/Dashboard";
<<<<<<< HEAD
=======
import Sidebar from "../components/Sidebar";
>>>>>>> e71f8ea46ce89185e7502f21fb024b5c6826c008

function DashboardPage() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* 좌측 사이드바 영역 */}
      <div className="w-80 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <Dashboard />
      </div>
    </div>
  );
}

export default DashboardPage;
