from pydantic import BaseModel
from typing import Optional
from datetime import date

class UnemploymentCertificateBase(BaseModel):
    registration_date: date
    village: Optional[str] = None
    village_en: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_name_en: Optional[str] = None
    adhar_number: Optional[str] = None
    adhar_number_en: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class UnemploymentCertificateCreate(UnemploymentCertificateBase):
    pass

class UnemploymentCertificateRead(UnemploymentCertificateBase):
    id: int
    image: Optional[str] = None
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True 