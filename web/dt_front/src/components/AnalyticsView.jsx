import React, { useMemo } from "react";
import { useSelector } from "react-redux";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const AnalyticsView = () => {
  const efficiencyData = useSelector((state) => state.agv.agvData);
  // orderTotal is used for the quantity chart (e.g., sum of order successes)
  const orderSuccessTotal = useSelector((state) => state.agv.orderTotal);
  // order_success contains each AGV's individual order success data
  const orderSuccessByAGV = useSelector((state) => state.agv.order_success);
  const totalCapacity = 3000;

  // Optimize efficiency data to only include points where values change
  const optimizedEfficiencyData = useMemo(() => {
    if (!efficiencyData || efficiencyData.length === 0) return [];

    return efficiencyData.reduce((acc, current, index) => {
      if (index === 0) {
        return [current];
      }
      const lastPoint = acc[acc.length - 1];
      if (Math.abs(lastPoint.efficiency - current.efficiency) > 0.01) {
        return [...acc, current];
      }
      if (
        index === efficiencyData.length - 1 &&
        lastPoint.time !== current.time
      ) {
        return [...acc, current];
      }
      return acc;
    }, []);
  }, [efficiencyData]);

  // Data for the quantity bar chart
  const quantityData = [
    {
      name: "잔여",
      remaining: totalCapacity - orderSuccessTotal,
    },
    {
      name: "완료",
      completed: orderSuccessTotal,
    },
  ];

  // Prepare data for the AGV order success chart
  const agvOrderSuccessData = useMemo(() => {
    if (!orderSuccessByAGV) return [];
    return Object.entries(orderSuccessByAGV).map(([agv, success]) => ({
      agv,
      success,
    }));
  }, [orderSuccessByAGV]);

  return (
    <div className="space-y-4 p-4 bg-gray-900 rounded-lg">
      {/* Efficiency Graph */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">실시간 AGV 효율성</h3>
        <div className="h-44">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={optimizedEfficiencyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="time"
                tick={{ fill: "#9CA3AF" }}
                angle={-45}
                textAnchor="end"
                height={60}
                interval={0}
              />
              <YAxis
                domain={[0, 30]}
                ticks={[0, 15, 30]}
                tick={{ fill: "#9CA3AF" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
                formatter={(value) => [`${value.toFixed(2)}sec`, "효율성"]}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="efficiency"
                name="효율성"
                stroke="#60A5FA"
                strokeWidth={2}
                dot={true}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quantity Bar Chart */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">물동량 현황</h3>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={quantityData}
              layout="vertical"
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis type="number" tick={{ fill: "#9CA3AF" }} />
              <YAxis
                dataKey="name"
                type="category"
                tick={{ fill: "#9CA3AF" }}
                width={60}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
              />
              <Legend />
              <Bar
                dataKey="remaining"
                name="잔여"
                fill="#EF4444"
                radius={[0, 4, 4, 0]}
                stackId="a"
              />
              <Bar
                dataKey="completed"
                name="완료"
                fill="#10B981"
                radius={[0, 4, 4, 0]}
                stackId="a"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AGV Order Success Bar Chart */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-white text-lg mb-4">AGV 별 주문 성공</h3>
        <div className="h-40">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={agvOrderSuccessData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="agv" tick={{ fill: "#9CA3AF" }} />
              <YAxis tick={{ fill: "#9CA3AF" }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1F2937",
                  border: "none",
                  borderRadius: "4px",
                  color: "#fff",
                }}
              />
              <Legend />
              <Bar dataKey="success" name="주문 성공" fill="#FBBF24" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsView;
