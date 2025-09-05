from pydantic import BaseModel
from typing import Optional
from datetime import date

class ResidentCertificateBase(BaseModel):
    dispatch_no: Optional[str]
    date: Optional[date]
    village: Optional[str]
    village_en: Optional[str]
    applicant_name: Optional[str]
    applicant_name_en: Optional[str]
    adhar_no: Optional[str]
    adhar_no_en: Optional[str]
    image_url: Optional[str]
    barcode: Optional[str]
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class ResidentCertificateCreate(ResidentCertificateBase):
    pass

class ResidentCertificateRead(ResidentCertificateBase):
    id: int
    image_url: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True 