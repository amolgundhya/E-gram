from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime
from typing import List, Optional
from namuna8 import namuna8_model as models, namuna8_schemas as schemas
from database import get_db, Base
from pydantic import BaseModel
import json
from namuna8.property_owner_history_model import PropertyOwnerHistory
from namuna8.owner_history_model import OwnerHistory
from namuna8.namuna8_apis import build_property_response
from namuna8.recordresponses.property_record_response import get_property_record
from Utility.QRcodeGeneration import QRCodeGeneration
import os

router = APIRouter()

# Database model for storing transfer logs
class PropertyTransferLogDB(Base):
    __tablename__ = "property_transfer_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    property_id = Column(Integer, nullable=False)  # Remove foreign key constraint
    date = Column(DateTime, nullable=False)
    entry_no = Column(String(50), nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    new_owners_json = Column(Text, nullable=False)  # Store as JSON string
    old_owners_json = Column(Text, nullable=False)  # Store as JSON string
    doc_note = Column(Text, nullable=True)
    register_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class TransferOwner(BaseModel):
    id: Optional[int] = None
    name: str
    wifeName: Optional[str] = None
    occupantName : Optional[str] = None

class PropertyTransferCreate(BaseModel):
    property_id: int
    date: datetime
    entry_no: str
    transaction_date: Optional[datetime] = None  # Make optional
    new_owners: List[TransferOwner]
    doc_note: Optional[str] = None
    register_note: Optional[str] = None
    district_id: Optional[int] = None
    taluka_id: Optional[int] = None
    gram_panchayat_id: Optional[int] = None

class PropertyTransferLog(BaseModel):
    id: int
    property_id: int
    date: datetime
    entry_no: str
    transaction_date: datetime
    new_owners: List[TransferOwner]
    old_owners: List[TransferOwner]
    doc_note: Optional[str] = None
    register_note: Optional[str] = None
    created_at: datetime

@router.post('/transfer/', response_model=PropertyTransferLog)
def transfer_property(data: PropertyTransferCreate, db: Session = Depends(get_db)):
    # Get property
    prop = db.query(models.Property).filter(models.Property.anuKramank == data.property_id).first()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get old owners for log
    old_owners = [TransferOwner(id=o.id, name=o.name, wifeName=o.wifeName, occupantName=o.occupantName) for o in prop.owners]
    
    # BEFORE TRANSFER: Save previous owners to PropertyOwnerHistory
    # Get or create PropertyOwnerHistory for this property
    property_history = db.query(PropertyOwnerHistory).filter(
        PropertyOwnerHistory.property_id == data.property_id
    ).first()
    
    if not property_history:
        # Create new PropertyOwnerHistory if it doesn't exist
        property_history = PropertyOwnerHistory(
            property_id=data.property_id,
            village_id=prop.village_id,
            gram_panchayat_id=1,
            district_id=1
        )
        db.add(property_history)
        db.commit()
        db.refresh(property_history)
    
    # Add previous owners to history with end date
    for old_owner in prop.owners:
        # Check if this owner already exists in history
        existing_owner_history = db.query(OwnerHistory).filter(
            OwnerHistory.property_owner_history_id == property_history.id,
            OwnerHistory.owner_id == old_owner.id,
            OwnerHistory.transferred_from_this_owner_date.is_(None)  # Current owner (no end date)
        ).first()
        
        # Check property_transfer_logs to determine when owner got the property
        previous_transfer = db.query(PropertyTransferLogDB).filter(
            PropertyTransferLogDB.property_id == data.property_id
        ).first()
        
        if previous_transfer:
            # Use the date from previous transfer record
            owner_got_property_date = previous_transfer.date
        else:
            # No previous transfer, use owner creation date
            owner_got_property_date = old_owner.created_at.date() if old_owner.created_at else data.date
        
        if existing_owner_history:
            # Update existing owner history with end date
            existing_owner_history.transferred_from_this_owner_date = data.date
        else:
            # Create new owner history record for previous owner
            owner_history = OwnerHistory(
                property_owner_history_id=property_history.id,
                entry_number=data.entry_no,
                owner_name=old_owner.name,
                wife_name=old_owner.wifeName,
                owner_id=old_owner.id,
                transferred_to_this_owner_date=owner_got_property_date,
                transferred_from_this_owner_date=data.date  # End date when transferred
            )
            db.add(owner_history)
    
    # Prepare new owners (create if needed)
    new_owners = []
    for owner in data.new_owners:
        if owner.id:
            db_owner = db.query(models.Owner).filter(models.Owner.id == owner.id).first()
            if not db_owner:
                raise HTTPException(status_code=404, detail=f"Owner with id {owner.id} not found")
        else:
            db_owner = models.Owner(
                name=owner.name, 
                wifeName=owner.wifeName, 
                occupantName = 'स्वतः',
                village_id=prop.village_id,
                district_id=data.district_id,
                taluka_id=data.taluka_id,
                gram_panchayat_id=data.gram_panchayat_id
            )
            db.add(db_owner)
            db.commit()
            db.refresh(db_owner)
        new_owners.append(db_owner)
    
    # Update property owners
    prop.owners = new_owners
    db.commit()
    db.refresh(prop)
    
    # AFTER TRANSFER: Add new owners to history with start date
    for new_owner in new_owners:
        new_owner_history = OwnerHistory(
            property_owner_history_id=property_history.id,
            entry_number=data.entry_no,
            owner_name=new_owner.name,
            wife_name=new_owner.wifeName,
            owner_id=new_owner.id,
            transferred_to_this_owner_date=data.date,  # Start date when got the property
            transferred_from_this_owner_date=None  # Current owner (no end date)
        )
        db.add(new_owner_history)
    
    # Delete previous transfer records for this property
    db.query(PropertyTransferLogDB).filter(PropertyTransferLogDB.property_id == data.property_id).delete()
    
    # Save new transfer log to database
    transfer_log_record = PropertyTransferLogDB(
        property_id=data.property_id,
        date=data.date,
        entry_no=data.entry_no,
        transaction_date=data.transaction_date if data.transaction_date else data.date,  # Use date as fallback
        new_owners_json=json.dumps([{"id": o.id, "name": o.name, "wifeName": o.wifeName,"occupantName":o.occupantName} for o in new_owners]),
        old_owners_json=json.dumps([{"id": o.id, "name": o.name, "wifeName": o.wifeName,"occupantName":o.occupantName} for o in old_owners]),
        doc_note=data.doc_note,
        register_note=data.register_note,
        created_at=datetime.utcnow()
    )
    
    db.add(transfer_log_record)
    db.commit()
    db.refresh(transfer_log_record)

    # Update QR code for this property after owners change (use first owner)
    try:
        # Refresh property to ensure relations are current
        db.refresh(prop)
        first_owner = prop.owners[0] if prop.owners else None
        owner_name = first_owner.name if first_owner else ''
        wife_name = first_owner.wifeName if first_owner and getattr(first_owner, 'wifeName', None) else None

        # Pull canonical values from property_record
        rr = get_property_record(
            prop.anuKramank,
            prop.village_id,
            district_id=prop.district_id,
            taluka_id=prop.taluka_id,
            gram_panchayat_id=prop.gram_panchayat_id,
            db=db
        )
        total_area = round(rr.get('totalArea', 0) or 0, 2)
        mobile_number = rr.get('mobileNumber')
        vpanikar_qr = rr.get('vpanikar',0)
        totalTax_qr = rr.get('totaltax',0)
        # electricityTax = record_response.get('electricityTax', 0)
        totalTax = totalTax_qr - vpanikar_qr
        response = build_property_response(prop, db, prop.gram_panchayat_id)
        cons_area = sum(
            (c.get('length') or 0) * (c.get('width') or 0)
            for c in (response.get('constructions', []) or [])
            if not (str(c.get('constructionType', '') or '').strip().startswith('खाली जागा'))
        )
        cons_area = round(cons_area, 2)
        open_area = round(total_area - cons_area, 2)

        # qr_data = {
        #     "अनुक्रमांक": getattr(prop, 'anuKramank', None),
        #     "मालकाचे नाव": owner_name,
        #     # "mobileNumber": mobile_number,
        #     "एकूण क्षेत्रफळ": total_area,
        #     "बांधकाम क्षेत्रफळ": cons_area,
        #     "खुली जागा": open_area,
        #     "एकूण कर": totalTax,
        # }
        # if wife_name:
        #     qr_data["पत्नीचे नाव"] = wife_name

        qr_data = {
            # Marathi labels for QR display
            "मा. धा. ना.": owner_name,
            "Mal. Kr." : getattr(prop, 'malmattaKramank', None),
            "T. A.": total_area,
            "T. T.": totalTax
        }

        qr_dir = os.path.join(
            "uploaded_images", "qrcode",
            str(prop.district_id),
            str(prop.taluka_id),
            str(prop.gram_panchayat_id),
            str(prop.village_id),
            str(prop.anuKramank)
        )
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = os.path.join(qr_dir, "qrcode.png")
        QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
        prop.qrcode = qr_path.replace(os.sep, "/")
        db.commit()
    except Exception:
        # Do not block transfer on QR update
        pass
    
    # Return transfer log (for API response)
    transfer_log = PropertyTransferLog(
        id=transfer_log_record.id,
        property_id=prop.anuKramank,
        date=data.date,
        entry_no=data.entry_no,
        transaction_date=data.transaction_date if data.transaction_date else data.date,  # Use date as fallback
        new_owners=[TransferOwner(id=o.id, name=o.name, wifeName=o.wifeName) for o in new_owners],
        old_owners=old_owners,
        doc_note=data.doc_note,
        register_note=data.register_note,
        created_at=transfer_log_record.created_at
    )
    return transfer_log 

@router.get('/owners/', response_model=List[TransferOwner])
def get_all_owners(db: Session = Depends(get_db)):
    """Get all owners from the database"""
    owners = db.query(models.Owner).all()
    return [TransferOwner(id=owner.id, name=owner.name, wifeName=owner.wifeName) for owner in owners]

@router.get('/owners/{owner_id}', response_model=TransferOwner)
def get_owner_by_id(owner_id: int, db: Session = Depends(get_db)):
    """Get a specific owner by ID"""
    owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return TransferOwner(id=owner.id, name=owner.name, wifeName=owner.wifeName)

@router.get('/owners/search/{search_term}')
def search_owners(search_term: str, db: Session = Depends(get_db)):
    """Search owners by name or Aadhaar number"""
    owners = db.query(models.Owner).filter(
        (models.Owner.name.contains(search_term)) | 
        (models.Owner.aadhaarNumber.contains(search_term))
    ).all()
    return [TransferOwner(id=owner.id, name=owner.name, wifeName=owner.wifeName) for owner in owners] 

@router.get('/owners/bulk/')
def get_owners_bulk(
    page: int = 1, 
    page_size: int = 100, 
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get owners with pagination and search - optimized for bulk data"""
    # Calculate offset
    offset = (page - 1) * page_size
    
    # Build query
    query = db.query(models.Owner)
    
    # Add search filter if provided
    if search:
        query = query.filter(
            (models.Owner.name.contains(search)) | 
            (models.Owner.aadhaarNumber.contains(search))
        )
    
    # Get total count for pagination
    total_count = query.count()
    
    # Get paginated results
    owners = query.offset(offset).limit(page_size).all()
    
    # Format response
    owners_data = [
        {
            "id": owner.id, 
            "name": owner.name, 
            "wifeName": owner.wifeName,
            "aadhaarNumber": owner.aadhaarNumber,
            "mobileNumber": owner.mobileNumber
        } for owner in owners
    ]
    
    return {
        "owners": owners_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": page * page_size < total_count,
            "has_previous": page > 1
        }
    }

@router.get('/property-history/{property_id}')
def get_property_ownership_history(property_id: int, db: Session = Depends(get_db)):
    """Get complete ownership history for a property"""
    # Get property details
    property_details = db.query(models.Property).filter(models.Property.anuKramank == property_id).first()
    if not property_details:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Get property owner history
    property_history = db.query(PropertyOwnerHistory).filter(
        PropertyOwnerHistory.property_id == property_id
    ).first()
    
    if not property_history:
        return {
            "property_id": property_id,
            "property_details": {
                "anuKramank": property_details.anuKramank,
                "streetName": property_details.streetName,
                "totalAreaSqFt": property_details.totalAreaSqFt,
                "village_id": property_details.village_id
            },
            "ownership_history": [],
            "message": "No ownership history found for this property"
        }
    
    # Get all owner history records for this property
    owner_history_records = db.query(OwnerHistory).filter(
        OwnerHistory.property_owner_history_id == property_history.id
    ).order_by(OwnerHistory.transferred_to_this_owner_date).all()
    
    # Format the history
    ownership_history = []
    for record in owner_history_records:
        ownership_history.append({
            "owner_id": record.owner_id,
            "owner_name": record.owner_name,
            "wife_name": record.wife_name,
            "entry_number": record.entry_number,
            "transferred_to_this_owner_date": record.transferred_to_this_owner_date.isoformat() if record.transferred_to_this_owner_date else None,
            "transferred_from_this_owner_date": record.transferred_from_this_owner_date.isoformat() if record.transferred_from_this_owner_date else None,
            "is_current_owner": record.transferred_from_this_owner_date is None,
            "created_at": record.created_at.isoformat() if record.created_at else None
        })
    
    return {
        "property_id": property_id,
        "property_details": {
            "anuKramank": property_details.anuKramank,
            "streetName": property_details.streetName,
            "totalAreaSqFt": property_details.totalAreaSqFt,
            "village_id": property_details.village_id
        },
        "ownership_history": ownership_history,
        "total_owners": len(ownership_history),
        "current_owner": next((owner for owner in ownership_history if owner["is_current_owner"]), None)
    }

@router.get('/property-history-bulk/')
def get_property_history_bulk(
    page: int = 1,
    page_size: int = 50,
    village_id: Optional[int] = None,
    has_history: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """Get property history in bulk with pagination - optimized for large datasets"""
    offset = (page - 1) * page_size
    
    # Build base query for properties
    property_query = db.query(models.Property)
    
    if village_id:
        property_query = property_query.filter(models.Property.village_id == village_id)
    
    # Get total count
    total_count = property_query.count()
    
    # Get paginated properties
    properties = property_query.offset(offset).limit(page_size).all()
    
    # Get all property IDs for batch querying
    property_ids = [prop.anuKramank for prop in properties]
    
    # Batch query property histories
    property_histories = db.query(PropertyOwnerHistory).filter(
        PropertyOwnerHistory.property_id.in_(property_ids)
    ).all()
    
    # Create lookup dictionary
    history_lookup = {ph.property_id: ph.id for ph in property_histories}
    
    # Batch query owner histories for all properties
    if history_lookup:
        owner_histories = db.query(OwnerHistory).filter(
            OwnerHistory.property_owner_history_id.in_(history_lookup.values())
        ).all()
        
        # Group owner histories by property
        owner_history_lookup = {}
        for oh in owner_histories:
            if oh.property_owner_history_id not in owner_history_lookup:
                owner_history_lookup[oh.property_owner_history_id] = []
            owner_history_lookup[oh.property_owner_history_id].append(oh)
    else:
        owner_history_lookup = {}
    
    # Format results
    results = []
    for prop in properties:
        property_history_id = history_lookup.get(prop.anuKramank)
        
        if property_history_id and property_history_id in owner_history_lookup:
            # Has history
            owner_records = owner_history_lookup[property_history_id]
            ownership_history = []
            
            for record in sorted(owner_records, key=lambda x: x.transferred_to_this_owner_date):
                ownership_history.append({
                    "owner_id": record.owner_id,
                    "owner_name": record.owner_name,
                    "wife_name": record.wife_name,
                    "entry_number": record.entry_number,
                    "transferred_to_this_owner_date": record.transferred_to_this_owner_date.isoformat() if record.transferred_to_this_owner_date else None,
                    "transferred_from_this_owner_date": record.transferred_from_this_owner_date.isoformat() if record.transferred_from_this_owner_date else None,
                    "is_current_owner": record.transferred_from_this_owner_date is None
                })
            
            current_owner = next((owner for owner in ownership_history if owner["is_current_owner"]), None)
        else:
            # No history
            ownership_history = []
            current_owner = None
        
        # Apply has_history filter if specified
        if has_history is not None:
            if has_history and not ownership_history:
                continue
            if not has_history and ownership_history:
                continue
        
        results.append({
            "property_id": prop.anuKramank,
            "property_details": {
                "anuKramank": prop.anuKramank,
                "streetName": prop.streetName,
                "totalAreaSqFt": prop.totalAreaSqFt,
                "village_id": prop.village_id
            },
            "ownership_history": ownership_history,
            "total_owners": len(ownership_history),
            "current_owner": current_owner,
            "has_history": len(ownership_history) > 0
        })
    
    return {
        "properties": results,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": page * page_size < total_count,
            "has_previous": page > 1
        }
    }

@router.get('/property-history-by-name/')
def get_property_ownership_history_by_name(property_name: str, db: Session = Depends(get_db)):
    """Get complete ownership history for a property by searching property name"""
    # Search for property by name (assuming streetName or other property fields)
    properties = db.query(models.Property).filter(
        models.Property.streetName.contains(property_name)
    ).all()
    
    if not properties:
        raise HTTPException(status_code=404, detail="No properties found with this name")
    
    results = []
    for prop in properties:
        # Get property owner history
        property_history = db.query(PropertyOwnerHistory).filter(
            PropertyOwnerHistory.property_id == prop.anuKramank
        ).first()
        
        if property_history:
            # Get all owner history records for this property
            owner_history_records = db.query(OwnerHistory).filter(
                OwnerHistory.property_owner_history_id == property_history.id
            ).order_by(OwnerHistory.transferred_to_this_owner_date).all()
            
            # Format the history
            ownership_history = []
            for record in owner_history_records:
                ownership_history.append({
                    "owner_id": record.owner_id,
                    "owner_name": record.owner_name,
                    "wife_name": record.wife_name,
                    "entry_number": record.entry_number,
                    "transferred_to_this_owner_date": record.transferred_to_this_owner_date.isoformat() if record.transferred_to_this_owner_date else None,
                    "transferred_from_this_owner_date": record.transferred_from_this_owner_date.isoformat() if record.transferred_from_this_owner_date else None,
                    "is_current_owner": record.transferred_from_this_owner_date is None,
                    "created_at": record.created_at.isoformat() if record.created_at else None
                })
            
            results.append({
                "property_id": prop.anuKramank,
                "property_details": {
                    "anuKramank": prop.anuKramank,
                    "streetName": prop.streetName,
                    "totalAreaSqFt": prop.totalAreaSqFt,
                    "village_id": prop.village_id
                },
                "ownership_history": ownership_history,
                "total_owners": len(ownership_history),
                "current_owner": next((owner for owner in ownership_history if owner["is_current_owner"]), None)
            })
    
    return {
        "search_term": property_name,
        "properties_found": len(results),
        "results": results
    } 

@router.get('/transfer-logs-bulk/')
def get_transfer_logs_bulk(
    page: int = 1,
    page_size: int = 50,
    property_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get property transfer logs in bulk with pagination"""
    offset = (page - 1) * page_size
    
    # Build query
    query = db.query(PropertyTransferLogDB)
    
    if property_id:
        query = query.filter(PropertyTransferLogDB.property_id == property_id)
    
    if from_date:
        query = query.filter(PropertyTransferLogDB.date >= from_date)
    
    if to_date:
        query = query.filter(PropertyTransferLogDB.date <= to_date)
    
    # Get total count
    total_count = query.count()
    
    # Get paginated results
    transfer_logs = query.order_by(PropertyTransferLogDB.date.desc()).offset(offset).limit(page_size).all()
    
    # Format results
    logs_data = []
    for log in transfer_logs:
        try:
            new_owners = json.loads(log.new_owners_json)
            old_owners = json.loads(log.old_owners_json)
        except json.JSONDecodeError:
            new_owners = []
            old_owners = []
        
        logs_data.append({
            "id": log.id,
            "property_id": log.property_id,
            "date": log.date.isoformat() if log.date else None,
            "entry_no": log.entry_no,
            "transaction_date": log.transaction_date.isoformat() if log.transaction_date else None,
            "new_owners": new_owners,
            "old_owners": old_owners,
            "doc_note": log.doc_note,
            "register_note": log.register_note,
            "created_at": log.created_at.isoformat() if log.created_at else None
        })
    
    return {
        "transfer_logs": logs_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": (total_count + page_size - 1) // page_size,
            "has_next": page * page_size < total_count,
            "has_previous": page > 1
        }
    }

@router.get('/property-history-summary/')
def get_property_history_summary(db: Session = Depends(get_db)):
    """Get summary statistics for property history - optimized for dashboard"""
    # Get total properties
    total_properties = db.query(models.Property).count()
    
    # Get properties with history
    properties_with_history = db.query(PropertyOwnerHistory).count()
    
    # Get total transfers
    total_transfers = db.query(PropertyTransferLogDB).count()
    
    # Get recent transfers (last 30 days)
    from datetime import datetime, timedelta
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_transfers = db.query(PropertyTransferLogDB).filter(
        PropertyTransferLogDB.date >= thirty_days_ago
    ).count()
    
    # Get top villages by transfer count
    village_transfers = db.query(
        models.Property.village_id,
        db.func.count(PropertyTransferLogDB.id).label('transfer_count')
    ).join(
        PropertyTransferLogDB, 
        models.Property.anuKramank == PropertyTransferLogDB.property_id
    ).group_by(
        models.Property.village_id
    ).order_by(
        db.func.count(PropertyTransferLogDB.id).desc()
    ).limit(10).all()
    
    return {
        "summary": {
            "total_properties": total_properties,
            "properties_with_history": properties_with_history,
            "properties_without_history": total_properties - properties_with_history,
            "total_transfers": total_transfers,
            "recent_transfers_30_days": recent_transfers
        },
        "top_villages_by_transfers": [
            {"village_id": vt.village_id, "transfer_count": vt.transfer_count}
            for vt in village_transfers
        ]
    } 

@router.get('/transfer-register-response/')
def get_transfer_register_response(
    village_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get property transfer register response in the same format as ferfar/recordresponses"""
    
    # Get village details (assuming village_id=1 for now, you can modify as needed)
    village_id = village_id or 1
    
    # Get village information (you may need to adjust this based on your village table structure)
    village_info = {
        "village": "गावाचे नाव",  # Replace with actual village name from database
        "gramPanchayat": "ग्रामपंचायत नाव",  # Replace with actual gram panchayat name
        "jilha": "जिल्हा नाव",  # Replace with actual district name
        "taluk": "तालुका नाव"  # Replace with actual taluka name
    }
    
    # Build query for transfer logs
    query = db.query(PropertyTransferLogDB)
    
    if village_id:
        # Join with properties to filter by village
        query = query.join(
            models.Property,
            PropertyTransferLogDB.property_id == models.Property.anuKramank
        ).filter(models.Property.village_id == village_id)
    
    if from_date:
        query = query.filter(PropertyTransferLogDB.date >= from_date)
    
    if to_date:
        query = query.filter(PropertyTransferLogDB.date <= to_date)
    
    # Get all transfer logs
    transfer_logs = query.order_by(PropertyTransferLogDB.date.desc()).all()
    
    # Format the response
    property_transfers = []
    
    for log in transfer_logs:
        try:
            new_owners = json.loads(log.new_owners_json)
            old_owners = json.loads(log.old_owners_json)
        except json.JSONDecodeError:
            new_owners = []
            old_owners = []
        
        # Get property details
        property_details = db.query(models.Property).filter(
            models.Property.anuKramank == log.property_id
        ).first()
        
        if property_details:
            # Format previous owner names
            previous_owner_names = []
            for old_owner in old_owners:
                if old_owner.get('wifeName'):
                    previous_owner_names.append(f"{old_owner.get('name', '')} व {old_owner.get('wifeName', '')}")
                else:
                    previous_owner_names.append(old_owner.get('name', ''))
            
            # Format current owner names
            current_owner_names = []
            for new_owner in new_owners:
                if new_owner.get('wifeName'):
                    current_owner_names.append(f"{new_owner.get('name', '')} व {new_owner.get('wifeName', '')}")
                else:
                    current_owner_names.append(new_owner.get('name', ''))
            
            # Create transfer record
            transfer_record = {
                "entry_number": log.entry_no,
                "village": village_info["village"],
                "transaction_date": log.transaction_date.strftime("%d/%m/%Y") if log.transaction_date else "",
                "roadName": property_details.streetName or "",
                "propertyNumber": str(property_details.anuKramank),
                "propertyDescription": f"क्षेत्र: {property_details.totalAreaSqFt} चौ.फूट" if property_details.totalAreaSqFt else "",
                "previousOwnerName": ", ".join(previous_owner_names),
                "currentOwnerName": ", ".join(current_owner_names),
                "modification_reference_remarks": log.doc_note or "",
                "assessment_register_entry_details": log.register_note or "",
                "remark": f"मालकी हस्तांतरण - नोंद क्रमांक: {log.entry_no}"
            }
            
            property_transfers.append(transfer_record)
    
    # Group by property number (as per your format)
    grouped_transfers = {}
    for transfer in property_transfers:
        property_num = transfer["propertyNumber"]
        if property_num not in grouped_transfers:
            grouped_transfers[property_num] = []
        grouped_transfers[property_num].append(transfer)
    
    # Build final response
    response = {
        "village": village_info["village"],
        "gramPanchayat": village_info["gramPanchayat"],
        "jilha": village_info["jilha"],
        "taluk": village_info["taluk"]
    }
    
    # Add property transfers grouped by property number
    for property_num, transfers in grouped_transfers.items():
        response[property_num] = transfers
    
    return response

@router.get('/recordresponses/')
def get_transfer_record_responses(
    village_id: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get property transfer record responses - same endpoint name as ferfar/recordresponses"""
    
    # Get village information (you may need to adjust this based on your village table structure)
    village_info = {
        "village": "गावाचे नाव",  # Replace with actual village name from database
        "gramPanchayat": "ग्रामपंचायत नाव",  # Replace with actual gram panchayat name
        "jilha": "जिल्हा नाव",  # Replace with actual district name
        "taluk": "तालुका नाव"  # Replace with actual taluka name
    }
    
    # Build query for transfer logs - NO VILLAGE FILTERING
    query = db.query(PropertyTransferLogDB)
    
    if from_date:
        query = query.filter(PropertyTransferLogDB.date >= from_date)
    
    if to_date:
        query = query.filter(PropertyTransferLogDB.date <= to_date)
    
    # Get all transfer logs
    transfer_logs = query.order_by(PropertyTransferLogDB.date.desc()).all()
    
    # Format the response
    property_transfers = []
    
    for log in transfer_logs:
        try:
            new_owners = json.loads(log.new_owners_json)
            old_owners = json.loads(log.old_owners_json)
        except json.JSONDecodeError:
            new_owners = []
            old_owners = []
        
        # Get property details
        property_details = db.query(models.Property).filter(
            models.Property.anuKramank == log.property_id
        ).first()
        
        if property_details:
            # Format previous owner names
            previous_owner_names = []
            for old_owner in old_owners:
                if old_owner.get('wifeName'):
                    previous_owner_names.append(f"{old_owner.get('name', '')} व {old_owner.get('wifeName', '')}")
                else:
                    previous_owner_names.append(old_owner.get('name', ''))
            
            # Format current owner names
            current_owner_names = []
            for new_owner in new_owners:
                if new_owner.get('wifeName'):
                    current_owner_names.append(f"{new_owner.get('name', '')} व {new_owner.get('wifeName', '')}")
                else:
                    current_owner_names.append(new_owner.get('name', ''))
            
            # Create transfer record
            transfer_record = {
                "entry_number": log.entry_no,
                "village": village_info["village"],
                "transaction_date": log.transaction_date.strftime("%d/%m/%Y") if log.transaction_date else "",
                "roadName": property_details.streetName or "",
                "propertyNumber": str(property_details.anuKramank),
                "propertyDescription": f"क्षेत्र: {property_details.totalAreaSqFt} चौ.फूट" if property_details.totalAreaSqFt else "",
                "previousOwnerName": ", ".join(previous_owner_names),
                "currentOwnerName": ", ".join(current_owner_names),
                "modification_reference_remarks": log.doc_note or "",
                "assessment_register_entry_details": log.register_note or "",
                "remark": f"मालकी हस्तांतरण - नोंद क्रमांक: {log.entry_no}"
            }
            
            property_transfers.append(transfer_record)
    
    # Group by property number (as per your format)
    grouped_transfers = {}
    for transfer in property_transfers:
        property_num = transfer["propertyNumber"]
        if property_num not in grouped_transfers:
            grouped_transfers[property_num] = []
        grouped_transfers[property_num].append(transfer)
    
    # Build final response
    response = {
        "village": village_info["village"],
        "gramPanchayat": village_info["gramPanchayat"],
        "jilha": village_info["jilha"],
        "taluk": village_info["taluk"]
    }
    
    # Add property transfers grouped by property number
    for property_num, transfers in grouped_transfers.items():
        response[property_num] = transfers
    
    return response

@router.get('/transfer-register-response-by-village/{village_id}')
def get_transfer_register_response_by_village(
    village_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get property transfer register response for a specific village"""
    return get_transfer_register_response(village_id, from_date, to_date, db) 