export default function SuccessModal({ show, onClose }) {
  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center">
      <div className="bg-[#11263f] p-6 rounded-lg shadow-lg border border-gray-700">
        <h3 className="text-lg font-semibold mb-4 text-gray-200">등록 완료</h3>
        <p className="text-gray-300">AGV가 성공적으로 등록되었습니다.</p>
        <button
          onClick={onClose}
          className="mt-4 w-full bg-blue-900 text-gray-200 py-2 rounded-lg hover:bg-blue-800 
                   transition-colors border border-gray-600"
        >
          확인
        </button>
      </div>
    </div>
  );
}
