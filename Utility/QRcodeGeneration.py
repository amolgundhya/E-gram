import qrcode
import os
import json
from qrcode import constants
from PIL import Image

class QRCodeGeneration:
    @staticmethod
    def createQRcodeTemp(data: dict, save_path: str) -> str:
        qr = qrcode.QRCode(
            version=None,  # let library choose minimal version that fits
            error_correction=constants.ERROR_CORRECT_H,
            box_size=8,
            border=4,  # quiet zone recommended by ISO/IEC 18004
        )
        # Use UTF-8 JSON so Marathi characters are preserved
        qr.add_data(json.dumps(data, ensure_ascii=False))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Convert to PIL Image if not already
        if not isinstance(img, Image.Image):
            img = img.get_image()
        # Do not resample; preserve exact module edges for better scanning
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            img.save(f)
        return save_path
        
   
    @staticmethod
    def createQRcode(data : dict):
        qr = qrcode.QRCode(
            version=None,  # let library choose minimal version that fits
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=4,
        )

        # Encode as UTF-8 JSON so Marathi characters are preserved
        qr.add_data(json.dumps(data, ensure_ascii=False))
        qr.make(fit=True)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__) , '..'))
        static_dir = os.path.join(base_dir , 'reports')
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        img.save(os.path.join(static_dir , 'qrcode.png'))
        print("QR Code saved as 'qrcode.png'")
        