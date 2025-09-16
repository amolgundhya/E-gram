from pydantic import BaseModel
from typing import Optional
from datetime import date

class FamilyCertificateBase(BaseModel):
    registration_date: date
    village: Optional[str] = None
    village_en: Optional[str] = None
    family_name: Optional[str] = None
    family_name_en: Optional[str] = None
    adhar_number: Optional[str] = None
    adhar_number_en: Optional[str] = None
    record_no: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_name_en: Optional[str] = None
    relation: Optional[str] = None
    relation_en: Optional[str] = None
    year: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class FamilyCertificateCreate(FamilyCertificateBase):
    pass

class FamilyCertificateRead(FamilyCertificateBase):
    class Config:
        orm_mode = True
    id: int
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    