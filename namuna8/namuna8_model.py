import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Table,DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base
from datetime import datetime
import uuid


# Association table for many-to-many relationship between Property and Owner
property_owner_association = Table(
    "property_owner_association",
    Base.metadata,
    Column("id", Integer, ForeignKey("properties.id")),
    Column("owner_id", Integer, ForeignKey("owners.id"))
)
class Village(Base):
    __tablename__ = "villages"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(unique=True)
    properties = relationship("Property", back_populates="village", cascade="all, delete-orphan")
    owners = relationship("Owner", back_populates="village", cascade="all, delete-orphan")
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)

class Owner(Base):
    __tablename__ = "owners"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column()
    aadhaarNumber: Mapped[str] = mapped_column(index=True, nullable=True)
    mobileNumber: Mapped[str] = mapped_column(nullable=True)
    wifeName: Mapped[str] = mapped_column(nullable=True)
    occupantName: Mapped[str] = mapped_column(nullable=True)
    ownerPhoto: Mapped[str] = mapped_column(nullable=True)
    holderno: Mapped[int] = mapped_column(nullable=True)  # धारक नंबर
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id", ondelete="CASCADE"))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    village = relationship("Village", back_populates="owners")
    properties = relationship("Property", secondary=property_owner_association, back_populates="owners")
   
class Property(Base):
    __tablename__ = "properties"
    id : Mapped[int] = mapped_column(primary_key=True, index=True)
    anuKramank: Mapped[int] = mapped_column(nullable=False)
    village_id: Mapped[int] = mapped_column(ForeignKey("villages.id", ondelete="CASCADE"))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    village = relationship("Village", back_populates="properties")
    malmattaKramank: Mapped[str] = mapped_column(String, index=True, nullable=False)
    streetName: Mapped[str] = mapped_column(nullable=True)
    citySurveyOrGatNumber: Mapped[str] = mapped_column(nullable=True)
    length: Mapped[float] = mapped_column(nullable=True)
    width: Mapped[float] = mapped_column(nullable=True)
    totalAreaSqFt: Mapped[float] = mapped_column(nullable=True)
    eastBoundary: Mapped[str] = mapped_column(nullable=True)
    westBoundary: Mapped[str] = mapped_column(nullable=True)
    northBoundary: Mapped[str] = mapped_column(nullable=True)
    southBoundary: Mapped[str] = mapped_column(nullable=True)
    divaArogyaKar: Mapped[bool] = mapped_column(default=False)
    safaiKar: Mapped[bool] = mapped_column(default=False)
    shauchalayKar: Mapped[bool] = mapped_column(default=False)
    karLaguNahi: Mapped[bool] = mapped_column(default=False)
    dwarPurv: Mapped[bool] = mapped_column(default=False)
    dwarPashchim: Mapped[bool] = mapped_column(default=False)
    dwarUttar: Mapped[bool] = mapped_column(default=False)
    dwarDakshin: Mapped[bool] = mapped_column(default=False)
    gharKar: Mapped[float] = mapped_column(default=0)
    vacantLandType: Mapped[str] = mapped_column("vacantLandType", nullable=True)
    eastBoundary2: Mapped[str] = mapped_column(nullable=True)
    westBoundary2: Mapped[str] = mapped_column(nullable=True)
    northBoundary2: Mapped[str] = mapped_column(nullable=True)
    southBoundary2: Mapped[str] = mapped_column(nullable=True)
    waterFacility1: Mapped[str] = mapped_column(nullable=True)
    waterFacility2: Mapped[str] = mapped_column(nullable=True)
    toilet: Mapped[str] = mapped_column(nullable=True)
    toiletBenefitYear: Mapped[str] = mapped_column(nullable=True)  # शौचालय योजना लाभ वर्ष
    roofType: Mapped[str] = mapped_column(nullable=True)
    gharkul: Mapped[str] = mapped_column(nullable=True)  # घरकुल: आहे/नाही
    gharkulYojana: Mapped[str] = mapped_column(nullable=True)  # घरकुल योजनेचे नाव
    gharkulBenefitYear: Mapped[str] = mapped_column(nullable=True)  # घरकुल योजना लाभ वर्ष
    eastLength: Mapped[float] = mapped_column(nullable=True)
    westLength: Mapped[float] = mapped_column(nullable=True)
    northLength: Mapped[float] = mapped_column(nullable=True)
    southLength: Mapped[float] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)
    areaUnit: Mapped[str] = mapped_column(nullable=True)
    # बांधकामाचे प्रकार तक्त्यातील लांबी/रुंदी कोणत्या एककात आहेत - areaUnit (एकूण जागेचे
    # एकक) पेक्षा वेगळं असू शकतं, त्यामुळे वेगळं साठवतो. रिकामं असल्यास areaUnit प्रमाणेच धरायचं.
    constructionAreaUnit: Mapped[str] = mapped_column(nullable=True)
    totalArea: Mapped[float] = mapped_column(nullable=True)
    qrcode: Mapped[str] = mapped_column(nullable=True)  # Path/URL to QR code image
    constructions = relationship("Construction", back_populates="property", cascade="all, delete-orphan")
    owners = relationship("Owner", secondary=property_owner_association, back_populates="properties")
    remarks: Mapped[str] = mapped_column(nullable=True)
    # यादीतला डिस्प्ले-क्रम - मालमत्ता क्रमांकाच्या मजकुरावरून काढलेल्या नैसर्गिक
    # क्रमवारीऐवजी हाच वापरायचा, जेणेकरून "Insert" ने घातलेली मालमत्ता निवडलेल्या
    # मालमत्तेनंतर लगेच दिसेल, तिचा मालमत्ता क्रमांक काहीही असो. अ.क्र. (anuKramank) पासून
    # पूर्णपणे वेगळं - तो कधीच बदलत नाही.
    sort_order: Mapped[float] = mapped_column(nullable=True)
    # आजी/माजी सैनिक - प्रत्येक मालमत्तेनुसार (MASTER मधल्या जुन्या ग्लोबल सेटिंगऐवजी).
    # टिक असल्यास प्रिंट्सवर सैनिक टीप दाखवायची.
    exServiceman: Mapped[bool] = mapped_column(default=False)


