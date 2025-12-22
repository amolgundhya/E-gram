from pydantic import BaseModel
from typing import Optional, Union, List
from datetime import datetime

class Namuna9YearSetupBase(BaseModel):
    village: str
    year: str
    data_source: str
    notes: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None
    # Add more fields as needed for section 2/3
    # previous_year: Optional[str] = None
    # shakti_option: Optional[str] = None

class Namuna9YearSetupCreate(Namuna9YearSetupBase):
    pass

class Namuna9YearSetupRead(Namuna9YearSetupBase):
    id: int
    class Config:
        orm_mode = True

class Namuna9CarryForward(BaseModel):
    village: Union[str, int]
    from_year: str
    to_year: str
    carry_forward_option: str # e.g., "मागील एकूण चे" ~

class Namuna9SettingsBase(BaseModel):
    penalty_percentage: int
    notice_fee: int
    warrant_fee: int
    notes: Optional[str] = None
    keep_namuna9_date: bool = False
    keep_notice_date: bool = False
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna9SettingsCreate(Namuna9SettingsBase):
    pass

class Namuna9SettingsRead(Namuna9SettingsBase):
    id: int
    class Config:
        orm_mode = True
class Namuna9SettingsUpdate(BaseModel):
    penalty_percentage: Optional[int] = None
    notice_fee: Optional[int] = None
    warrant_fee: Optional[int] = None
    notes: Optional[str] = None
    keep_namuna9_date: Optional[bool] = None
    keep_notice_date: Optional[bool] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

# Schemas for Namuna9PropertyData
class Namuna9PropertyDataBase(BaseModel):
    property_id: int
    shaktiGhar: float = 0.0
    shaktiDiva: float = 0.0
    shaktiAarogyaKar: float = 0.0
    shaktiSapanikar: float = 0.0
    shaktiVpanikar: float = 0.0
    shaktiCleaningTax: float = 0.0
    dand: float = 0.0
    chaluGhar: float = 0.0
    chaluDiva: float = 0.0
    chaluAarogyaKar: float = 0.0
    chaluSapanikar: float = 0.0
    chaluVpanikar: float = 0.0
    chaluCleaningTax: float = 0.0
    ekunGhar: float = 0.0
    ekunDiva: float = 0.0
    ekunAarogyaKar: float = 0.0
    ekunSapanikar: float = 0.0
    ekunVpanikar: float = 0.0
    ekunCleaningTax: float = 0.0
    warrantFee: float = 0.0
    noticeFee: float = 0.0
    total: float = 0.0
    # vasuli
    vasuliGhar: float = 0.0
    vasuliDiva: float = 0.0
    vasuliAarogyaKar: float = 0.0
    vasuliSapanikar: float = 0.0
    vasuliVpanikar: float = 0.0
    vasuliCleaningTax: float = 0.0
    vasuliDand: float = 0.0
    vasuliNoticeFee: float = 0.0
    vasuliWarrantFee: float = 0.0

class Namuna9PropertyDataCreate(Namuna9PropertyDataBase):
    namuna9_id: int

class Namuna9PropertyDataUpdate(BaseModel):
    shaktiGhar: Optional[float] = None
    shaktiDiva: Optional[float] = None
    shaktiAarogyaKar: Optional[float] = None
    shaktiSapanikar: Optional[float] = None
    shaktiVpanikar: Optional[float] = None
    shaktiCleaningTax: Optional[float] = None
    dand: Optional[float] = None
    chaluGhar: Optional[float] = None
    chaluDiva: Optional[float] = None
    chaluAarogyaKar: Optional[float] = None
    chaluSapanikar: Optional[float] = None
    chaluVpanikar: Optional[float] = None
    chaluCleaningTax: Optional[float] = None
    ekunGhar: Optional[float] = None
    ekunDiva: Optional[float] = None
    ekunAarogyaKar: Optional[float] = None
    ekunSapanikar: Optional[float] = None
    ekunVpanikar: Optional[float] = None
    ekunCleaningTax: Optional[float] = None
    warrantFee: Optional[float] = None
    noticeFee: Optional[float] = None
    total: Optional[float] = None
    vasuliGhar: Optional[float] = None
    vasuliDiva: Optional[float] = None
    vasuliAarogyaKar: Optional[float] = None
    vasuliSapanikar: Optional[float] = None
    vasuliVpanikar: Optional[float] = None
    vasuliCleaningTax: Optional[float] = None
    vasuliDand: Optional[float] = None
    vasuliNoticeFee: Optional[float] = None
    vasuliWarrantFee: Optional[float] = None

