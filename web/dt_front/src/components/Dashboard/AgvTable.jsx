export default function AgvTable() {
  //임시 데이터
  const tableData = [
    {
      time: "15:34:24",
      name: "AGV9",
      location: "A3",
      efficiency: "73%",
      workStatus: "12초 정지",
      operationStatus: "충돌 회피대기",
    },
    {
      time: "15:35:53",
      name: "AGV2",
      location: "F23",
      efficiency: "85%",
      workStatus: "정상 가동",
      operationStatus: "-",
    },
    {
      time: "15:44:10",
      name: "AGV2",
      location: "F23",
      efficiency: "55%",
      workStatus: "123초 정지",
      operationStatus: "정체중",
    },
    {
      time: "15:56:33",
      name: "AGV2",
      location: "F23",
      efficiency: "49%",
      workStatus: "재가동",
      operationStatus: "-",
    },
  ];

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-lg font-semibold mb-4 text-[#11263f]">AGV 등록</h2>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="bg-[#11263f]">
              <th className="px-4 py-2 text-left text-white">시간</th>
              <th className="px-4 py-2 text-left text-white">AGV 이름</th>
              <th className="px-4 py-2 text-left text-white">위치</th>
              <th className="px-4 py-2 text-left text-white">이동 효율성</th>
              <th className="px-4 py-2 text-left text-white">작업상태</th>
              <th className="px-4 py-2 text-left text-white">구동상태</th>
            </tr>
          </thead>
          <tbody>
            {tableData.map((row, index) => (
              <tr
                key={index}
                className="border-b border-[#11263f]/10 hover:bg-[#11263f]/5 transition-colors"
              >
                <td className="px-4 py-2 text-[#11263f]">{row.time}</td>
                <td className="px-4 py-2 text-[#11263f]">{row.name}</td>
                <td className="px-4 py-2 text-[#11263f]">{row.location}</td>
                <td className="px-4 py-2 text-[#11263f]">{row.efficiency}</td>
                <td className="px-4 py-2 text-[#11263f]">{row.workStatus}</td>
                <td className="px-4 py-2 text-[#11263f]">
                  {row.operationStatus}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
