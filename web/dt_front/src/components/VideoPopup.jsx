import React, { useState, useEffect, useRef } from "react";
import { X, Minimize2, Maximize2 } from "lucide-react";

const VideoPopup = ({ onClose }) => {
  const [streamStatus, setStreamStatus] = useState("연결 대기 중...");
  const [streamError, setStreamError] = useState(null);
  const [isMinimized, setIsMinimized] = useState(false);
  const videoRef = useRef(null);
  const peerConnection = useRef(null);
  const wsRef = useRef(null);
  const BASE_URL = process.env.REACT_APP_API_URL;

  useEffect(() => {
    const startWebRTC = async () => {
      try {
        peerConnection.current = new RTCPeerConnection({
          iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "stun:stun1.l.google.com:19302" },
          ],
          iceCandidatePoolSize: 10,
        });

        peerConnection.current.ontrack = (event) => {
          if (videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
          }
        };

        wsRef.current = new WebSocket(BASE_URL + "/ws");

        wsRef.current.onopen = () => {
          setStreamStatus("서버에 연결됨");
          setStreamError(null);
        };

        wsRef.current.onclose = () => {
          setStreamStatus("연결 끊김");
          setStreamError("연결 종료");
        };

        wsRef.current.onerror = () => {
          setStreamError("연결 오류");
        };

        wsRef.current.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data);

            if (message.type === "offer") {
              await peerConnection.current.setRemoteDescription(
                new RTCSessionDescription(message)
              );

              const answer = await peerConnection.current.createAnswer();
              await peerConnection.current.setLocalDescription(answer);

              wsRef.current.send(
                JSON.stringify({
                  type: "answer",
                  sdp: answer.sdp,
                })
              );

              setStreamStatus("연결 중...");
            } else if (message.type === "candidate" && message.candidate) {
              try {
                await peerConnection.current.addIceCandidate(
                  new RTCIceCandidate(message.candidate)
                );
              } catch (e) {
                console.error("ICE candidate 추가 실패:", e);
              }
            }
          } catch (e) {
            setStreamError("처리 오류");
          }
        };

        peerConnection.current.onicecandidate = (event) => {
          if (event.candidate) {
            wsRef.current?.send(
              JSON.stringify({
                type: "candidate",
                candidate: event.candidate,
              })
            );
          }
        };

        peerConnection.current.oniceconnectionstatechange = () => {
          const state = peerConnection.current.iceConnectionState;
          if (state === "connected") {
            setStreamStatus("스트리밍 중");
          } else if (state === "disconnected") {
            setStreamStatus("연결 끊김");
          }
        };
      } catch (err) {
        setStreamError("초기화 실패");
      }
    };

    startWebRTC();

    return () => {
      if (peerConnection.current) {
        peerConnection.current.close();
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const toggleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  return (
    <div
      className={`fixed z-50 shadow-lg rounded-lg bg-gray-900 transition-all duration-300 ${
        isMinimized
          ? "right-4 bottom-4 w-64 h-36"
          : "right-4 bottom-4 w-96 h-64"
      }`}
    >
      {/* Header */}
      <div className="absolute top-0 left-0 right-0 bg-gray-800 bg-opacity-75 p-2 flex justify-between items-center z-10">
        <span
          className={`text-white text-xs ${streamError ? "text-red-400" : ""}`}
        >
          {streamError || streamStatus}
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleMinimize}
            className="text-white hover:text-gray-300 transition-colors"
          >
            {isMinimized ? <Maximize2 size={14} /> : <Minimize2 size={14} />}
          </button>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-300 transition-colors"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Video */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        className="w-full h-full object-cover rounded-lg"
      />

      {/* Loading Overlay */}
      {!videoRef.current?.srcObject && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 text-white text-sm">
          비디오 스트림 대기 중...
        </div>
      )}
    </div>
  );
};

export default VideoPopup;
