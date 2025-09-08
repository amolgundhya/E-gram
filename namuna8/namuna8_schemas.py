from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import datetime
# --- Owner Schemas ---
class OwnerBase(BaseModel):
    name: str
    aadhaarNumber: Optional[str] = None
    mobileNumber: Optional[str] = None
    wifeName: Optional[str] = None
    occupantName: Optional[str] = None
    ownerPhoto: Optional[str] = None
    village_id: int
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class OwnerCreate(OwnerBase):
    id: Optional[int] = None

class Owner(BaseModel):
    id: int
    name: str
    aadhaarNumber: Optional[str] = None
    mobileNumber: Optional[str] = None
    wifeName: Optional[str] = None
    occupantName: Optional[str] = None
    ownerPhoto: Optional[str] = None
    village_id: int
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None
    holderno: Optional[int] = None

    class Config:
        orm_mode = True

class OwnerUpdate(OwnerBase):
    id: Optional[int] = None

# --- Construction Schemas ---
class ConstructionBase(BaseModel):
    constructionType: str
    length: float
    width: float
    constructionYear: str
    floor: str
    # usage: str
    bharank: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class ConstructionCreate(ConstructionBase):
    pass

class Construction(BaseModel):
    id: int
    constructionType: str
    length: float
    width: float
    constructionYear: str
    floor: str
    bharank: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Property Schemas ---
class PropertyBase(BaseModel):
    id: Optional[int] = None
    village_id: int
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None
    anuKramank: int
    malmattaKramank: str
    streetName: Optional[str] = None
    citySurveyOrGatNumber: Optional[str] = None
    length: Optional[float] = None
    width: Optional[float] = None
    totalAreaSqFt: Optional[float] = None
    eastBoundary: Optional[str] = None
    westBoundary: Optional[str] = None
    northBoundary: Optional[str] = None
    southBoundary: Optional[str] = None
    divaArogyaKar: Optional[bool] = False
    safaiKar: Optional[bool] = False
    shauchalayKar: Optional[bool] = False
    karLaguNahi: Optional[bool] = False
    vacantLandType: Optional[str] = None
    waterFacility1: Optional[str] = None
    waterFacility2: Optional[str] = None
    toilet: Optional[str] = None
    roofType: Optional[str] = None
    eastBoundary2: Optional[str] = None
    westBoundary2: Optional[str] = None
    northBoundary2: Optional[str] = None
    southBoundary2: Optional[str] = None
    eastLength: Optional[float] = None
    westLength: Optional[float] = None
    northLength: Optional[float] = None
    southLength: Optional[float] = None
    totalArea: Optional[float] = None
    areaUnit: Optional[str] = None
    remarks: Optional[str] = None

class PropertyCreate(PropertyBase):
    owners: List[OwnerCreate]
    constructions: List[ConstructionCreate]
    qrcode: Optional[str] = None

class PropertyRead(PropertyBase):
    owners: List[Owner] = []
    constructions: List[Construction] = []
    divaKar: Optional[float] = None
    aarogyaKar: Optional[float] = None
    cleaningTax: Optional[float] = None
    toiletTax: Optional[float] = None
    sapanikar: Optional[float] = None
    vpanikar: Optional[float] = None
    qrcode: Optional[str] = None

    class Config:
        from_attributes = True

class PropertyUpdate(PropertyBase):
    owners: List[OwnerUpdate]
    constructions: List[ConstructionCreate]
    qrcode: Optional[str] = None

# --- Schema for the property list on the side ---
class PropertyList(BaseModel):
    malmattaKramank: str
    ownerName: str
    anuKramank: int
    holderno: Optional[int] = None

class BulkEditPropertyRow(BaseModel):
    serial_no: int
    malmattaKramank: str
    ownerName: str
    occupant: str  # always 'स्वतः' for now
    gharKar: float
    divaKar: float
    aarogyaKar: float
    sapanikar: float
    vpanikar: float

    class Config:
        orm_mode = True

