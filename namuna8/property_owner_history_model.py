from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from datetime import datetime
from database import Base

class PropertyOwnerHistory(Base):
    __tablename__ = 'property_owner_history'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False)  # Remove foreign key constraint
    # मालमत्तेचा खरा id (properties.id). property_id मध्ये अनुक्रमांक असतो - तो दोन गावांत
    # सारखा असू शकतो आणि Serialize / गाव बदल ने बदलतो; इतिहास नेहमी याच id ने शोधायचा.
    property_db_id = Column(Integer, nullable=True, index=True)
    village_id = Column(Integer, default=1)
    gram_panchayat_id = Column(Integer, default=1)
    district_id = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'property_id': self.property_id,
            'village_id': self.village_id,
            'gram_panchayat_id': self.gram_panchayat_id,
            'district_id': self.district_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_owners_history_list(self):
        """Returns list of OwnerHistory objects - similar to List<OwnerHistory> in Java"""
        return self.owners_history 