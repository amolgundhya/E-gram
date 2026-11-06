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

    @staticmethod
    def createQRcodeTextTemp(text: str, save_path: str) -> str:
        """createQRcodeTemp प्रमाणेच, पण JSON ऐवजी साधा वाचनीय मजकूर (plain text)
        एन्कोड करतो - स्कॅन केल्यावर माणसाला थेट वाचता यावं म्हणून. मजकूर जास्त असतो
        (JSON च्या तुलनेत) आणि देवनागरी अक्षरं UTF-8 मध्ये जास्त बाईट्स घेतात, त्यामुळे
        ERROR_CORRECT_H ऐवजी L वापरतो (M पेक्षाही जास्त क्षमता, त्यामुळे कमी QR
        version/कमी modules) - अन्यथा QR छापलेल्या (विशेषतः लहान) आकारात स्कॅन करणं
        अवघड होईल इतका दाट होतो. box_size=8 मुळे मूळ फाईल नेहमी ~500-900px एवढी मोठी
        राहते (CSS मध्ये लहान दाखवली तरी), जेणेकरून ब्राउझर/प्रिंट कमी करताना किनारी
        (edges) धारदार राहतील."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        if not isinstance(img, Image.Image):
            img = img.get_image()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, "wb") as f:
            img.save(f)
        return save_path

    @staticmethod
    def createQRcodeTextDataUri(text: str) -> str:
        """नाव प्लेटसारख्या ठिकाणी जिथे फाईल न लिहिता थेट base64 data URI लागते.
        createQRcodeTextTemp प्रमाणेच सेटिंग्ज (ERROR_CORRECT_L) - जेणेकरून नाव
        प्लेट/कचरा sticker चा QR नमुना-8 प्रिंटच्याच QR इतकाच सहज स्कॅन होईल."""
        import base64
        import io
        qr = qrcode.QRCode(
            version=None,
            error_correction=constants.ERROR_CORRECT_L,
            box_size=8,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        if not isinstance(img, Image.Image):
            img = img.get_image()
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
