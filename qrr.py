#!/usr/bin/python3
import qrcode
import json
from datetime import datetime

def generate_qr(data: dict, filename: str):
    """
    통일된 형식의 데이터를 받아 QR 코드를 생성합니다.
    
    매개변수:
      data: dict  
            예시)
              {"type": "stop", "location": "(6,0)"}
              {"type": "loading", "location": "(3,3)"}
              {"type": "obstacle", "location": "(2,2)", "message": "Obstacle detected, waiting for removal"}
              {"type": "unloading", "location": "(2,0)"}
      filename: 생성될 QR 코드 이미지 파일명 (예: "qr_stop_6_0.png")
    """
    # 타임스탬프가 없으면 현재 시간 추가
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    # JSON 문자열로 변환 (일관된 데이터 포맷 유지)
    qr_data = json.dumps(data, sort_keys=True)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    print(f"QR 코드가 생성되어 '{filename}' 파일에 저장되었습니다.")

if __name__ == "__main__":
    # 테스트 샘플: 정지 이벤트
    sample_data = {"type": "stop", "location": "(6,0)"}
    generate_qr(sample_data, "qr_stop_6_0.png")