class BulkEditUpdateRequest(BaseModel):
    property_ids: list[str]
    waterFacility1: Optional[str] = None
    waterFacility2: Optional[str] = None
    toilet: Optional[str] = None
    house: Optional[str] = None
    roofType: Optional[str] = None
    divaArogyaKar: Optional[bool] = None
    safaiKar: Optional[bool] = None
    shauchalayKar: Optional[bool] = None
    karLaguNahi: Optional[bool] = None
    waterFacility1Price: Optional[float] = None
    waterFacility2Price: Optional[float] = None
    # Add more fields as needed

class PropertyReportDTO(BaseModel):
    sr_no: int
    property_id: int
    village_info: Optional[str] = None
    owner_name: Optional[str] = None
    occupant_name: Optional[str] = None
    property_description: Optional[tuple[list, int]] = None  # (list of constructions, remaining area)
    dimension: Optional[tuple[float, float]] = None  # (length, width)
            
class ConstructionTypeBase(BaseModel):
    name: str
    rate: float
    bandhmastache_dar: float
    bandhmastache_prakar: int
    gharache_prakar: int
    annualLandValueRate: float = 0
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class ConstructionTypeCreate(ConstructionTypeBase):
    pass

class ConstructionType(ConstructionTypeBase):
    id: int
    class Config:
        from_attributes = True

class ConstructionTypeUpsert(BaseModel):
    id: Optional[int] = None
    name: str
    rate: float
    bandhmastache_dar: float
    bandhmastache_prakar: int
    gharache_prakar: int
    annualLandValueRate: float
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class BulkConstructionTypeUpsertRequest(BaseModel):
    construction_types: list[ConstructionTypeUpsert]

class VillageBase(BaseModel):
    name: str
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class VillageCreate(VillageBase):
    pass

class VillageRead(VillageBase):
    id: int
    class Config:
        from_attributes = True

class Namuna8SettingChecklistBase(BaseModel):
    tip: bool = False
    date: bool = False
    stamp: bool = False
    sachivSarpanch: bool = False
    total: bool = False
    tipRelatedPropertyDescription: bool = False
    roundupArea: bool = False
    boundaryMarking: bool = False
    aadharCard: bool = False
    mobileNumber: bool = False
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8SettingChecklistCreate(Namuna8SettingChecklistBase):
    pass

class Namuna8SettingChecklistRead(Namuna8SettingChecklistBase):
    id: int
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        orm_mode = True

class Namuna8SettingChecklistUpdate(BaseModel):
    id: Optional[int] = None
    tip: Optional[bool] = None
    date: Optional[bool] = None
    stamp: Optional[bool] = None
    sachivSarpanch: Optional[bool] = None
    total: Optional[bool] = None
    tipRelatedPropertyDescription: Optional[bool] = None
    roundupArea: Optional[bool] = None
    boundaryMarking: Optional[bool] = None
    aadharCard: Optional[bool] = None
    mobileNumberAdd: Optional[bool] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8DropdownAddSettingsBase(BaseModel):
    divaArogya: str
    khalijagevarAarogya: bool
    manoreDiva: bool
    reassessmentYear: int
    exemptionCount: int
    anukramank_id: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8DropdownAddSettingsCreate(Namuna8DropdownAddSettingsBase):
    pass

class Namuna8DropdownAddSettingsRead(Namuna8DropdownAddSettingsBase):
    id: int
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        orm_mode = True

class Namuna8DropdownAddSettingsUpdate(BaseModel):
    id: Optional[int] = None
    divaArogya: Optional[str] = None
    khalijagevarAarogya: Optional[bool] = None
    manoreDiva: Optional[bool] = None
    reassessmentYear: Optional[int] = None
    exemptionCount: Optional[int] = None
    anukramank_id: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8SettingTaxBase(BaseModel):
    lightUpto300: int
    healthUpto300: int
    cleaningUpto300: int
    bathroomUpto300: int
    light301_700: int
    health301_700: int
    cleaning301_700: int
    bathroom301_700: int
    lightAbove700: int
    healthAbove700: int
    cleaningAbove700: int
    bathroomAbove700: int
    generalWater: int
    generalWaterUpto300: int
    generalWater301_700: int
    generalWaterAbove700: int
    houseWater: Optional[int] = None
    commercialWater: Optional[int] = None
    exemptBuilding: Optional[int] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8SettingTaxCreate(Namuna8SettingTaxBase):
    pass

