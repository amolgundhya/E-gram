from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .namuna7_model import Namuna7
from .namuna7_schemas import Namuna7Create, Namuna7Read, Namuna7Update, Namuna7PrintResponse
from typing import List
from database import get_db
from uuid import UUID
from datetime import datetime, timedelta
from ..namuna8_model import Owner, Village, Property
from location_management import models as location_models

router = APIRouter(prefix="/namuna7", tags=["Namuna7"])

@router.post("/", response_model=Namuna7Read)
def create_namuna7(item: Namuna7Create, db: Session = Depends(get_db)):
    db_item = Namuna7(**item.dict())    
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[Namuna7Read])
def get_all_namuna7(
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy if any of the three fields are provided
    if district_id is not None:
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
        if not district:
            raise HTTPException(status_code=404, detail="District not found")
    
    if taluka_id is not None:
        if district_id is None:
            raise HTTPException(status_code=400, detail="District ID is required when Taluka ID is provided")
        taluka = db.query(location_models.Taluka).filter(
            location_models.Taluka.id == taluka_id,
            location_models.Taluka.district_id == district_id
        ).first()
        if not taluka:
            raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    if gram_panchayat_id is not None:
        if taluka_id is None:
            raise HTTPException(status_code=400, detail="Taluka ID is required when Gram Panchayat ID is provided")
        gram_panchayat = db.query(location_models.GramPanchayat).filter(
            location_models.GramPanchayat.id == gram_panchayat_id,
            location_models.GramPanchayat.taluka_id == taluka_id
        ).first()
        if not gram_panchayat:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    query = db.query(Namuna7)
    if district_id:
        query = query.filter(Namuna7.district_id == district_id)
    if taluka_id:
        query = query.filter(Namuna7.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(Namuna7.gram_panchayat_id == gram_panchayat_id)
    return query.all()

@router.get("/getall_receipts")
def get_namuna7_custom_list(
    startdate: str = Query(..., description="Start date in YYYY-MM-DD format"),
    enddate: str = Query(..., description="End date in YYYY-MM-DD format"),
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    from datetime import datetime, timedelta
    try:
        start_dt = datetime.strptime(startdate, "%Y-%m-%d")
        end_dt = datetime.strptime(enddate, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    # Validate location hierarchy if any of the three fields are provided
    if district_id is not None:
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
        if not district:
            raise HTTPException(status_code=404, detail="District not found")
    
    if taluka_id is not None:
        if district_id is None:
            raise HTTPException(status_code=400, detail="District ID is required when Taluka ID is provided")
        taluka = db.query(location_models.Taluka).filter(
            location_models.Taluka.id == taluka_id,
            location_models.Taluka.district_id == district_id
        ).first()
        if not taluka:
            raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    if gram_panchayat_id is not None:
        if taluka_id is None:
            raise HTTPException(status_code=400, detail="Taluka ID is required when Gram Panchayat ID is provided")
        gram_panchayat = db.query(location_models.GramPanchayat).filter(
            location_models.GramPanchayat.id == gram_panchayat_id,
            location_models.GramPanchayat.taluka_id == taluka_id
        ).first()
        if not gram_panchayat:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    query = db.query(Namuna7).filter(Namuna7.createdAt >= start_dt, Namuna7.createdAt < end_dt)
    if district_id:
        query = query.filter(Namuna7.district_id == district_id)
    if taluka_id:
        query = query.filter(Namuna7.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(Namuna7.gram_panchayat_id == gram_panchayat_id)
    items = query.all()
    result = []
    today = datetime.now().strftime("%d/%m/%Y")
    for idx, item in enumerate(items, start=1):
        owner = db.query(Owner).filter(Owner.id == item.userId).first()
        ownername = owner.name if owner else ""
        occupant = getattr(owner, "occupantName", "") or ""
        village = db.query(Village).filter(Village.id == item.villageId).first()
        grampanchayat = village.name if village else ""
        result.append({
            "grampanchayat": grampanchayat,
            "srNo": idx,
            "receiptDate": item.createdAt.strftime("%Y-%m-%d") if getattr(item, "createdAt", None) else None,
            "receiptNumber": item.receiptNumber,
            "receiptBookNumber": item.receiptBookNumber,
            "village": grampanchayat,
            "ownername": ownername,
            "occupant":occupant,
            "reason": item.reason or "",
            "receivedMoney": item.receivedMoney,
            "currentDate": today
        })
    return result

@router.get("/{item_id}", response_model=Namuna7Read)
def get_namuna7(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Namuna7).filter(Namuna7.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Namuna7 not found")
    return item

@router.put("/{item_id}", response_model=Namuna7Read)
def update_namuna7(item_id: int, update: Namuna7Update, db: Session = Depends(get_db)):
    item = db.query(Namuna7).filter(Namuna7.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Namuna7 not found")
    for key, value in update.dict(exclude_unset=True).items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/{item_id}")
def delete_namuna7(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Namuna7).filter(Namuna7.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Namuna7 not found")
    db.delete(item)
    db.commit()
    return {"detail": "Deleted successfully"}

@router.get("/by-date/")
def get_namuna7_by_date(
    from_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    to_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    village_id: int = Query(None, description="Village ID to filter by"),
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    try:
        from_dt = datetime.strptime(from_date, "%Y-%m-%d")
        to_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    query = (
        db.query(Namuna7, Owner)
        .join(Owner, Namuna7.userId == Owner.id)
        .filter(Namuna7.createdAt >= from_dt, Namuna7.createdAt < to_dt)
    )
    if village_id is not None:
        query = query.filter(Namuna7.villageId == village_id)
    if district_id:
        query = query.filter(Namuna7.district_id == district_id)
    if taluka_id:
        query = query.filter(Namuna7.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(Namuna7.gram_panchayat_id == gram_panchayat_id)
    results = query.order_by(Namuna7.createdAt, Namuna7.receiptNumber).all()
    response = [
        {
            **{k: getattr(n7, k) for k in n7.__table__.columns.keys()},
            "date": n7.createdAt.strftime("%Y-%m-%d"),
            "ownerName": owner.name
        }
        for n7, owner in results
    ]
    return response

@router.get("/prints/get/{item_id}", response_model=Namuna7PrintResponse)
def get_namuna7_print(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Namuna7).filter(Namuna7.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Namuna7 not found")
    owner = db.query(Owner).filter(Owner.id == item.userId).first()
    occupant = getattr(owner, "occupantName", "") or ""
    village = db.query(Village).filter(Village.id == item.villageId).first()
    grampanchayat = village.name if village else ""
    ownername = owner.name if owner else ""
    currentDate = datetime.now().strftime("%d/%m/%Y")
    return Namuna7PrintResponse(
        grampanchayat=grampanchayat,
        receiptNumber=int(item.__dict__["receiptNumber"]),
        receiptBookNumber=int(item.__dict__["receiptBookNumber"]),
        village=grampanchayat,
        ownername=ownername,
        occupant=occupant,
        reason=str(item.__dict__["reason"]) if item.__dict__["reason"] is not None else "",
        receivedMoney=int(item.__dict__["receivedMoney"]),
        currentDate=currentDate
    ) 

@router.get("/prints/by_location")
def get_namuna7_prints_by_location(
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy if any of the three fields are provided
    if district_id is not None:
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
        if not district:
            raise HTTPException(status_code=404, detail="District not found")
    
    if taluka_id is not None:
        if district_id is None:
            raise HTTPException(status_code=400, detail="District ID is required when Taluka ID is provided")
        taluka = db.query(location_models.Taluka).filter(
            location_models.Taluka.id == taluka_id,
            location_models.Taluka.district_id == district_id
        ).first()
        if not taluka:
            raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    if gram_panchayat_id is not None:
        if taluka_id is None:
            raise HTTPException(status_code=400, detail="Taluka ID is required when Gram Panchayat ID is provided")
        gram_panchayat = db.query(location_models.GramPanchayat).filter(
            location_models.GramPanchayat.id == gram_panchayat_id,
            location_models.GramPanchayat.taluka_id == taluka_id
        ).first()
        if not gram_panchayat:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    # Build query based on location filters
    query = db.query(Namuna7)
    if district_id:
        query = query.filter(Namuna7.district_id == district_id)
    if taluka_id:
        query = query.filter(Namuna7.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(Namuna7.gram_panchayat_id == gram_panchayat_id)
    
    items = query.all()
    
    # Get location name for display
    location_name = ""
    if gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == gram_panchayat_id).first()
        location_name = gram_panchayat.name if gram_panchayat else ""
    elif taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
        location_name = taluka.name if taluka else ""
    elif district_id:
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
        location_name = district.name if district else ""
    
    currentDate = datetime.now().strftime("%d/%m/%Y")
    
    results = []
    for item in items:
        # Get owner information
        owner = db.query(Owner).filter(Owner.id == item.userId).first()
        ownername = owner.name if owner else "Unknown Owner"
        
        # Get village information
        village = db.query(Village).filter(Village.id == item.villageId).first()
        village_name = village.name if village else "Unknown Village"
        
        # Add record to results
        results.append({
            "receiptNumber": int(item.receiptNumber),
            "receiptBookNumber": int(item.receiptBookNumber),
            "ownername": ownername,
            "village": village_name,
            "reason": str(item.reason) if item.reason is not None else "",
            "receivedMoney": int(item.receivedMoney)
        })
    
    return {
        "grampanchayat": location_name,
        "village": location_name,
        "currentDate": currentDate,
        "records": results,
        "debug_info": {
            "district_id": district_id,
            "taluka_id": taluka_id,
            "gram_panchayat_id": gram_panchayat_id,
            "total_records_found": len(items),
            "location_name": location_name
        }
    }

@router.get("/debug/villages")
def debug_villages_and_records(db: Session = Depends(get_db)):
    """Debug endpoint to check all villages and their namuna7 records"""
    villages = db.query(Village).all()
    result = []
    
    for village in villages:
        namuna7_count = db.query(Namuna7).filter(Namuna7.villageId == village.id).count()
        result.append({
            "village_id": village.id,
            "village_name": village.name,
            "namuna7_records_count": namuna7_count
        })
    
    return {
        "total_villages": len(villages),
        "villages": result
    }

@router.get("/debug/locations")
def debug_locations_and_records(db: Session = Depends(get_db)):
    """Debug endpoint to check all locations and their namuna7 records"""
    # Get all districts
    districts = db.query(location_models.District).all()
    district_result = []
    
    for district in districts:
        namuna7_count = db.query(Namuna7).filter(Namuna7.district_id == district.id).count()
        district_result.append({
            "district_id": district.id,
            "district_name": district.name,
            "namuna7_records_count": namuna7_count
        })
    
    # Get all talukas
    talukas = db.query(location_models.Taluka).all()
    taluka_result = []
    
    for taluka in talukas:
        namuna7_count = db.query(Namuna7).filter(Namuna7.taluka_id == taluka.id).count()
        taluka_result.append({
            "taluka_id": taluka.id,
            "taluka_name": taluka.name,
            "district_id": taluka.district_id,
            "namuna7_records_count": namuna7_count
        })
    
    # Get all gram panchayats
    gram_panchayats = db.query(location_models.GramPanchayat).all()
    gram_panchayat_result = []
    
    for gram_panchayat in gram_panchayats:
        namuna7_count = db.query(Namuna7).filter(Namuna7.gram_panchayat_id == gram_panchayat.id).count()
        gram_panchayat_result.append({
            "gram_panchayat_id": gram_panchayat.id,
            "gram_panchayat_name": gram_panchayat.name,
            "taluka_id": gram_panchayat.taluka_id,
            "namuna7_records_count": namuna7_count
        })
    
    return {
        "total_districts": len(districts),
        "total_talukas": len(talukas),
        "total_gram_panchayats": len(gram_panchayats),
        "districts": district_result,
        "talukas": taluka_result,
        "gram_panchayats": gram_panchayat_result
    } 
    