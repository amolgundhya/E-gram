from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import database
from namuna9 import namuna9_model, namuna9_schemas
from namuna9.namuna9_schemas import Namuna9PropertyDataCreate, Namuna9PropertyDataUpdate, Namuna9PropertyDataRead, Namuna9BulkPropertyDataUpdate, Namuna9Collect, Namuna9ReceiptCreate, Namuna9ReceiptRead
from typing import List , Optional

router = APIRouter(
    prefix="/namuna9",
    tags=["namuna9-property-data"]
)

# New API endpoints for property data management
@router.post("/property-data", response_model=Namuna9PropertyDataRead, status_code=status.HTTP_201_CREATED)
def create_property_data(property_data: Namuna9PropertyDataCreate, db: Session = Depends(database.get_db)):
    """Create property data for a specific Namuna9 record"""
    # Check if Namuna9 record exists
    namuna9_record = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == property_data.namuna9_id).first()
    if not namuna9_record:
        raise HTTPException(status_code=404, detail="Namuna9 record not found")
    
    # Check if property data already exists
    existing = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == property_data.namuna9_id,
        namuna9_model.Namuna9PropertyData.property_id == property_data.property_id
    ).first()
    
    if existing:
        # Upsert behavior: update existing record instead of failing on unique constraint
        for field, value in property_data.dict(exclude_unset=True).items():
            if field in ("namuna9_id", "property_id"):
                continue
            setattr(existing, field, value)
        # Recompute ekun and total consistently
        existing.ekunGhar = (existing.shaktiGhar or 0) + (existing.chaluGhar or 0)
        existing.ekunDiva = (existing.shaktiDiva or 0) + (existing.chaluDiva or 0)
        existing.ekunAarogyaKar = (existing.shaktiAarogyaKar or 0) + (existing.chaluAarogyaKar or 0)
        existing.ekunSapanikar = (existing.shaktiSapanikar or 0) + (existing.chaluSapanikar or 0)
        existing.ekunVpanikar = (existing.shaktiVpanikar or 0) + (existing.chaluVpanikar or 0)
        existing.ekunCleaningTax = (existing.shaktiCleaningTax or 0) + (existing.chaluCleaningTax or 0)
        existing.total = (existing.ekunGhar or 0) + (existing.ekunDiva or 0) + (existing.ekunAarogyaKar or 0) + (existing.ekunSapanikar or 0) + (existing.ekunVpanikar or 0) + (existing.ekunCleaningTax or 0) + (existing.noticeFee or 0) + (existing.warrantFee or 0) + (existing.dand or 0)
        db.commit()
        db.refresh(existing)
        return existing

    db_property_data = namuna9_model.Namuna9PropertyData(**property_data.dict())
    # Initialize ekun and total on create too
    db_property_data.ekunGhar = (db_property_data.shaktiGhar or 0) + (db_property_data.chaluGhar or 0)
    db_property_data.ekunDiva = (db_property_data.shaktiDiva or 0) + (db_property_data.chaluDiva or 0)
    db_property_data.ekunAarogyaKar = (db_property_data.shaktiAarogyaKar or 0) + (db_property_data.chaluAarogyaKar or 0)
    db_property_data.ekunSapanikar = (db_property_data.shaktiSapanikar or 0) + (db_property_data.chaluSapanikar or 0)
    db_property_data.ekunVpanikar = (db_property_data.shaktiVpanikar or 0) + (db_property_data.chaluVpanikar or 0)
    db_property_data.ekunCleaningTax = (db_property_data.shaktiCleaningTax or 0) + (db_property_data.chaluCleaningTax or 0)
    db_property_data.total = (db_property_data.ekunGhar or 0) + (db_property_data.ekunDiva or 0) + (db_property_data.ekunAarogyaKar or 0) + (db_property_data.ekunSapanikar or 0) + (db_property_data.ekunVpanikar or 0) + (db_property_data.ekunCleaningTax or 0) + (db_property_data.noticeFee or 0) + (db_property_data.warrantFee or 0) + (db_property_data.dand or 0)
    db.add(db_property_data)
    db.commit()
    db.refresh(db_property_data)
    return db_property_data