class ConstructionType(Base):
    __tablename__ = "construction_types"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column()
    rate: Mapped[float] = mapped_column()
    bandhmastache_dar: Mapped[float] = mapped_column()
    bandhmastache_prakar: Mapped[int] = mapped_column()
    gharache_prakar: Mapped[int] = mapped_column()
    annualLandValueRate: Mapped[float] = mapped_column(default=0)
    # Add other fields as needed

    constructions = relationship("Construction", back_populates="construction_type")

class Construction(Base):
    __tablename__ = "constructions"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id", ondelete="CASCADE"))
    construction_type_id: Mapped[int] = mapped_column(ForeignKey("construction_types.id"))
    length: Mapped[float] = mapped_column()
    width: Mapped[float] = mapped_column()
    constructionYear: Mapped[str] = mapped_column()
    floor: Mapped[str] = mapped_column()
    # usage: Mapped[str] = mapped_column()
    bharank: Mapped[str] = mapped_column(nullable=True)
    houseTax:Mapped[float] = mapped_column(nullable=True)
    capitalValue:Mapped[float] = mapped_column(nullable=True)

    property = relationship("Property", back_populates="constructions")
    construction_type = relationship("ConstructionType", back_populates="constructions")
    
class Namuna8SettingChecklist(Base):
    __tablename__ = "namuna8_setting_checklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), unique=True, nullable=False)
    tip = Column(Boolean, default=False)
    date = Column(Boolean, default=False)
    stamp = Column(Boolean, default=False)
    sachivSarpanch = Column(Boolean, default=False)
    total = Column(Boolean, default=False)
    tipRelatedPropertyDescription = Column(Boolean, default=False)
    roundupArea = Column(Boolean, default=False)
    boundaryMarking = Column(Boolean, default=False)
    aadharCard = Column(Boolean, default=False)
    mobileNumberAdd = Column(Boolean, default=False)
    pageNumber = Column(Boolean, default=False)
    exportPassword = Column(String, nullable=True)  # Excel export उघडण्यासाठी पासवर्ड - रिकामं असेल तर पासवर्डशिवाय export होतो

    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Namuna8DropdownAddSettings(Base):
    __tablename__ = "namuna8DropdownAddSettings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), unique=True, nullable=False)
    divaArogya = Column(String)
    khalijagevarAarogya = Column(Boolean)
    manoreDiva = Column(Boolean)
    reassessmentYear = Column(Integer)
    exemptionCount = Column(Integer)
    anukramank_id = Column(String, nullable=True)
    # कर रक्कम राउंडिंग - "ceil" (नेहमी वरचा रुपया, डिफॉल्ट) किंवा "half_up" (साधारण नियम).
    taxRoundingMode = Column(String, nullable=True, default="ceil")
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Namuna8SettingTax(Base):
    __tablename__ = "namuna8SettingTax"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), unique=True, nullable=False)
    lightUpto300 = Column(Integer)
    healthUpto300 = Column(Integer)
    cleaningUpto300 = Column(Integer)
    bathroomUpto300 = Column(Integer)
    light301_700 = Column(Integer)
    health301_700 = Column(Integer)
    cleaning301_700 = Column(Integer)
    bathroom301_700 = Column(Integer)
    lightAbove700 = Column(Integer)
    healthAbove700 = Column(Integer)
    cleaningAbove700 = Column(Integer)
    bathroomAbove700 = Column(Integer)
    generalWater = Column(Integer)
    generalWaterUpto300 = Column(Integer)
    generalWater301_700 = Column(Integer)
    generalWaterAbove700 = Column(Integer)
    houseWater = Column(Integer)
    commercialWater = Column(Integer)
    exemptBuilding = Column(Integer)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Namuna8WaterTaxSettings(Base):
    __tablename__ = "namuna8WaterTaxSettings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), unique=True, nullable=False)
    generalWater = Column(Integer)
    houseTax = Column(Float)
    commercialTax = Column(Integer)
    exemptRate = Column(Float)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
class Namuna8GeneralWaterTaxSlabSettings(Base):
    __tablename__ = "namuna8GeneralWaterTaxSlabSettings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), unique=True, nullable=False)
    rateUpto300 = Column(Float)
    rate301To700 = Column(Float)
    rateAbove700 = Column(Float)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
