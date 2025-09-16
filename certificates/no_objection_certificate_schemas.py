from pydantic import BaseModel, constr, validator
from datetime import date
from typing import Optional

class NoObjectionCertificateBase(BaseModel):
    registration_date: date
    village: str
    village_en: str
    applicant_name: str
    applicant_name_en: str
    adhar_number: constr(min_length=4)
    adhar_number_en: constr(min_length=4)
    prop_gut_number: Optional[str] = None
    prop_gut_number_en: Optional[str] = None
    subject: str
    subject_en: str
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

    @validator('adhar_number', 'adhar_number_en')
    def must_be_digits(cls, v):
        if not v.isdigit():
            raise ValueError('Aadhaar number must be digits only')
        return v

class NoObjectionCertificateCreate(NoObjectionCertificateBase):
    pass

class NoObjectionCertificateRead(NoObjectionCertificateBase):
    id: int
    image_url: Optional[str] = None
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    class Config:
        orm_mode = True