export default function StatusCard({ data }) {
  const items = [
    { label: "운영", value: data.operating, color: "text-blue-500" },
    { label: "대기", value: data.waiting, color: "text-gray-500" },
    { label: "적재", value: data.charging, color: "text-green-500" },
    { label: "에러", value: data.error, color: "text-red-500" },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {items.map((item, index) => (
        <div key={index} className="text-center">
          <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
          <div className="text-gray-600">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
