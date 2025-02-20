# jetson_webrtc.py
import asyncio
import json
import logging
import cv2
import numpy as np
import websockets
from av import VideoFrame
from aiortc import MediaStreamTrack, RTCPeerConnection, RTCSessionDescription, RTCIceCandidate, VideoStreamTrack
import gi

gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SIGNALING_SERVER = 'ws://127.0.0.1:5000/ws'


class JetsonVideoTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self):
        super().__init__()
        Gst.init(None)

        # CSI 카메라를 위한 GStreamer 파이프라인
        self.pipeline_str = (
            'nvarguscamerasrc sensor-id=0 ! '
            'video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1 ! '
            'nvvidconv ! '
            'video/x-raw, width=640, height=480, format=BGRx ! '
            'videoconvert ! '
            'video/x-raw, format=BGR ! '
            'appsink name=sink emit-signals=True max-buffers=1 drop=True'
        )

        self.pipeline = Gst.parse_launch(self.pipeline_str)
        self.appsink = self.pipeline.get_by_name('sink')

        # 파이프라인 시작
        self.pipeline.set_state(Gst.State.PLAYING)
        logger.info("GStreamer 파이프라인이 시작되었습니다")

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        # GStreamer에서 프레임 가져오기
        sample = self.appsink.try_pull_sample(Gst.SECOND)
        if sample:
            buf = sample.get_buffer()
            caps = sample.get_caps()

            # 메모리에서 프레임 데이터 추출
            success, map_info = buf.map(Gst.MapFlags.READ)
            if success:
                try:
                    # NumPy 배열로 변환
                    frame = np.ndarray(
                        shape=(480, 640, 3),
                        dtype=np.uint8,
                        buffer=map_info.data
                    )

                    # BGR에서 RGB로 변환
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                    # VideoFrame 생성
                    video_frame = VideoFrame.from_ndarray(frame, format='rgb24')
                    video_frame.pts = pts
                    video_frame.time_base = time_base

                    return video_frame
                finally:
                    buf.unmap(map_info)

        return None

    def stop(self):
        super().stop()
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        logger.info("GStreamer 파이프라인이 종료되었습니다")


async def run_webrtc():
    pc = RTCPeerConnection()
    video_sender = None
    websocket = None

    try:
        video_sender = JetsonVideoTrack()
        video_track = pc.addTrack(video_sender)
        logger.info("비디오 트랙이 추가되었습니다")

        # WebSocket 연결
        logger.info(f"시그널링 서버 연결 중... ({SIGNALING_SERVER})")
        websocket = await websockets.connect(
            SIGNALING_SERVER,
            ping_interval=20,
            ping_timeout=20
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
                            candidate = RTCIceCandidate(
                                candidate=candidate_data,
                                sdpMid=data.get("sdpMid"),
                                sdpMLineIndex=data.get("sdpMLineIndex")
                            )
                        else:
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