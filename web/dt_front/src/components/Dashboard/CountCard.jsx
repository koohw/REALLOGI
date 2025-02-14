export default function CountCard({ data }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="text-center p-4 bg-[#11263f] rounded-lg">
        <div className="text-3xl font-bold text-white">3000</div>
        <div className="text-white/80">주문수</div>
      </div>
      <div className="text-center p-4 bg-[#11263f] rounded-lg">
        <div className="text-3xl font-bold text-white">
          {3000 - data.productCount.total}
        </div>
        <div className="text-white/80">남은 상품수</div>
      </div>
    </div>
  );
}
