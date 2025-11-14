from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base

class PropertyDocument(Base):
    __tablename__ = "property_documents"
    id = Column(Integer, primary_key=True, index=True)
    document_name = Column(String, nullable=False)
    document_path = Column(String, nullable=True)
    document_image = Column(String, nullable=True)  # Store image path or filename
    village_id = Column(Integer,nullable=False)
    property_anuKramank = Column(Integer, ForeignKey("properties.anuKramank"), nullable=False)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    taluka_id = Column(Integer, ForeignKey("talukas.id"), nullable=True)
    gram_panchayat_id = Column(Integer, ForeignKey("gram_panchayats.id"), nullable=True) 