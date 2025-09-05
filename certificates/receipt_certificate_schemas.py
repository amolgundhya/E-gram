from pydantic import BaseModel
from typing import Optional
from datetime import date

class ReceiptCertificateBase(BaseModel):
    receipt_date: date
    receipt_id: str
    village: Optional[str] = None
    village_en: Optional[str] = None
    name1: Optional[str] = None
    name1_en: Optional[str] = None
    name2: Optional[str] = None
    name2_en: Optional[str] = None
    receipt_amount: Optional[str] = None
    receipt_amount_en: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class ReceiptCertificateCreate(ReceiptCertificateBase):
    pass

class ReceiptCertificateRead(ReceiptCertificateBase):
    id: int
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True 