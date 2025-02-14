import AgvRegister from "../components/AgvRegister";
import Sidebar from "../components/Sidebar";

function AgvRegisterPage() {
  return (
    <div className="flex min-h-screen bg-[#0D1B2A]">
      {/* 좌측 사이드바 영역 */}
      <div className="w-64 border-r border-gray-700">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <AgvRegister />
      </div>
    </div>
  );
}

export default AgvRegisterPage;
