from pydantic import BaseModel
from typing import Optional
from datetime import date

class BirthDeathUnavailabilityCertificateBase(BaseModel):
    id: Optional[int] = None
    register_date: Optional[date]
    village: Optional[str]
    village_en: Optional[str]
    applicant_name: Optional[str]
    applicant_name_en: Optional[str]
    adhar_number: Optional[str]
    adhar_number_en: Optional[str]
    certificate_name: Optional[str]
    certificate_name_en: Optional[str]
    subject: Optional[str]
    subject_en: Optional[str]
    barcode: str | None = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class BirthDeathUnavailabilityCertificateCreate(BirthDeathUnavailabilityCertificateBase):
    pass

class BirthDeathUnavailabilityCertificateRead(BirthDeathUnavailabilityCertificateBase):
    barcode: str | None = None
    barcode_url: str | None = None
    gramPanchayat: str | None = None
    taluka: str | None = None
    jilha: str | None = None
    model_config = {
        "from_attributes": True
    } 