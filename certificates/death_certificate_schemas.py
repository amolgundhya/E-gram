from pydantic import BaseModel
from typing import Optional
from datetime import date

class DeathCertificateBase(BaseModel):
    date: Optional[date]
    register_date: Optional[date]
    village: Optional[str]
    deceased_name: Optional[str]
    gender: Optional[str]
    gender_en: Optional[str]
    death_date: Optional[date]
    place_of_death: Optional[str]
    mother_name: Optional[str]
    father_name: Optional[str]
    address_at_death: Optional[str]
    permanent_address: Optional[str]
    remark: Optional[str]
    deceased_name_en: Optional[str]
    place_of_death_en: Optional[str]
    mother_name_en: Optional[str]
    father_name_en: Optional[str]
    address_at_death_en: Optional[str]
    permanent_address_en: Optional[str]
    remark_en: Optional[str]
    barcode: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class DeathCertificateCreate(DeathCertificateBase):
    pass

class DeathCertificateRead(DeathCertificateBase):
    id: int
    qrcode: Optional[str] = None
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True 