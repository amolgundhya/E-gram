from pydantic import BaseModel
from typing import Optional
from datetime import date

class BirthCertificateBase(BaseModel):
    date: Optional[date]
    register_date: Optional[date]
    village: Optional[str]
    child_name: Optional[str]
    child_name_en: str
    gender: Optional[str]
    gender_en: Optional[str]
    panhera: Optional[str]
    birth_date: Optional[date]
    birth_place: Optional[str]
    birth_place_en: Optional[str]
    mother_name: Optional[str]
    mother_name_en: str
    father_name: Optional[str]
    father_name_en: str
    address_at_birth: Optional[str]
    address_at_birth_en: str
    permanent_address: Optional[str]
    permanent_address_en: str
    remark: Optional[str]
    remark_en: str
    barcode: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class BirthCertificateCreate(BirthCertificateBase):
    id: Optional[int] = None

class BirthCertificateRead(BirthCertificateBase):
    id: int
    qrcode: Optional[str] = None
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True 