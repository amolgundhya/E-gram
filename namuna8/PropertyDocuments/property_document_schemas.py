from pydantic import BaseModel
from typing import Optional

class PropertyDocumentBase(BaseModel):
    document_name: str
    document_path: Optional[str] = None
    document_image: Optional[str] = None
    village_id : int
    property_anuKramank: int
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class PropertyDocumentCreate(PropertyDocumentBase):
    pass

class PropertyDocumentResponse(PropertyDocumentBase):
    id: int

    class Config:
        orm_mode = True 