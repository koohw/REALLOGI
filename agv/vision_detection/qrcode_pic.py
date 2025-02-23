import qrcode

# 완전 축약된 형태 (문자열 “p1,1cstopd10” 정도)
data_str = "2,1,s10"  

qr = qrcode.QRCode(
    version=1,  
    error_correction=qrcode.constants.ERROR_CORRECT_L,
    box_size=1,
    border=1,
)
qr.add_data(data_str)
qr.make(fit=True)
img = qr.make_image(fill_color="black", back_color="white")
img.save("qr_ver_3.png")