@router.put("/property-data/{property_data_id}", response_model=Namuna9PropertyDataRead)
def update_property_data(property_data_id: int, property_data: Namuna9PropertyDataUpdate, db: Session = Depends(database.get_db)):
    """Update property data"""
    db_property_data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.id == property_data_id
    ).first()
    
    if not db_property_data:
        raise HTTPException(status_code=404, detail="Property data not found")
    
    # Update only provided fields
    for field, value in property_data.dict(exclude_unset=True).items():
        setattr(db_property_data, field, value)
    
    db.commit()
    db.refresh(db_property_data)
    return db_property_data

@router.get("/property-data/{namuna9_id}", response_model=List[Namuna9PropertyDataRead])
def get_property_data(namuna9_id: int, db: Session = Depends(database.get_db)):
    """Get all property data for a specific Namuna9 record"""
    return db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == namuna9_id
    ).all()

@router.get("/property-data/by-receipt/{receipt_id}", response_model=Namuna9PropertyDataRead)
def get_property_data_by_receipt(receipt_id: int, db: Session = Depends(database.get_db)):
    """Fetch property data using a receipt id (maps to namuna9_id + property_id)."""
    rec = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.id == receipt_id
    ).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == rec.namuna9_id,
        namuna9_model.Namuna9PropertyData.property_id == rec.property_id
    ).first()
    if not data:
        raise HTTPException(status_code=404, detail="Property data not found for receipt")
    return data

@router.post("/property-data/bulk-update")
def bulk_update_property_data(bulk_data: Namuna9BulkPropertyDataUpdate, db: Session = Depends(database.get_db)):
    """Bulk update property data for multiple properties"""
    # Check if Namuna9 record exists
    namuna9_record = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == bulk_data.namuna9_id).first()
    if not namuna9_record:
        raise HTTPException(status_code=404, detail="Namuna9 record not found")
    
    # Merge multiple updates per property_id to avoid duplicate inserts in one transaction
    merged_by_property: dict[int, dict] = {}
    for item in bulk_data.property_data:
        pid = item.property_id
        if pid not in merged_by_property:
            merged_by_property[pid] = {}
        for field, value in item.dict(exclude_unset=True).items():
            if field == 'property_id':
                continue
            merged_by_property[pid][field] = value

    updated_count = 0
    created_count = 0

    for property_id, updates in merged_by_property.items():
        existing = db.query(namuna9_model.Namuna9PropertyData).filter(
            namuna9_model.Namuna9PropertyData.namuna9_id == bulk_data.namuna9_id,
            namuna9_model.Namuna9PropertyData.property_id == property_id
        ).first()

        if existing:
            for field, value in updates.items():
                setattr(existing, field, value)
            # Recompute ekun and total after updates
            existing.ekunGhar = (existing.shaktiGhar or 0) + (existing.chaluGhar or 0)
            existing.ekunDiva = (existing.shaktiDiva or 0) + (existing.chaluDiva or 0)
            existing.ekunAarogyaKar = (existing.shaktiAarogyaKar or 0) + (existing.chaluAarogyaKar or 0)
            existing.ekunSapanikar = (existing.shaktiSapanikar or 0) + (existing.chaluSapanikar or 0)
            existing.ekunVpanikar = (existing.shaktiVpanikar or 0) + (existing.chaluVpanikar or 0)
            existing.ekunCleaningTax = (existing.shaktiCleaningTax or 0) + (existing.chaluCleaningTax or 0)
            existing.total = (existing.ekunGhar or 0) + (existing.ekunDiva or 0) + (existing.ekunAarogyaKar or 0) + (existing.ekunSapanikar or 0) + (existing.ekunVpanikar or 0) + (existing.ekunCleaningTax or 0) + (existing.noticeFee or 0) + (existing.warrantFee or 0) + (existing.dand or 0)
            updated_count += 1
        else:
            new_data = namuna9_model.Namuna9PropertyData(
                namuna9_id=bulk_data.namuna9_id,
                property_id=property_id,
                **updates
            )
            # Initialize ekun and total on create
            new_data.ekunGhar = (new_data.shaktiGhar or 0) + (new_data.chaluGhar or 0)
            new_data.ekunDiva = (new_data.shaktiDiva or 0) + (new_data.chaluDiva or 0)
            new_data.ekunAarogyaKar = (new_data.shaktiAarogyaKar or 0) + (new_data.chaluAarogyaKar or 0)
            new_data.ekunSapanikar = (new_data.shaktiSapanikar or 0) + (new_data.chaluSapanikar or 0)
            new_data.ekunVpanikar = (new_data.shaktiVpanikar or 0) + (new_data.chaluVpanikar or 0)
            new_data.ekunCleaningTax = (new_data.shaktiCleaningTax or 0) + (new_data.chaluCleaningTax or 0)
            new_data.total = (new_data.ekunGhar or 0) + (new_data.ekunDiva or 0) + (new_data.ekunAarogyaKar or 0) + (new_data.ekunSapanikar or 0) + (new_data.ekunVpanikar or 0) + (new_data.ekunCleaningTax or 0) + (new_data.noticeFee or 0) + (new_data.warrantFee or 0) + (new_data.dand or 0)
            db.add(new_data)
            created_count += 1
    
    db.commit()
    
    return {
        "message": "Bulk update completed",
        "updated_count": updated_count,
        "created_count": created_count,
        "total_processed": len(merged_by_property)
    }

