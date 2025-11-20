from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from namuna8 import namuna8_model as models, namuna8_schemas as schemas
from location_management import models as location_models
from database import get_db
from namuna8.mastertab.transfer_apis import PropertyTransferLogDB
import json

router = APIRouter()

@router.get('/recordresponses')
def get_ferfar_record_responses(
    gram_panchayat_id: int,
    taluka_id: int,
    district_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """फेरफाराचे रजिस्टर - Get property transfer record responses for all properties using existing data"""
    
    # Resolve and collect human-readable location names for response header
    # village_name = ""
    gp_name = ""
    taluka_name = ""
    district_name = ""

    # No village_id filter; header village will remain blank

    gp_row = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == gram_panchayat_id).first()
    if gp_row:
        gp_name = gp_row.name or ""

    taluka_row = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
    if taluka_row:
        taluka_name = taluka_row.name or ""

    district_row = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if district_row:
        district_name = district_row.name or ""

    village_info = {
        # "village": village_name,
        "gramPanchayat": gp_name,
        "jilha": district_name,
        "taluk": taluka_name,
    }
    
    # Build query for transfer logs joined with properties to allow location-based filtering
    query = (
        db.query(PropertyTransferLogDB)
        .join(models.Property, PropertyTransferLogDB.property_id == models.Property.anuKramank)
    )
    
    if from_date:
        query = query.filter(PropertyTransferLogDB.date >= from_date)
    
    if to_date:
        query = query.filter(PropertyTransferLogDB.date <= to_date)
    
    # Apply required location filters (no village filter)
    query = query.filter(models.Property.gram_panchayat_id == gram_panchayat_id)
    query = query.filter(models.Property.taluka_id == taluka_id)
    query = query.filter(models.Property.district_id == district_id)

    # Get all transfer logs after filters
    transfer_logs = query.order_by(PropertyTransferLogDB.date.desc()).all()

    # If no records found for the given filters, return an explicit no data message
    if not transfer_logs:
        return {"message": "no data"}
    
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
            # Get village information separately
            village_data = db.query(models.Village).filter(
                models.Village.id == property_details.village_id
            ).first()
            
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
            
            # Create transfer record using existing data
            transfer_record = {
                "entry_number": log.entry_no,
                "village": village_data.name if village_data else "",
                "transaction_date": log.transaction_date.strftime("%d/%m/%Y") if log.transaction_date else "",
                "roadName": property_details.streetName or property_details.citySurveyOrGatNumber or "",
                "propertyNumber": str(property_details.anuKramank),
                "propertyDescription": f"क्षेत्र: {property_details.totalAreaSqFt} चौ.फूट" if property_details.totalAreaSqFt else "",
                "previousOwnerName": ", ".join(previous_owner_names),
                "previousOccupantName" : old_owners[0].get("occupantName") if old_owners and old_owners[0].get("occupantName") else "स्वतः",
                "currentOccupantName"  : new_owners[0].get("occupantName") if new_owners and new_owners[0].get("occupantName") else "स्वतः",
                "currentOwnerName": ", ".join(current_owner_names),
                "modification_reference_remarks": log.doc_note or "",  # Using existing doc_note
                "assessment_register_entry_details": log.register_note or ""  # Using existing register_note
            }
            
            property_transfers.append(transfer_record)
    
    # Top-level village not required in response

    # Group by property number (as per your format)
    grouped_transfers = {}
    for transfer in property_transfers:
        property_num = transfer["propertyNumber"]
        if property_num not in grouped_transfers:
            grouped_transfers[property_num] = []
        grouped_transfers[property_num].append(transfer)
    
    # Build final response
    response = {
        "gramPanchayat": village_info["gramPanchayat"],
        "jilha": village_info["jilha"],
        "taluk": village_info["taluk"]
    }
    
    # Add property transfers grouped by property number
    for property_num, transfers in grouped_transfers.items():
        response[property_num] = transfers
    
    return response 