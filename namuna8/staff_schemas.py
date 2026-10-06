from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class StaffBase(BaseModel):
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None
    name: Optional[str] = None
    photo: Optional[str] = None
    designation: Optional[str] = None
    mobileNumber: Optional[str] = None
    tenure: Optional[str] = None
    duration: Optional[str] = None
    email: Optional[str] = None
    remarks: Optional[str] = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(StaffBase):
    pass


class StaffRead(StaffBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
