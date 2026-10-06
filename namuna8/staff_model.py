from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from datetime import datetime


class GramPanchayatStaff(Base):
    __tablename__ = "gram_panchayat_staff"
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"), nullable=True)
    taluka_id: Mapped[int] = mapped_column(ForeignKey("talukas.id", ondelete="CASCADE"), nullable=True)
    gram_panchayat_id: Mapped[int] = mapped_column(ForeignKey("gram_panchayats.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(nullable=True)          # अधिकाऱ्याचे नांव
    photo: Mapped[str] = mapped_column(nullable=True)         # फोटो
    designation: Mapped[str] = mapped_column(nullable=True)   # पद
    mobileNumber: Mapped[str] = mapped_column(nullable=True)  # मोबाईल नंबर
    tenure: Mapped[str] = mapped_column(nullable=True)        # कार्यकाळ
    duration: Mapped[str] = mapped_column(nullable=True)      # कालावधी
    email: Mapped[str] = mapped_column(nullable=True)         # मेल
    remarks: Mapped[str] = mapped_column(nullable=True)       # शेरा
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.now)
