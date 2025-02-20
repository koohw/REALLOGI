# webcam_webrtc.py
import asyncio
import cv2
import json
import logging
import numpy as np
import websockets
from av import VideoFrame
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, VideoStreamTrack
from aiortc.contrib.media import MediaBlackhole, MediaPlayer, MediaRecorder

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SIGNALING_SERVER = 'ws://127.0.0.1:6033/ws'


class VideoCamera(VideoStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        if not self.cap.isOpened():
            raise RuntimeError("카메라를 열 수 없습니다")

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        ret, frame = self.cap.read()
        if not ret:
            logger.error("카메라에서 프레임을 읽을 수 없습니다")
            return None

        # OpenCV BGR을 RGB로 변환
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = VideoFrame.from_ndarray(frame, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base

        return frame

    def stop(self):
        super().stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()


async def run_webrtc():
    # RTCPeerConnection 생성
    pc = RTCPeerConnection()

    # 비디오 트랙 추가
    video_sender = None
    websocket = None

    try:
        video_sender = VideoCamera()
        video_track = pc.addTrack(video_sender)
        logger.info("비디오 트랙이 추가되었습니다")

        # WebSocket 연결
        logger.info(f"시그널링 서버 연결 중... ({SIGNALING_SERVER})")
        websocket = await websockets.connect(
            SIGNALING_SERVER,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=20
        )
        logger.info("시그널링 서버에 연결되었습니다")

        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate and websocket.open:
                logger.debug(f"ICE candidate 전송: {candidate.candidate}")
                await websocket.send(json.dumps({
                    "type": "candidate",
                    "candidate": candidate.candidate,
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex
                }))

        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"연결 상태 변경: {pc.connectionState}")

        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            logger.info(f"ICE 연결 상태: {pc.iceConnectionState}")

        # 초기 offer 생성 및 전송
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        logger.info("로컬 description이 설정되었습니다")

        await websocket.send(json.dumps({
            "type": "offer",
            "sdp": pc.localDescription.sdp
        }))
        logger.info("Offer를 전송했습니다")

        while True:
            try:
                message = await websocket.recv()
                data = json.loads(message)
                logger.info(f"메시지 수신: {data['type']}")

                if data["type"] == "answer":
                    logger.info("Answer 처리 중...")
                    answer = RTCSessionDescription(
                        sdp=data["sdp"],
                        type=data["type"]
                    )
                    await pc.setRemoteDescription(answer)
                    logger.info("Remote description이 설정되었습니다")

                elif data["type"] == "candidate":
                    try:
                        candidate_data = data.get("candidate", {})
                        if isinstance(candidate_data, str):
                            # 문자열 형태의 candidate 처리
                            candidate = RTCIceCandidate(
                                candidate=candidate_data,
                                sdpMid=data.get("sdpMid"),
                                sdpMLineIndex=data.get("sdpMLineIndex")
                            )
                        else:
                            # 객체 형태의 candidate 처리
                            candidate = RTCIceCandidate(
                                candidate=candidate_data.get("candidate"),
                                sdpMid=candidate_data.get("sdpMid", "0"),
                                sdpMLineIndex=candidate_data.get("sdpMLineIndex", 0)
                            )
                        await pc.addIceCandidate(candidate)
                        logger.info("ICE candidate가 추가되었습니다")
                    except Exception as e:
                        logger.error(f"ICE candidate 처리 오류: {str(e)}")

            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket 연결이 종료되었습니다")
                break
            except Exception as e:
                logger.error(f"메시지 처리 중 오류 발생: {str(e)}")
                continue

    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
    finally:
        logger.info("정리 작업 중...")
        if video_sender:
            video_sender.stop()
        if pc:
            await pc.close()
        if websocket and not websocket.closed:
            await websocket.close()
        logger.info("정리 작업 완료")


if __name__ == "__main__":
    try:
        asyncio.run(run_webrtc())
    except KeyboardInterrupt:
        logger.info("키보드 인터럽트가 감지되었습니다. 종료합니다...")
    except Exception as e:
        logger.error(f"치명적 오류: {str(e)}")