# Upsert schema used in bulk updates: requires property_id to target a row
class Namuna9PropertyDataUpsert(BaseModel):
    property_id: int
    shaktiGhar: Optional[float] = None
    shaktiDiva: Optional[float] = None
    shaktiAarogyaKar: Optional[float] = None
    shaktiSapanikar: Optional[float] = None
    shaktiVpanikar: Optional[float] = None
    shaktiCleaningTax: Optional[float] = None
    dand: Optional[float] = None
    chaluGhar: Optional[float] = None
    chaluDiva: Optional[float] = None
    chaluAarogyaKar: Optional[float] = None
    chaluSapanikar: Optional[float] = None
    chaluVpanikar: Optional[float] = None
    chaluCleaningTax: Optional[float] = None
    ekunGhar: Optional[float] = None
    ekunDiva: Optional[float] = None
    ekunAarogyaKar: Optional[float] = None
    ekunSapanikar: Optional[float] = None
    ekunVpanikar: Optional[float] = None
    ekunCleaningTax: Optional[float] = None
    warrantFee: Optional[float] = None
    noticeFee: Optional[float] = None
    total: Optional[float] = None
    vasuliGhar: Optional[float] = None
    vasuliDiva: Optional[float] = None
    vasuliAarogyaKar: Optional[float] = None
    vasuliSapanikar: Optional[float] = None
    vasuliVpanikar: Optional[float] = None
    vasuliCleaningTax: Optional[float] = None
    vasuliDand: Optional[float] = None
    vasuliNoticeFee: Optional[float] = None
    vasuliWarrantFee: Optional[float] = None

class Namuna9Collect(BaseModel):
    namuna9_id: int
    property_id: int
    vasuliGhar: float = 0.0
    vasuliChaluGhar: float = 0.0
    vasuliDiva: float = 0.0
    vasuliChaluDiva: float = 0.0
    vasuliAarogyaKar: float = 0.0
    vasuliChaluAarogyaKar: float = 0.0
    vasuliSapanikar: float = 0.0
    vasuliChaluSapanikar: float = 0.0
    vasuliVpanikar: float = 0.0
    vasuliChaluVpanikar: float = 0.0
    vasuliCleaningTax: float = 0.0
    vasuliChaluCleaningTax: float = 0.0
    vasuliDand: float = 0.0
    vasuliNoticeFee: float = 0.0
    vasuliWarrantFee: float = 0.0

class Namuna9ReceiptCreate(BaseModel):
    namuna9_id: int
    property_id: int
    gram_panchayat_id: int
    pa_book_kramank: Optional[str] = None
    pavti_kramank: int
    pavti_date: Optional[str] = None
    payment_mode: Optional[str] = None
    utr_tr_id: Optional[str] = None
    vasuliGhar: float = 0.0
    vasuliChaluGhar: float = 0.0
    vasuliDiva: float = 0.0
    vasuliChaluDiva: float = 0.0
    vasuliAarogyaKar: float = 0.0
    vasuliChaluAarogyaKar: float = 0.0
    vasuliSapanikar: float = 0.0
    vasuliChaluSapanikar: float = 0.0
    vasuliVpanikar: float = 0.0
    vasuliChaluVpanikar: float = 0.0
    vasuliCleaningTax: float = 0.0
    vasuliChaluCleaningTax: float = 0.0
    vasuliDand: float = 0.0
    vasuliNoticeFee: float = 0.0
    vasuliWarrantFee: float = 0.0
    total: float = 0.0
    # Optional snapshot fields; backend will populate if not provided
    owner_name: Optional[str] = None
    malmatta_kramank: Optional[str] = None

class Namuna9ReceiptRead(BaseModel):
    id: int
    namuna9_id: int
    property_id: int
    gram_panchayat_id: Optional[int] = None
    pa_book_kramank: Optional[str] = None
    pavti_kramank: int
    pavti_date: Union[str, datetime, None]
    owner_name: Optional[str] = None
    malmatta_kramank: Optional[str] = None
    # Stored snapshot of vasuli values for this receipt
    vasuliGhar: float
    vasuliChaluGhar: float
    vasuliDiva: float
    vasuliChaluDiva: float
    vasuliAarogyaKar: float
    vasuliChaluAarogyaKar: float
    vasuliSapanikar: float
    vasuliChaluSapanikar: float
    vasuliVpanikar: float
    vasuliChaluVpanikar: float
    vasuliCleaningTax: float
    vasuliChaluCleaningTax: float
    vasuliDand: float
    vasuliNoticeFee: float
    vasuliWarrantFee: float
    total: float
    payment_mode: Optional[str] = None
    utr_tr_id: Optional[str] = None
    createdAt: Optional[datetime] = None
    # Enriched fields
    grampanchayat: Optional[str] = None
    district: Optional[str] = None
    taluka: Optional[str] = None
    village: Optional[str] = None
    occupant: Optional[str] = None
    yearslap: Optional[str] = None
    class Config: 
       orm_mode = True

class Namuna9PropertyDataRead(Namuna9PropertyDataBase):
    id: int
    namuna9_id: int
    class Config: 
       orm_mode = True

# Schema for bulk update of property data
class Namuna9BulkPropertyDataUpdate(BaseModel):
    namuna9_id: int
    property_data: List[Namuna9PropertyDataUpsert]