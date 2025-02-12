export default function CountCard({ data }) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="text-center">
        <div className="text-3xl font-bold">3000</div>
        <div className="text-gray-600">주문수</div>
      </div>
      <div className="text-center">
        <div className="text-3xl font-bold">
          {3000 - data.productCount.total}
        </div>
        <div className="text-gray-600">남은 상품수</div>
      </div>
    </div>
  );
}