@router.post("/property-data/collect")
def collect_property_amounts(payload: Namuna9Collect, db: Session = Depends(database.get_db)):
    """Apply collections to arrears and store vasuli amounts."""
    # Ensure Namuna9 exists
    rec = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == payload.namuna9_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Namuna9 record not found")

    data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == payload.namuna9_id,
        namuna9_model.Namuna9PropertyData.property_id == payload.property_id
    ).first()
    if not data:
        # Create if not exists
        data = namuna9_model.Namuna9PropertyData(
            namuna9_id=payload.namuna9_id,
            property_id=payload.property_id
        )
        db.add(data)
        db.flush()

    # Apply vasuli and reduce shakti fields (not below zero)
    def apply(field_shakti: str, field_vasuli: str, amount: float):
        current_shakti = getattr(data, field_shakti) or 0.0
        current_vasuli = getattr(data, field_vasuli) or 0.0
        take = max(min(amount, current_shakti), 0.0)
        setattr(data, field_shakti, current_shakti - take)
        setattr(data, field_vasuli, current_vasuli + take)

    apply('shaktiGhar', 'vasuliGhar', payload.vasuliGhar)
    # Reduce chalu (current) from chaluGhar rather than shakti
    def apply_chalu(field_chalu: str, field_vasuli_chalu: str, amount: float):
        current_chalu = getattr(data, field_chalu) or 0.0
        current_vasuli_chalu = getattr(data, field_vasuli_chalu) or 0.0
        take = max(min(amount, current_chalu), 0.0)
        setattr(data, field_chalu, current_chalu - take)
        setattr(data, field_vasuli_chalu, current_vasuli_chalu + take)

    apply_chalu('chaluGhar', 'vasuliChaluGhar', payload.vasuliChaluGhar)
    apply('shaktiDiva', 'vasuliDiva', payload.vasuliDiva)
    apply_chalu('chaluDiva', 'vasuliChaluDiva', payload.vasuliChaluDiva)
    apply('shaktiAarogyaKar', 'vasuliAarogyaKar', payload.vasuliAarogyaKar)
    apply_chalu('chaluAarogyaKar', 'vasuliChaluAarogyaKar', payload.vasuliChaluAarogyaKar)
    apply('shaktiSapanikar', 'vasuliSapanikar', payload.vasuliSapanikar)
    apply_chalu('chaluSapanikar', 'vasuliChaluSapanikar', payload.vasuliChaluSapanikar)
    apply('shaktiVpanikar', 'vasuliVpanikar', payload.vasuliVpanikar)
    apply_chalu('chaluVpanikar', 'vasuliChaluVpanikar', payload.vasuliChaluVpanikar)
    apply('shaktiCleaningTax', 'vasuliCleaningTax', payload.vasuliCleaningTax)
    apply_chalu('chaluCleaningTax', 'vasuliChaluCleaningTax', payload.vasuliChaluCleaningTax)
    # dand and fees
    apply('dand', 'vasuliDand', payload.vasuliDand)
    apply('noticeFee', 'vasuliNoticeFee', payload.vasuliNoticeFee)
    apply('warrantFee', 'vasuliWarrantFee', payload.vasuliWarrantFee)

    # Recompute ekun and total
    data.ekunGhar = (data.shaktiGhar or 0) + (data.chaluGhar or 0)
    data.ekunDiva = (data.shaktiDiva or 0) + (data.chaluDiva or 0)
    data.ekunAarogyaKar = (data.shaktiAarogyaKar or 0) + (data.chaluAarogyaKar or 0)
    data.ekunSapanikar = (data.shaktiSapanikar or 0) + (data.chaluSapanikar or 0)
    data.ekunVpanikar = (data.shaktiVpanikar or 0) + (data.chaluVpanikar or 0)
    data.ekunCleaningTax = (data.shaktiCleaningTax or 0) + (data.chaluCleaningTax or 0)
    data.total = (data.ekunGhar or 0) + (data.ekunDiva or 0) + (data.ekunAarogyaKar or 0) + (data.ekunSapanikar or 0) + (data.ekunVpanikar or 0) + (data.ekunCleaningTax or 0) + (data.noticeFee or 0) + (data.warrantFee or 0) + (data.dand or 0)

    db.commit()
    db.refresh(data)
    return {"message": "Collection applied", "data": data.id}

