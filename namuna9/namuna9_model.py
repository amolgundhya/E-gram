from sqlalchemy import Column, Integer, String, Text, DateTime, Table, ForeignKey, UniqueConstraint, PickleType, Boolean, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import uuid

namuna9_property_association = Table(
    "namuna9_property_association",
    Base.metadata,
    Column("namuna9_id", Integer, ForeignKey("namuna9.id")),
    Column("property_id", Integer, ForeignKey("properties.anuKramank"))
)

class Namuna9YearSetup(Base):
    __tablename__ = "namuna9_year_setups"
    id = Column(Integer, primary_key=True, index=True)
    village = Column(String, index=True)
    year = Column(String, index=True)
    data_source = Column(String)
    notes = Column(Text, nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    taluka_id = Column(Integer, ForeignKey("talukas.id"), nullable=True)
    gram_panchayat_id = Column(Integer, ForeignKey("gram_panchayats.id"), nullable=True)
    # Add more fields as needed for section 2/3
    # e.g., previous_year, shakti_option, etc. 

class Namuna9PropertyData(Base):
    """Model to store individual property tax data for Namuna9"""
    __tablename__ = "namuna9_property_data"
    __table_args__ = (
        UniqueConstraint("namuna9_id", "property_id", name="uix_namuna9_property"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    namuna9_id = Column(Integer, ForeignKey("namuna9.id"), nullable=False)
    property_id = Column(Integer, nullable=False)  # Property anuKramank
    
    # थकित (Arrears) fields
    shaktiGhar = Column(Float, default=0.0)  # थकित घर
    shaktiDiva = Column(Float, default=0.0)  # थकित दिवा
    shaktiAarogyaKar = Column(Float, default=0.0)  # थकित आ.कर.
    shaktiSapanikar = Column(Float, default=0.0)  # थकित सा.पाणी
    shaktiVpanikar = Column(Float, default=0.0)  # थकित वि.पाणी
    shaktiCleaningTax = Column(Float, default=0.0)  # थकित शौ.कर
    
    # दंड (Penalty) field
    dand = Column(Float, default=0.0)  # दंड
    
    # चालू (Current) fields
    chaluGhar = Column(Float, default=0.0)  # चालू घर
    chaluDiva = Column(Float, default=0.0)  # चालू दिवा
    chaluAarogyaKar = Column(Float, default=0.0)  # चालू आ.कर.
    chaluSapanikar = Column(Float, default=0.0)  # चालू सा.पाणी
    chaluVpanikar = Column(Float, default=0.0)  # चालू वि.पाणी
    chaluCleaningTax = Column(Float, default=0.0)  # चालू शौ.कर
    
    # एकूण (Total) fields
    ekunGhar = Column(Float, default=0.0)  # एकूण घर
    ekunDiva = Column(Float, default=0.0)  # एकूण दिवा
    ekunAarogyaKar = Column(Float, default=0.0)  # एकूण आ.कर.
    ekunSapanikar = Column(Float, default=0.0)  # एकूण सा.पाणी
    ekunVpanikar = Column(Float, default=0.0)  # एकूण वि.पाणी
    ekunCleaningTax = Column(Float, default=0.0)  # एकूण शौ.कर
    
    # Fees
    warrantFee = Column(Float, default=0.0)  # वारंट फी
    noticeFee = Column(Float, default=0.0)  # नोटीस फी
    
    # Total
    total = Column(Float, default=0.0)  # एकूण

    # Vasuli (collections) - amounts collected against arrears
    vasuliGhar = Column(Float, default=0.0)
    vasuliChaluGhar = Column(Float, default=0.0)
    vasuliDiva = Column(Float, default=0.0)
    vasuliChaluDiva = Column(Float, default=0.0)
    vasuliAarogyaKar = Column(Float, default=0.0)
    vasuliChaluAarogyaKar = Column(Float, default=0.0)
    vasuliSapanikar = Column(Float, default=0.0)
    vasuliChaluSapanikar = Column(Float, default=0.0)
    vasuliVpanikar = Column(Float, default=0.0)
    vasuliChaluVpanikar = Column(Float, default=0.0)
    vasuliCleaningTax = Column(Float, default=0.0)
    vasuliChaluCleaningTax = Column(Float, default=0.0)
    vasuliDand = Column(Float, default=0.0)
    vasuliNoticeFee = Column(Float, default=0.0)
    vasuliWarrantFee = Column(Float, default=0.0)
    
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    namuna9 = relationship("Namuna9", back_populates="property_data")

class Namuna9(Base):
    __tablename__ = "namuna9"
    __table_args__ = (
        UniqueConstraint("villageId", "yearslap", name="uix_village_yearslap"),
    )
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doesThakit = Column(Boolean, default=False)
    thakitValues = Column(String, nullable=True)
    thakitYear = Column(String(9), nullable=True)  # yearslap for thakit
    yearslap = Column(String(9), nullable=False)
    villageId = Column(String(36), nullable=False)
    grampanchayatId = Column(String(36), nullable=False)
    property_ids = Column(PickleType, nullable=True)  # List of property IDs
    createdAt = Column(DateTime(timezone=True), server_default=func.now())
    updatedAt = Column(DateTime(timezone=True), onupdate=func.now())
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    taluka_id = Column(Integer, ForeignKey("talukas.id"), nullable=True)
    gram_panchayat_id = Column(Integer, ForeignKey("gram_panchayats.id"), nullable=True)
    
    # Relationship
    property_data = relationship("Namuna9PropertyData", back_populates="namuna9", cascade="all, delete-orphan")

class Namuna9Receipt(Base):
    __tablename__ = "namuna9_receipts"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    namuna9_id = Column(Integer, ForeignKey("namuna9.id"), nullable=False)
    property_id = Column(Integer, nullable=False)
    gram_panchayat_id = Column(Integer, nullable=True)
    # Snapshot fields for display
    owner_name = Column(String, nullable=True)
    malmatta_kramank = Column(String, nullable=True)
    pa_book_kramank = Column(String, nullable=True)
    pavti_kramank = Column(Integer, nullable=False)
    pavti_date = Column(DateTime(timezone=True), server_default=func.now())
    payment_mode = Column(String, nullable=True)
    utr_tr_id = Column(String, nullable=True)

    # Stored snapshot of vasuli values for this receipt
    vasuliGhar = Column(Float, default=0.0)
    vasuliChaluGhar = Column(Float, default=0.0)
    vasuliDiva = Column(Float, default=0.0)
    vasuliChaluDiva = Column(Float, default=0.0)
    vasuliAarogyaKar = Column(Float, default=0.0)
    vasuliChaluAarogyaKar = Column(Float, default=0.0)
    vasuliSapanikar = Column(Float, default=0.0)
    vasuliChaluSapanikar = Column(Float, default=0.0)
    vasuliVpanikar = Column(Float, default=0.0)
    vasuliChaluVpanikar = Column(Float, default=0.0)
    vasuliCleaningTax = Column(Float, default=0.0)
    vasuliChaluCleaningTax = Column(Float, default=0.0)
    vasuliDand = Column(Float, default=0.0)
    vasuliNoticeFee = Column(Float, default=0.0)
    vasuliWarrantFee = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    createdAt = Column(DateTime(timezone=True), server_default=func.now())