export default function SimulationResult() {
    const results = [
      { label: '이동 효율성', before: '73%', after: '88%' },
      { label: '정지 횟수', before: '3.12회', after: '1.83회' },
      { label: '병목구간', before: '2곳(C2, A3)', after: '1곳(B1)' },
      { label: '경제적 효율성', before: '184,000,000원', after: '201,000,000원' },
    ];
  
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold mb-4">분석 결과</h2>
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="py-2 text-left">분석 결과</th>
              <th className="py-2 text-left">변경 전</th>
              <th className="py-2 text-left">변경 후</th>
            </tr>
          </thead>
          <tbody>
            {results.map((item, index) => (
              <tr key={index} className="border-b">
                <td className="py-2">{item.label}</td>
                <td className="py-2">{item.before}</td>
                <td className="py-2">{item.after}</td>
              </tr>
            ))}
            <tr>
              <td colSpan={3} className="py-2 text-sm">
                최종 결과: 변경 후의 경우 연간 17,000,000원의 추가 이익 예상
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    );
  }