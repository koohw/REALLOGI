import { useLocation } from 'react-router-dom';
import MenuItem from './MenuItem';

export default function Sidebar() {
  const menuItems = [
    {
      title: "대시보드",
      subtitle: "현황 확인판",
      path: "/"
    },
    {
      title: "모니터",
      subtitle: "실시간 모니터링",
      path: "/monitor"
    },
    {
      title: "시뮬레이션",
      subtitle: "효율 예상/예측",
      path: "/simulation"
    },
    {
      title: "AGV 등록",
      path: "/agv"
    },
    {
      title: "관리자 정보 수정",
      path: "/admin"
    }
  ];

  return (
    <div className="w-64 min-h-screen bg-white shadow-lg">
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-8">물류 관리 시스템</h1>
        <nav className="space-y-4">
          {menuItems.map((item, index) => (
            <MenuItem key={index} {...item} />
          ))}
        </nav>
      </div>
    </div>
  );
}
