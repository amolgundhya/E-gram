from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from .outward_entries_model import OutwardEntry

router = APIRouter(prefix="/outward-entries", tags=["Outward Entries"])

# Get all outward entries
@router.get("/")
def get_all_outward_entries(db: Session = Depends(get_db)):
    try:
        entries = db.query(OutwardEntry).order_by(OutwardEntry.created_at.desc()).all()
        return [entry.to_dict() for entry in entries]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching outward entries: {str(e)}")

# Get outward entries by date range (filtered by created_at)
@router.get("/date-range/")
def get_outward_entries_by_date_range(
    from_date: str,
    to_date: str,
    db: Session = Depends(get_db)
):
    try:
        # Convert date strings to datetime objects (date only, no time)
        # from_date should start at 00:00:00 of that day
        # to_date should end at 23:59:59 of that day
        from_dt = datetime.strptime(from_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt = datetime.strptime(to_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
        
        entries = db.query(OutwardEntry).filter(
            OutwardEntry.created_at >= from_dt,
            OutwardEntry.created_at <= to_dt
        ).all()

        # Sort numerically by srNo so that values like "1", "2", "10" are in true numeric order
        results = [entry.to_dict() for entry in entries]
        results = sorted(results, key=lambda r: int(r["srNo"]))  # assumes srNo is numeric-like
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching outward entries by date range: {str(e)}")

# Get outward entry by srNo
@router.get("/{sr_no}")
def get_outward_entry_by_srno(sr_no: str, db: Session = Depends(get_db)):
    try:
        entry = db.query(OutwardEntry).filter(OutwardEntry.srNo == sr_no).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Outward entry not found")
        return entry.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching outward entry: {str(e)}")

# Create new outward entry
@router.post("/")
def create_outward_entry(entry_data: dict, db: Session = Depends(get_db)):
    try:
        # Check if jaKramank already exists
        existing_jakramank = db.query(OutwardEntry).filter(OutwardEntry.jaKramank == entry_data.get('jaKramank')).first()
        if existing_jakramank:
            raise HTTPException(status_code=400, detail="जा.क्र. (Outward No.) already exists! Please use a different outward number.")
        
        # Convert timeNDate string to datetime
        if 'timeNDate' in entry_data and isinstance(entry_data['timeNDate'], str):
            entry_data['timeNDate'] = datetime.fromisoformat(entry_data['timeNDate'].replace('Z', '+00:00'))
        
        # Set default values if not provided
        entry_data.setdefault('village_id', 1)
        entry_data.setdefault('gram_panchayat_id', 1)
        entry_data.setdefault('district_id', 1)
        
        new_entry = OutwardEntry(**entry_data)
        db.add(new_entry)
        db.commit()
        db.refresh(new_entry)
        
        return new_entry.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating outward entry: {str(e)}")

# Update outward entry
@router.put("/{sr_no}")
def update_outward_entry(sr_no: str, entry_data: dict, db: Session = Depends(get_db)):
    try:
        entry = db.query(OutwardEntry).filter(OutwardEntry.srNo == sr_no).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Outward entry not found")
        
        # Convert timeNDate string to datetime if provided
        if 'timeNDate' in entry_data and isinstance(entry_data['timeNDate'], str):
            entry_data['timeNDate'] = datetime.fromisoformat(entry_data['timeNDate'].replace('Z', '+00:00'))
        
        # Update fields
        for key, value in entry_data.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        entry.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(entry)
        
        return entry.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating outward entry: {str(e)}")

# Delete outward entry
@router.delete("/{sr_no}")
def delete_outward_entry(sr_no: str, db: Session = Depends(get_db)):
    try:
        entry = db.query(OutwardEntry).filter(OutwardEntry.srNo == sr_no).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Outward entry not found")
        
        db.delete(entry)
        db.commit()
        
        return {"message": "Outward entry deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting outward entry: {str(e)}")

# Get existing serial numbers
@router.get("/existing/srnos")
def get_existing_srnos(db: Session = Depends(get_db)):
    try:
        srnos = db.query(OutwardEntry.srNo).all()
        return {"existing_srnos": [srno[0] for srno in srnos]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching existing serial numbers: {str(e)}")

# Get existing outward numbers
@router.get("/existing/jakramanks")
def get_existing_jakramanks(db: Session = Depends(get_db)):
    try:
        jakramanks = db.query(OutwardEntry.jaKramank).all()
        return {"existing_jakramanks": [jakramank[0] for jakramank in jakramanks]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching existing outward numbers: {str(e)}")

# Get next available serial number
@router.get("/next/srno")
def get_next_available_srno(db: Session = Depends(get_db)):
    try:
        # Get all existing srNos and find the next available number
        existing_srnos = db.query(OutwardEntry.srNo).all()
        existing_numbers = [int(srno[0]) for srno in existing_srnos if srno[0].isdigit()]
        
        if not existing_numbers:
            next_srno = "1"
        else:
            next_srno = str(max(existing_numbers) + 1)
        
        return {"next_srno": next_srno}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating next serial number: {str(e)}")

# Get next available outward number
@router.get("/next/jakramank")
def get_next_available_jakramank(db: Session = Depends(get_db)):
    try:
        # Get all existing jaKramanks and find the next available number
        existing_jakramanks = db.query(OutwardEntry.jaKramank).all()
        existing_numbers = [int(jakramank[0]) for jakramank in existing_jakramanks if jakramank[0].isdigit()]
        
        if not existing_numbers:
            next_jakramank = "1"
        else:
            next_jakramank = str(max(existing_numbers) + 1)
        
        return {"next_jakramank": next_jakramank}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating next outward number: {str(e)}") 