import Sidebar from "../components/Sidebar";
import AGVMap from "../components/AGVMap";

function MonitorPage() {
  return (
    <div className="flex min-h-screen bg-white">
      {/* 좌측 사이드바 영역 */}
      <div className="w-80 border-r border-gray-200">
        <Sidebar />
      </div>

      {/* 우측 메인 컨텐츠 영역 */}
      <div className="flex-1">
        <div>실시간 모니터링</div>
        <AGVMap />
      </div>
    </div>
  );
}

export default MonitorPage;
