from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from database import Base


class Namuna7(Base):
    __tablename__ = 'namuna7'

    id = Column(Integer, primary_key=True, autoincrement=True)
    receiptNumber = Column(Integer, nullable=False)
    receiptBookNumber = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    receivedMoney = Column(Integer, nullable=False)
    userId = Column(Integer, ForeignKey('owners.id'), nullable=False)
    villageId = Column(Integer, ForeignKey('villages.id'), nullable=False)
    malmattaKramank = Column(String, nullable=True)
    anuKramank = Column(Integer, nullable=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=True)
    taluka_id = Column(Integer, ForeignKey("talukas.id"), nullable=True)
    gram_panchayat_id = Column(Integer, ForeignKey("gram_panchayats.id"), nullable=True)
    createdAt = Column(DateTime, default=datetime.utcnow)
    updatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # सॉफ्ट-डिलीट - namuna9_receipts प्रमाणेच, पावती कधीच पूर्णपणे काढायची नाही.
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(String, nullable=True)
    delete_reason = Column(Text, nullable=True)