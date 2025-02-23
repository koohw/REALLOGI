import { useState, useEffect } from "react";
import StatusCard from "./StatusCard";
import CountCard from "./CountCard";
import AgvGraph from "./AgvGraph";
import AgvTable from "./AgvTable";

export default function Dashboard() {
  const [statusData, setStatusData] = useState({
    operating: 0,
    waiting: 0,
    charging: 0,
    error: 0,
  });

  const [orderData, setOrderData] = useState({
    productCount: {
      total: 0,
    },
  });

  const handleDataUpdate = (newData) => {
    setStatusData(newData);
  };

  const handleOrderUpdate = (newData) => {
    setOrderData(newData);
  };

  return (
    <div className="space-y-6 bg-[#11263f] p-6 min-h-screen">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-[#0D1B2A] rounded-lg shadow-lg p-6 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 text-white">
            로봇 운용 현황
          </h2>
          <StatusCard data={statusData} />
        </div>

        <div className="bg-[#0D1B2A] rounded-lg shadow-lg p-6 border border-white/10">
          <h2 className="text-lg font-semibold mb-4 text-white">
            물류 운용 현황
          </h2>
          <CountCard data={orderData} />
        </div>
      </div>

      <div className="bg-[#0D1B2A] rounded-lg shadow-lg border border-white/10">
        <AgvGraph
          onDataUpdate={handleDataUpdate}
          onOrderUpdate={handleOrderUpdate}
        />
      </div>

      <div className="bg-[#0D1B2A] rounded-lg shadow-lg border border-white/10">
        <AgvTable />
      </div>
    </div>
  );
}
