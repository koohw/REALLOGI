import React from "react";
import { X } from "lucide-react";

const EmergencyPopup = ({ agv, onClose }) => {
  if (!agv) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center">
            <div className="h-8 w-8 rounded-full bg-red-600 flex items-center justify-center">
              <span className="text-white font-bold">!</span>
            </div>
            <h2 className="text-xl font-bold ml-3">Emergency Stop Alert</h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Main Alert */}
        <div className="bg-red-100 border-l-4 border-red-600 p-4 mb-4 rounded">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg
                className="h-5 w-5 text-red-600"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                AGV {agv.agv_name} Emergency Stopped
              </h3>
              <p className="mt-1 text-sm text-red-700">
                Location: ({agv.location_x}, {agv.location_y})
              </p>
            </div>
          </div>
        </div>

        {/* Status Details */}
        <div className="space-y-4">
          <div className="bg-red-50 p-4 rounded-md">
            <h3 className="font-semibold text-red-800 mb-2">Status Details</h3>
            <ul className="space-y-2 text-sm text-red-700">
              <li className="flex items-center">
                <span className="mr-2">•</span>
                <span>Current State: {agv.state}</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">•</span>
                <span>Last Direction: {agv.direction || "N/A"}</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">•</span>
                <span>Issue: {agv.issue || "Unknown Error"}</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">•</span>
                <span>Time: {new Date().toLocaleTimeString()}</span>
              </li>
            </ul>
          </div>

          {/* Required Actions */}
          <div className="bg-yellow-50 p-4 rounded-md">
            <h3 className="font-semibold text-yellow-800 mb-2">
              Required Actions
            </h3>
            <ul className="space-y-2 text-sm text-yellow-700">
              <li className="flex items-center">
                <span className="mr-2">1.</span>
                <span>Check for physical obstacles</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">2.</span>
                <span>Verify safety sensors</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">3.</span>
                <span>Inspect battery status</span>
              </li>
              <li className="flex items-center">
                <span className="mr-2">4.</span>
                <span>Contact maintenance if needed</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="mt-6 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors rounded-md border border-gray-300 hover:bg-gray-50"
          >
            Close
          </button>
          <button
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
            onClick={() => {
              // Add emergency response logic here
              onClose();
            }}
          >
            Acknowledge
          </button>
        </div>
      </div>
    </div>
  );
};

export default EmergencyPopup;