@router.get("/receipt/next-number")
def get_next_receipt_number(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    last = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id
    ).order_by(namuna9_model.Namuna9Receipt.pavti_kramank.desc()).first()
    return {"nextNumber": (last.pavti_kramank + 1) if last else 1}

@router.post("/receipt", response_model=Namuna9ReceiptRead)
def create_receipt(payload: Namuna9ReceiptCreate, db: Session = Depends(database.get_db)):
    rec = namuna9_model.Namuna9Receipt(
        namuna9_id=payload.namuna9_id,
        property_id=payload.property_id,
        gram_panchayat_id=payload.gram_panchayat_id,
        pa_book_kramank=payload.pa_book_kramank,
        pavti_kramank=payload.pavti_kramank,
        vasuliGhar=payload.vasuliGhar,
        vasuliChaluGhar=payload.vasuliChaluGhar,
        vasuliDiva=payload.vasuliDiva,
        vasuliChaluDiva=payload.vasuliChaluDiva,
        vasuliAarogyaKar=payload.vasuliAarogyaKar,
        vasuliChaluAarogyaKar=payload.vasuliChaluAarogyaKar,
        vasuliSapanikar=payload.vasuliSapanikar,
        vasuliChaluSapanikar=payload.vasuliChaluSapanikar,
        vasuliVpanikar=payload.vasuliVpanikar,
        vasuliChaluVpanikar=payload.vasuliChaluVpanikar,
        vasuliCleaningTax=payload.vasuliCleaningTax,
        vasuliChaluCleaningTax=payload.vasuliChaluCleaningTax,
        vasuliDand=payload.vasuliDand,
        vasuliNoticeFee=payload.vasuliNoticeFee,
        vasuliWarrantFee=payload.vasuliWarrantFee,
        total=payload.total,
        payment_mode=payload.payment_mode,
        utr_tr_id=payload.utr_tr_id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec

@router.get("/receipt/list", response_model=list[Namuna9ReceiptRead])
def list_receipts(
    gram_panchayat_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    receipt_id: Optional[int] = None,
    show_all: bool = False,
    db: Session = Depends(database.get_db)
):
    q = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id
    )
    if receipt_id:
        q = q.filter(namuna9_model.Namuna9Receipt.id == receipt_id)
    if not show_all:
        from datetime import datetime
        if from_date:
            q = q.filter(namuna9_model.Namuna9Receipt.pavti_date >= from_date)
        if to_date:
            q = q.filter(namuna9_model.Namuna9Receipt.pavti_date <= to_date)
    return q.order_by(namuna9_model.Namuna9Receipt.pavti_date.desc()).all()

@router.put("/receipt/{receipt_id}", response_model=Namuna9ReceiptRead)
def update_receipt(receipt_id: int, payload: Namuna9ReceiptCreate, db: Session = Depends(database.get_db)):
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    for f, v in payload.dict(exclude_unset=True).items():
        setattr(rec, f, v)
    db.commit()
    db.refresh(rec)
    return rec

@router.delete("/receipt/{receipt_id}")
def delete_receipt(receipt_id: int, db: Session = Depends(database.get_db)):
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    db.delete(rec)
    db.commit()
    return {"message": "Receipt deleted"}

@router.delete("/property-data/{property_data_id}")
def delete_property_data(property_data_id: int, db: Session = Depends(database.get_db)):
    """Delete property data"""
    db_property_data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.id == property_data_id
    ).first()
    
    if not db_property_data:
        raise HTTPException(status_code=404, detail="Property data not found")
    
    db.delete(db_property_data)
    db.commit()
    
    return {"message": "Property data deleted successfully"}
