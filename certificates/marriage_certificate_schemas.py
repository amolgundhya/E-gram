from pydantic import BaseModel
from typing import Optional
from datetime import date

class MarriageCertificateBase(BaseModel):
    id: int
    registration_date: date
    village: Optional[str] = None
    village_en: Optional[str] = None
    husband_name: Optional[str] = None
    husband_name_en: Optional[str] = None
    husband_adhar: Optional[str] = None
    husband_adhar_en: Optional[str] = None
    husband_address: Optional[str] = None
    husband_address_en: Optional[str] = None
    wife_name: Optional[str] = None
    wife_name_en: Optional[str] = None
    wife_adhar: Optional[str] = None
    wife_adhar_en: Optional[str] = None
    wife_address: Optional[str] = None
    wife_address_en: Optional[str] = None
    marriage_date: date
    marriage_register_no: Optional[str] = None
    marriage_register_subno: Optional[str] = None
    marriage_place: Optional[str] = None
    marriage_place_en: Optional[str] = None
    remark: Optional[str] = None
    remark_en: Optional[str] = None
    barcode: Optional[str] = None
    qrcode: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class MarriageCertificateCreate(MarriageCertificateBase):
    pass

class MarriageCertificateRead(MarriageCertificateBase):
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True