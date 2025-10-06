from pydantic import BaseModel
from typing import Optional
from datetime import date

class WidowCertificateBase(BaseModel):
    id: Optional[int] = None
    registration_date: date
    village: Optional[str] = None
    village_en: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_name_en: Optional[str] = None
    husband_name: Optional[str] = None
    husband_name_en: Optional[str] = None
    adhar_number: Optional[str] = None
    adhar_number_en: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class WidowCertificateCreate(WidowCertificateBase):
    pass

class WidowCertificateRead(WidowCertificateBase):
    
    barcode: Optional[str] = None
    barcode_url: Optional[str] = None
    gramPanchayat: Optional[str] = None
    taluka: Optional[str] = None
    jilha: Optional[str] = None
    model_config = {
        "from_attributes": True
    } 