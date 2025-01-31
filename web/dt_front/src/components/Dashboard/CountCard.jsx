export default function CountCard({ data }) {
    return (
      <div className="grid grid-cols-2 gap-4">
        <div className="text-center">
          <div className="text-3xl font-bold">{data.orderCount.total}</div>
          <div className="text-xl">{data.orderCount.completed}</div>
          <div className="text-gray-600">주문수</div>
        </div>
        <div className="text-center">
          <div className="text-3xl font-bold">{data.productCount.total}</div>
          <div className="text-xl">{data.productCount.completed}</div>
          <div className="text-gray-600">상품수</div>
        </div>
      </div>
    );
  }
  