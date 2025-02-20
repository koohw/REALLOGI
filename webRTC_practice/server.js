// server.js
const WebSocket = require("ws");
const http = require("http");

// HTTP 서버 생성
const server = http.createServer((req, res) => {
  if (req.url === "/") {
    res.writeHead(200, { "Content-Type": "text/html" });
    res.end(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>WebRTC Viewer</title>
            </head>
            <body>
                <h2>WebRTC 스트림 뷰어</h2>
                <video id="video" autoplay playsinline style="width: 640px; height: 480px;"></video>
                <script>
                    const pc = new RTCPeerConnection({
                        iceServers: [
                            { urls: 'stun:stun.l.google.com:19302' }
                        ]
                    });
                    const video = document.getElementById('video');
                    
                    pc.ontrack = (event) => {
                        if (event.streams && event.streams[0]) {
                            video.srcObject = event.streams[0];
                        }
                    };

                    const ws = new WebSocket('ws://localhost:6033/ws');
                    
                    ws.onmessage = async (event) => {
                        const data = JSON.parse(event.data);
                        console.log('받은 메시지:', data.type);
                        
                        if (data.type === 'offer') {
                            await pc.setRemoteDescription(new RTCSessionDescription(data));
                            const answer = await pc.createAnswer();
                            await pc.setLocalDescription(answer);
                            
                            ws.send(JSON.stringify({
                                type: 'answer',
                                sdp: answer.sdp
                            }));
                        } else if (data.type === 'candidate' && data.candidate) {
                            try {
                                await pc.addIceCandidate(data.candidate);
                            } catch (e) {
                                console.error('ICE candidate 추가 실패:', e);
                            }
                        }
                    };

                    pc.onicecandidate = (event) => {
                        if (event.candidate) {
                            ws.send(JSON.stringify({
                                type: 'candidate',
                                candidate: event.candidate
                            }));
                        }
                    };
                </script>
            </body>
            </html>
        `);
    return;
  }
  res.writeHead(404);
  res.end();
});

// WebSocket 서버 설정
const wss = new WebSocket.Server({
  server: server,
  path: "/ws",
});

// 연결된 클라이언트 관리
const clients = new Set();

wss.on("connection", (ws, req) => {
  const ip = req.socket.remoteAddress;
  console.log(`새로운 클라이언트 연결됨: ${ip}`);
  clients.add(ws);

  // 연결 성공 메시지 전송
  ws.send(
    JSON.stringify({
      type: "connection_success",
      message: "시그널링 서버에 연결되었습니다",
    })
  );

  ws.on("message", (message) => {
    try {
      const data = JSON.parse(message);
      console.log(`메시지 수신됨 (${data.type}) - 발신자: ${ip}`);

      // 다른 클라이언트들에게 메시지 전달
      clients.forEach((client) => {
        if (client !== ws && client.readyState === WebSocket.OPEN) {
          client.send(message.toString());
        }
      });
    } catch (error) {
      console.error("메시지 처리 오류:", error);
    }
  });

  ws.on("close", () => {
    console.log(`클라이언트 연결 종료: ${ip}`);
    clients.delete(ws);
  });

  ws.on("error", (error) => {
    console.error(`WebSocket 오류 (${ip}):`, error);
    clients.delete(ws);
  });
});

const PORT = 6033;
const HOST = "0.0.0.0";

console.log(`서버 시작 중... (${HOST}:${PORT})`);
server.listen(PORT, HOST, () => {
  console.log(`시그널링 서버가 실행 중입니다: http://${HOST}:${PORT}`);
});