class Namuna8SettingTaxRead(BaseModel):
    id: int
    lightUpto300: Optional[int] = 0
    healthUpto300: Optional[int] = 0
    cleaningUpto300: Optional[int] = 0
    bathroomUpto300: Optional[int] = 0
    light301_700: Optional[int] = 0
    health301_700: Optional[int] = 0
    cleaning301_700: Optional[int] = 0
    bathroom301_700: Optional[int] = 0
    lightAbove700: Optional[int] = 0
    healthAbove700: Optional[int] = 0
    cleaningAbove700: Optional[int] = 0
    bathroomAbove700: Optional[int] = 0
    generalWater: Optional[int] = 0
    generalWaterUpto300: Optional[int] = 0
    generalWater301_700: Optional[int] = 0
    generalWaterAbove700: Optional[int] = 0
    houseWater: Optional[int] = 0
    commercialWater: Optional[int] = 0
    exemptBuilding: Optional[int] = 0
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None
    class Config:
        orm_mode = True

class Namuna8SettingTaxUpdate(BaseModel):
    id: Optional[int] = None
    lightUpto300: Optional[int] = None
    healthUpto300: Optional[int] = None
    cleaningUpto300: Optional[int] = None
    bathroomUpto300: Optional[int] = None
    light301_700: Optional[int] = None
    health301_700: Optional[int] = None
    cleaning301_700: Optional[int] = None
    bathroom301_700: Optional[int] = None
    lightAbove700: Optional[int] = None
    healthAbove700: Optional[int] = None
    cleaningAbove700: Optional[int] = None
    bathroomAbove700: Optional[int] = None
    generalWater: Optional[int] = None
    generalWaterUpto300: Optional[int] = None
    generalWater301_700: Optional[int] = None
    generalWaterAbove700: Optional[int] = None
    houseWater: Optional[int] = None
    commercialWater: Optional[int] = None
    exemptBuilding: Optional[int] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8WaterTaxSettingsBase(BaseModel):
    generalWater: int
    houseTax: float
    commercialTax: int
    exemptRate: float
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8WaterTaxSettingsCreate(Namuna8WaterTaxSettingsBase):
    pass

class Namuna8WaterTaxSettingsRead(Namuna8WaterTaxSettingsBase):
    id: int
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        orm_mode = True

class Namuna8WaterTaxSettingsUpdate(BaseModel):
    id: Optional[int] = None
    generalWater: Optional[int] = None
    houseTax: Optional[float] = None
    commercialTax: Optional[int] = None
    exemptRate: Optional[float] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8GeneralWaterTaxSlabSettingsBase(BaseModel):
    rateUpto300: Optional[float] = None
    rate301To700: Optional[float] = None
    rateAbove700: Optional[float] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class Namuna8GeneralWaterTaxSlabSettingsCreate(Namuna8GeneralWaterTaxSlabSettingsBase):
    pass

class Namuna8GeneralWaterTaxSlabSettingsRead(Namuna8GeneralWaterTaxSlabSettingsBase):
    id: int
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]

    class Config:
        orm_mode = True

class Namuna8GeneralWaterTaxSlabSettingsUpdate(BaseModel):
    id: Optional[int] = None
    rateUpto300: Optional[float] = None
    rate301To700: Optional[float] = None
    rateAbove700: Optional[float] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class BuildingUsageWeightageItem(BaseModel):
    serial: int
    usage: str
    weight: float
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class BulkNamuna8SettingsRequest(BaseModel):
    checklist: Optional[Namuna8SettingChecklistUpdate] = None
    dropdown: Optional[Namuna8DropdownAddSettingsUpdate] = None
    tax: Optional[Namuna8SettingTaxUpdate] = None
    watertax: Optional[Namuna8WaterTaxSettingsUpdate] = None
    watertaxslab: Optional[Namuna8GeneralWaterTaxSlabSettingsUpdate] = None
    construction_types: Optional[list[ConstructionTypeUpsert]] = None
    building_usage_weightage: Optional[List[BuildingUsageWeightageItem]] = None
    class Config:
        orm_mode = True