import { useState, useEffect, useRef } from "react";

const WebRTCStream = () => {
  const [status, setStatus] = useState("연결 대기 중...");
  const [error, setError] = useState(null);
  const videoRef = useRef(null);
  const peerConnection = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const startWebRTC = async () => {
      try {
        // WebRTC 연결 설정
        peerConnection.current = new RTCPeerConnection({
          iceServers: [
            { urls: "stun:stun.l.google.com:19302" },
            { urls: "stun:stun1.l.google.com:19302" },
          ],
          iceCandidatePoolSize: 10,
        });

        // 미디어 스트림 처리
        peerConnection.current.ontrack = (event) => {
          console.log("스트림 수신됨:", event.streams[0]);
          if (videoRef.current && event.streams[0]) {
            videoRef.current.srcObject = event.streams[0];
          }
        };

        // WebSocket 연결
        wsRef.current = new WebSocket("ws://127.0.0.1:6033/ws");

        wsRef.current.onopen = () => {
          console.log("WebSocket 연결됨");
          setStatus("서버에 연결됨");
          setError(null);
        };

        wsRef.current.onclose = () => {
          console.log("WebSocket 연결 끊김");
          setStatus("연결 끊김");
          setError("서버와의 연결이 종료되었습니다.");
        };

        wsRef.current.onerror = (error) => {
          console.error("WebSocket 에러:", error);
          setError("연결 중 오류가 발생했습니다.");
        };

        wsRef.current.onmessage = async (event) => {
          try {
            const message = JSON.parse(event.data);
            console.log("수신된 메시지:", message.type);

            if (message.type === "offer") {
              console.log("Offer 수신됨");
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

              setStatus("연결 설정 중...");
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
            console.error("메시지 처리 오류:", e);
            setError("메시지 처리 중 오류가 발생했습니다.");
          }
        };

        // ICE candidate 이벤트 처리
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

        // 연결 상태 모니터링
        peerConnection.current.oniceconnectionstatechange = () => {
          const state = peerConnection.current.iceConnectionState;
          console.log("ICE 상태:", state);
          setStatus(`ICE 상태: ${state}`);

          if (state === "connected") {
            setStatus("스트리밍 중");
          } else if (state === "disconnected") {
            setStatus("연결 끊김");
            setError("연결이 종료되었습니다.");
          }
        };
      } catch (err) {
        console.error("WebRTC 초기화 오류:", err);
        setError("WebRTC 초기화 실패: " + err.message);
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

  return (
    <div className="w-full max-w-2xl mx-auto p-4">
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <strong className="font-bold">오류: </strong>
          <span className="block sm:inline">{error}</span>
        </div>
      )}
      <div className="mb-4 text-center">
        <span
          className={`inline-block px-3 py-1 rounded ${
            status.includes("스트리밍")
              ? "bg-green-100 text-green-700"
              : status.includes("연결")
              ? "bg-blue-100 text-blue-700"
              : "bg-yellow-100 text-yellow-700"
          }`}
        >
          {status}
        </span>
      </div>
      <div className="relative aspect-video bg-gray-900 rounded-lg overflow-hidden">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          className="w-full h-full object-cover"
        />
        {!videoRef.current?.srcObject && (
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50 text-white">
            비디오 스트림 대기 중...
          </div>
        )}
      </div>
    </div>
  );
};

export default WebRTCStream;
