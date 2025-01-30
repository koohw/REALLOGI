export default function SuccessModal({ show, onClose }) {
    if (!show) return null;
  
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h3 className="text-lg font-semibold mb-4">등록 완료</h3>
          <p>AGV가 성공적으로 등록되었습니다.</p>
          <button
            onClick={onClose}
            className="mt-4 w-full bg-black text-white py-2 rounded-lg hover:bg-gray-800"
          >
            확인
          </button>
        </div>
      </div>
    );
  }