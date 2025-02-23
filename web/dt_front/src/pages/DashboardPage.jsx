import Dashboard from "../components/Dashboard";
import Sidebar from "../components/Sidebar";

function DashboardPage() {
  return (
    <div className="flex min-h-screen bg-[#11263f]">
      {/* 좌측 사이드바 영역 */}
      <div className="flex-none">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <div className="h-16 bg-[#11263f] border-b border-white/10 px-6 flex items-center">
          <h1 className="text-xl font-semibold text-white">대시보드</h1>
        </div>
        <div className="p-6">
          <Dashboard />
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
