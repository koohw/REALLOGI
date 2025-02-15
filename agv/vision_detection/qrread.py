import qrcode

# y: 8부터 0까지, x: 0부터 8까지
for y in range(8, -1, -1):
    for x in range(0, 9):
        data_str = f"{y},{x}"  # 예: "8,0", "8,1", ..., "0,8"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,    # 기존보다 5배 큰 크기
            border=1,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        filename = f"qr_{y}_{x}.png"
        img.save(filename)
        print(f"Saved QR for position ({y}, {x}) as {filename}")
