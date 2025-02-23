export default function StatusCard({ data }) {
  const items = [
    { label: "운영", value: data.operating, color: "text-white" },
    { label: "대기", value: data.waiting, color: "text-white" },
    { label: "적재", value: data.charging, color: "text-white" },
    { label: "에러", value: data.error, color: "text-red-400" },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {items.map((item, index) => (
        <div key={index} className="text-center p-3 rounded-lg bg-[#11263f]">
          <div className={`text-2xl font-bold ${item.color}`}>{item.value}</div>
          <div className="text-white/80">{item.label}</div>
        </div>
      ))}
    </div>
  );
}
