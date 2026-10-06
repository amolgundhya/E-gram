from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import database
from namuna9 import namuna9_model, namuna9_schemas
from namuna9.namuna9_schemas import Namuna9PropertyDataCreate, Namuna9PropertyDataUpdate, Namuna9PropertyDataRead, Namuna9BulkPropertyDataUpdate, Namuna9Collect, Namuna9ReceiptCreate, Namuna9ReceiptRead
from typing import List , Optional
from datetime import datetime, timedelta
from sqlalchemy import func
from location_management import models as location_models
from namuna8 import namuna8_model
from namuna8.recordresponses.property_record_response import compute_display_sr_no
import os

backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

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
        # Canonical calculation for chaluGhar/ekunGhar
        prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == property_data.property_id).first()
        constructions = db.query(namuna8_model.Construction).filter(namuna8_model.Construction.property_id == property_data.property_id).all()
        from namuna9.tax_calculations import calculate_total_house_tax
        totalHouseTax = calculate_total_house_tax(prop, constructions, db)
        existing.chaluGhar = totalHouseTax
        existing.ekunGhar = totalHouseTax + (existing.dand or 0) + (existing.shaktiGhar or 0)
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
    # Canonical calculation for chaluGhar/ekunGhar
    prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == property_data.property_id).first()
    constructions = db.query(namuna8_model.Construction).filter(namuna8_model.Construction.property_id == property_data.property_id).all()
    from namuna9.tax_calculations import calculate_total_house_tax
    totalHouseTax = calculate_total_house_tax(prop, constructions, db)
    db_property_data.chaluGhar = totalHouseTax
    db_property_data.ekunGhar = totalHouseTax + (db_property_data.dand or 0) + (db_property_data.shaktiGhar or 0)
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

    # Recompute ekun fields and total so partial edits (e.g., only dand) reflect correctly
    db_property_data.ekunGhar = (db_property_data.shaktiGhar or 0) + (db_property_data.chaluGhar or 0) + (db_property_data.dand or 0)
    db_property_data.ekunDiva = (db_property_data.shaktiDiva or 0) + (db_property_data.chaluDiva or 0)
    db_property_data.ekunAarogyaKar = (db_property_data.shaktiAarogyaKar or 0) + (db_property_data.chaluAarogyaKar or 0)
    db_property_data.ekunSapanikar = (db_property_data.shaktiSapanikar or 0) + (db_property_data.chaluSapanikar or 0)
    db_property_data.ekunVpanikar = (db_property_data.shaktiVpanikar or 0) + (db_property_data.chaluVpanikar or 0)
    db_property_data.ekunCleaningTax = (db_property_data.shaktiCleaningTax or 0) + (db_property_data.chaluCleaningTax or 0)
    db_property_data.total = (
        (db_property_data.ekunGhar or 0) +
        (db_property_data.ekunDiva or 0) +
        (db_property_data.ekunAarogyaKar or 0) +
        (db_property_data.ekunSapanikar or 0) +
        (db_property_data.ekunVpanikar or 0) +
        (db_property_data.ekunCleaningTax or 0) +
        (db_property_data.noticeFee or 0) +
        (db_property_data.warrantFee or 0) +
        (db_property_data.dand or 0)
    )

    db.commit()
    db.refresh(db_property_data)
    return db_property_data

@router.get("/property-data/{namuna9_id}", response_model=List[Namuna9PropertyDataRead])
def get_property_data(namuna9_id: int, db: Session = Depends(database.get_db)):
    """Get all property data for a specific Namuna9 record"""
    rows = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == namuna9_id
    ).all()
    # Stable numeric ordering by property_id (and id as tiebreaker)
    try:
        rows = sorted(rows, key=lambda r: (int(r.property_id or 0), int(r.id or 0)))
    except Exception:
        rows = sorted(rows, key=lambda r: (r.property_id or 0, r.id or 0))
    return rows

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
    print(f"Bulk update received: namuna9_id={bulk_data.namuna9_id}, property_data_count={len(bulk_data.property_data)}")
    # Check if Namuna9 record exists
    namuna9_record = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == bulk_data.namuna9_id).first()
    if not namuna9_record:
        print(f"Namuna9 record not found for id: {bulk_data.namuna9_id}")
        raise HTTPException(status_code=404, detail="Namuna9 record not found")
    print(f"Found Namuna9 record: villageId={namuna9_record.villageId}, yearslap={namuna9_record.yearslap}")
    
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
        print(f"Processing property_id: {property_id}, updates: {updates}")
        existing = db.query(namuna9_model.Namuna9PropertyData).filter(
            namuna9_model.Namuna9PropertyData.namuna9_id == bulk_data.namuna9_id,
            namuna9_model.Namuna9PropertyData.property_id == property_id
        ).first()

        if existing:
            print(f"Updating existing record for property_id: {property_id}")
            for field, value in updates.items():
                setattr(existing, field, value)
            # Recompute ekun and total after updates
            # Include dand in ekunGhar (house total)
            existing.ekunGhar = (existing.shaktiGhar or 0) + (existing.chaluGhar or 0) + (existing.dand or 0)
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
            # Include dand in ekunGhar (house total)
            new_data.ekunGhar = (new_data.shaktiGhar or 0) + (new_data.chaluGhar or 0) + (new_data.dand or 0)
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
    # Debug logging
    print(f"[DEBUG] Collect request: namuna9_id={payload.namuna9_id}, property_id={payload.property_id}")
    print(f"[DEBUG] Payload: {payload.dict()}")
    
    # Validate input data
    if not payload.namuna9_id or payload.namuna9_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid namuna9_id")
    if not payload.property_id or payload.property_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid property_id")
    
    # Ensure Namuna9 exists
    rec = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == payload.namuna9_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Namuna9 record not found")

    # Validate that property exists in the namuna9 record
    if not rec.property_ids or payload.property_id not in rec.property_ids:
        raise HTTPException(status_code=422, detail="Property not found in this Namuna9 record")

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

    # Apply vasuli and reduce shakti fields (allow negative values)
    def apply(field_shakti: str, field_vasuli: str, amount: float):
        current_shakti = getattr(data, field_shakti) or 0.0
        current_vasuli = getattr(data, field_vasuli) or 0.0
        # Allow subtraction even if it results in negative values
        setattr(data, field_shakti, current_shakti - amount)
        setattr(data, field_vasuli, current_vasuli + amount)

    apply('shaktiGhar', 'vasuliGhar', payload.vasuliGhar)
    # Reduce chalu (current) from chaluGhar rather than shakti
    def apply_chalu(field_chalu: str, field_vasuli_chalu: str, amount: float):
        current_chalu = getattr(data, field_chalu) or 0.0
        current_vasuli_chalu = getattr(data, field_vasuli_chalu) or 0.0
        # Allow subtraction even if it results in negative values
        setattr(data, field_chalu, current_chalu - amount)
        setattr(data, field_vasuli_chalu, current_vasuli_chalu + amount)

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

    # Clamp negative values to zero before recalculating ekun/total
    clamp_fields = [
        'shaktiGhar', 'chaluGhar',
        'shaktiDiva', 'chaluDiva',
        'shaktiAarogyaKar', 'chaluAarogyaKar',
        'shaktiSapanikar', 'chaluSapanikar',
        'shaktiVpanikar', 'chaluVpanikar',
        'shaktiCleaningTax', 'chaluCleaningTax',
        'dand', 'noticeFee', 'warrantFee'
    ]
    for field in clamp_fields:
        value = getattr(data, field)
        if value is not None and value < 0:
            setattr(data, field, 0)

    # Recompute ekun and total
    # Include dand in ekunGhar recompute
    data.ekunGhar = (max(data.shaktiGhar,0) or 0) + (max(0,data.chaluGhar) or 0) + (max(0,data.dand) or 0)
    data.ekunDiva = (max(data.shaktiDiva,0) or 0) + (max(0,data.chaluDiva) or 0)
    data.ekunAarogyaKar = (max(0,data.shaktiAarogyaKar) or 0) + (max(0,data.chaluAarogyaKar) or 0)
    data.ekunSapanikar = (max(data.shaktiSapanikar,0) or 0) + (max(0,data.chaluSapanikar) or 0)
    data.ekunVpanikar = (max(0,data.shaktiVpanikar) or 0) + (max(0,data.chaluVpanikar) or 0)
    data.ekunCleaningTax = (max(0,data.shaktiCleaningTax) or 0) + (max(0,data.chaluCleaningTax) or 0)
    data.total = (max(0,data.ekunGhar) or 0) + (max(0,data.ekunDiva) or 0) + (max(0,data.ekunAarogyaKar) or 0) + (max(0,data.ekunSapanikar) or 0) + (max(0,data.ekunVpanikar) or 0) + (max(0,data.ekunCleaningTax) or 0) + (max(0,data.noticeFee) or 0) + (max(0,data.warrantFee) or 0) + (max(0,data.dand) or 0)

    db.commit()
    db.refresh(data)
    return {"message": "Collection applied", "data": data.id}

@router.get("/receipt/next-number")
def get_next_receipt_number(gram_panchayat_id: int, village_id: int = None, db: Session = Depends(database.get_db)):
    # Get receipts for this gram panchayat
    q = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id
    )
    
    # If village_id provided, filter by properties in that village
    if village_id is not None:
        prop_ids_subq = db.query(namuna8_model.Property.id).filter(namuna8_model.Property.village_id == village_id).subquery()
        q = q.filter(namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq))
        print(f"Getting next receipt number for gram_panchayat_id={gram_panchayat_id}, village_id={village_id}")
    else:
        print(f"Getting next receipt number for gram_panchayat_id={gram_panchayat_id} (all villages)")
    
    last = q.order_by(namuna9_model.Namuna9Receipt.pavti_kramank.desc()).first()
    next_number = (last.pavti_kramank + 1) if last else 1
    print(f"Last receipt number: {last.pavti_kramank if last else 'None'}, Next number: {next_number}")
    return {"nextNumber": next_number}

# Maps each भरणा (collected) field on a receipt to the थकित/चालू/दंड/fee
# field on that property's Namuna9PropertyData ledger row it pays down.
VASULI_TO_PROPERTY_FIELD = {
    'vasuliGhar': 'shaktiGhar',
    'vasuliChaluGhar': 'chaluGhar',
    'vasuliDiva': 'shaktiDiva',
    'vasuliChaluDiva': 'chaluDiva',
    'vasuliAarogyaKar': 'shaktiAarogyaKar',
    'vasuliChaluAarogyaKar': 'chaluAarogyaKar',
    'vasuliSapanikar': 'shaktiSapanikar',
    'vasuliChaluSapanikar': 'chaluSapanikar',
    'vasuliVpanikar': 'shaktiVpanikar',
    'vasuliChaluVpanikar': 'chaluVpanikar',
    'vasuliCleaningTax': 'shaktiCleaningTax',
    'vasuliChaluCleaningTax': 'chaluCleaningTax',
    'vasuliDand': 'dand',
    'vasuliNoticeFee': 'noticeFee',
    'vasuliWarrantFee': 'warrantFee',
}


def _adjust_property_data_for_receipt(db: Session, namuna9_id: int, property_id: int, vasuli_deltas: dict):
    """Adjust a property's थकित/चालू/दंड/fee ledger row by the given per-field
    deltas (positive = restore/add back, negative = subtract as collected).
    Used to keep receipts (भरणा) and the tax ledger in sync on
    create/edit/delete, without touching एकूण - that's always recomputed
    live from shakti+chalu+dand elsewhere, never stored. Silently no-ops if
    the property has no ledger row yet (nothing to adjust against) - this
    only affects receipts created from now on, not historical ones.
    """
    row = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == namuna9_id,
        namuna9_model.Namuna9PropertyData.property_id == property_id
    ).first()
    if not row:
        return
    changed = False
    for vasuli_field, prop_field in VASULI_TO_PROPERTY_FIELD.items():
        delta = vasuli_deltas.get(vasuli_field) or 0
        if delta:
            current = getattr(row, prop_field, 0) or 0
            setattr(row, prop_field, round(max(current + delta, 0), 2))
            changed = True
    if changed:
        db.commit()


@router.post("/receipt", response_model=Namuna9ReceiptRead)
def create_receipt(payload: Namuna9ReceiptCreate, db: Session = Depends(database.get_db)):
    # Debug logging
    print(f"[DEBUG] Receipt creation request: namuna9_id={payload.namuna9_id}, property_id={payload.property_id}")
    print(f"[DEBUG] Receipt payload: {payload.dict()}")
    
    # Validate input data
    if not payload.namuna9_id or payload.namuna9_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid namuna9_id")
    if not payload.property_id or payload.property_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid property_id")
    if not payload.gram_panchayat_id or payload.gram_panchayat_id <= 0:
        raise HTTPException(status_code=422, detail="Invalid gram_panchayat_id")
    if not payload.pavti_kramank or payload.pavti_kramank <= 0:
        raise HTTPException(status_code=422, detail="Invalid pavti_kramank")
    
    # Normalize pavti_date to datetime if provided as ISO string
    pavti_dt = None
    if payload.pavti_date:
        try:
            pavti_dt = datetime.fromisoformat(str(payload.pavti_date).replace('Z',''))
        except Exception:
            pavti_dt = None
    # Lookup owner name and malmatta kramank from property
    prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == payload.property_id).first()
    owner_name = None
    if prop:
        # Prefer first owner name if many-to-many exists
        try:
            if prop.owners and len(prop.owners) > 0 and getattr(prop.owners[0], 'name', None):
                owner_name = prop.owners[0].name
        except Exception:
            owner_name = None

    # डबल-क्लिक / झटपट पुन्हा-सबमिटने तीच पावती दोनदा सेव्ह होऊ नये (safety net) - फक्त
    # नवीन पावतीसाठी, edit/delete ला लागू होत नाही. याच property + namuna9_id साठी,
    # अगदी त्याच रकमा आणि त्याच तारखेची पावती गेल्या 10 सेकंदांत आधीच सेव्ह झाली असेल,
    # तर नवीन रो न बनवता तीच परत करतो. कुठलाही DB constraint नाही आणि जुन्या पावत्यांना
    # (उदा. आधीच सेव्ह झालेल्या डुप्लिकेट रो) हात लावत नाही - फक्त वाचून तुलना करतो.
    try:
        recent_cutoff = datetime.utcnow() - timedelta(seconds=10)
        recent_candidates = db.query(namuna9_model.Namuna9Receipt).filter(
            namuna9_model.Namuna9Receipt.property_id == payload.property_id,
            namuna9_model.Namuna9Receipt.namuna9_id == payload.namuna9_id,
            namuna9_model.Namuna9Receipt.is_deleted == False,
        ).order_by(namuna9_model.Namuna9Receipt.id.desc()).limit(5).all()
        for cand in recent_candidates:
            cand_created = cand.createdAt
            if cand_created is None:
                continue
            cand_created_naive = cand_created.replace(tzinfo=None) if cand_created.tzinfo else cand_created
            if cand_created_naive < recent_cutoff:
                break  # id नुसार उतरत्या क्रमाने आहेत - पुढच्या आणखी जुन्या असतील
            same_amounts = (
                (cand.vasuliGhar or 0) == (payload.vasuliGhar or 0) and
                (cand.vasuliChaluGhar or 0) == (payload.vasuliChaluGhar or 0) and
                (cand.vasuliDiva or 0) == (payload.vasuliDiva or 0) and
                (cand.vasuliChaluDiva or 0) == (payload.vasuliChaluDiva or 0) and
                (cand.vasuliAarogyaKar or 0) == (payload.vasuliAarogyaKar or 0) and
                (cand.vasuliChaluAarogyaKar or 0) == (payload.vasuliChaluAarogyaKar or 0) and
                (cand.vasuliSapanikar or 0) == (payload.vasuliSapanikar or 0) and
                (cand.vasuliChaluSapanikar or 0) == (payload.vasuliChaluSapanikar or 0) and
                (cand.vasuliVpanikar or 0) == (payload.vasuliVpanikar or 0) and
                (cand.vasuliChaluVpanikar or 0) == (payload.vasuliChaluVpanikar or 0) and
                (cand.vasuliCleaningTax or 0) == (payload.vasuliCleaningTax or 0) and
                (cand.vasuliChaluCleaningTax or 0) == (payload.vasuliChaluCleaningTax or 0) and
                (cand.vasuliDand or 0) == (payload.vasuliDand or 0) and
                (cand.vasuliNoticeFee or 0) == (payload.vasuliNoticeFee or 0) and
                (cand.vasuliWarrantFee or 0) == (payload.vasuliWarrantFee or 0) and
                round(cand.total or 0, 2) == round(payload.total or 0, 2)
            )
            same_date = (
                cand.pavti_date == pavti_dt or
                (cand.pavti_date and pavti_dt and cand.pavti_date.date() == pavti_dt.date())
            )
            if same_amounts and same_date:
                return cand
    except Exception:
        # ही तपासणी स्वतःच फेल झाली तरी सामान्य पावती सेव्ह होण्यात अडथळा येऊ नये.
        pass

    rec = namuna9_model.Namuna9Receipt(
        namuna9_id=payload.namuna9_id,
        property_id=payload.property_id,
        gram_panchayat_id=payload.gram_panchayat_id,
        owner_name=payload.owner_name or owner_name,
        malmatta_kramank=payload.malmatta_kramank or (prop.malmattaKramank if prop else None),
        pa_book_kramank=payload.pa_book_kramank,
        pavti_kramank=payload.pavti_kramank,
        pavti_date=pavti_dt,
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

    # Note: unlike update/delete below, creating a receipt does NOT also
    # adjust the थकित/चालू ledger here - the only caller of this endpoint
    # (the "new भरणा entry" save flow in Namuna9.tsx) already does that
    # itself via a separate POST to /property-data/collect right before
    # this call. Adjusting here too would double-subtract the same amount.

    return rec

# @router.get("/receipt/list", response_model=list[Namuna9ReceiptRead])
# def list_receipts(
#     district_id: int,
#     taluka_id: int,
#     village_id: int,
#     gram_panchayat_id: int,
#     from_date: Optional[str] = None,
#     to_date: Optional[str] = None,
#     receipt_id: Optional[int] = None,
#     show_all: bool = False,
#     db: Session = Depends(database.get_db)
# ):
#     # Validate hierarchy
#     district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
#     if not district:
#         raise HTTPException(status_code=404, detail="District not found")
#     taluka = db.query(location_models.Taluka).filter(
#         location_models.Taluka.id == taluka_id,
#         location_models.Taluka.district_id == district_id
#     ).first()
#     if not taluka:
#         raise HTTPException(status_code=400, detail="Taluka does not belong to district")
#     gram_panchayat = db.query(location_models.GramPanchayat).filter(
#         location_models.GramPanchayat.id == gram_panchayat_id,
#         location_models.GramPanchayat.taluka_id == taluka_id
#     ).first()
#     if not gram_panchayat:
#         raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to taluka")
#     village = db.query(namuna8_model.Village).filter(
#         namuna8_model.Village.id == village_id,
#         namuna8_model.Village.gram_panchayat_id == gram_panchayat_id
#     ).first()
#     if not village:
#         raise HTTPException(status_code=400, detail="Village does not belong to gram panchayat")

#     q = db.query(namuna9_model.Namuna9Receipt).filter(
#         namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id
#     )
#     # Further restrict to receipts for properties in this village
#     prop_ids_subq = db.query(namuna8_model.Property.id).filter(namuna8_model.Property.village_id == village_id).subquery()
#     q = q.filter(namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq))
#     if receipt_id:
#         print(f"[DEBUG] Searching for receipt_id: {receipt_id} (type: {type(receipt_id)})")
#         # Search by both id and pavti_kramank to handle both cases
#         q = q.filter(
#             (namuna9_model.Namuna9Receipt.id == receipt_id) | 
#             (namuna9_model.Namuna9Receipt.pavti_kramank == receipt_id)
#         )
#         print(f"[DEBUG] Query after receipt_id filter: {q}")
#     if not show_all:
#         def _parse_dt(s: Optional[str]):
#             if not s:
#                 return None
#             try:
#                 return datetime.fromisoformat(s)
#             except Exception:
#                 try:
#                     return datetime.strptime(s, '%Y-%m-%d')
#                 except Exception:
#                     return None
#         fd = _parse_dt(from_date)
#         td = _parse_dt(to_date)
#         date_expr = func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt)
#         if fd:
#             q = q.filter(date_expr >= fd)
#         if td:
#             # include the whole day if only date provided
#             td_end = td
#             if td.time().hour == 0 and td.time().minute == 0 and td.time().second == 0:
#                 td_end = td + timedelta(days=1)
#             q = q.filter(date_expr < td_end)
#     results = q.order_by(func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt).desc()).all()
#     # Ensure snapshot fields are filled for legacy rows
#     for rec in results:
#         if (not rec.owner_name) or (not rec.malmatta_kramank):
#             prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
#             if prop:
#                 if not rec.malmatta_kramank:
#                     rec.malmatta_kramank = prop.malmattaKramank
#                 if not rec.owner_name:
#                     try:
#                         if prop.owners and len(prop.owners) > 0 and getattr(prop.owners[0], 'name', None):
#                             rec.owner_name = prop.owners[0].name
#                     except Exception:
#                         pass
#     db.commit()
#     print(f"[DEBUG] Found {len(results)} receipts")
#     for i, rec in enumerate(results):
#         print(f"[DEBUG] Receipt {i}: id={rec.id}, pavti_kramank={rec.pavti_kramank}, property_id={rec.property_id}")
#     return results
@router.get("/receipt/list", response_model=list[Namuna9ReceiptRead])
def list_receipts(
    district_id: int,
    taluka_id: int,
    village_id: int,
    gram_panchayat_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    receipt_id: Optional[int] = None,
    show_all: bool = False,
    db: Session = Depends(database.get_db)
):
    # Validate hierarchy
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")

    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to district")

    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to taluka")

    village = db.query(namuna8_model.Village).filter(
        namuna8_model.Village.id == village_id,
        namuna8_model.Village.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not village:
        raise HTTPException(status_code=400, detail="Village does not belong to gram panchayat")

    # ---------------- FILTER START ----------------

    if show_all:
        # सर्व दाखवा spans every गाव/मोहल्ला (area) under this gram panchayat,
        # not just the currently selected village - so payments collected
        # across different areas can be shown grouped by area.
        base_q = db.query(namuna9_model.Namuna9Receipt).filter(
            namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id,
            namuna9_model.Namuna9Receipt.is_deleted == False
        )
        q = base_q
    else:
        # Otherwise stay scoped to the selected village, as before.
        prop_ids_subq = db.query(namuna8_model.Property.id).filter(
            namuna8_model.Property.village_id == village_id
        ).subquery()

        base_q = db.query(namuna9_model.Namuna9Receipt).filter(
            namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id,
            namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq),
            namuna9_model.Namuna9Receipt.is_deleted == False
        )
        q = base_q

        # Filter by receipt id if provided
        if receipt_id:
            q = q.filter(
                (namuna9_model.Namuna9Receipt.id == receipt_id) |
                (namuna9_model.Namuna9Receipt.pavti_kramank == receipt_id)
            )

        # Date filtering
        def _parse_dt(s: Optional[str]):
            if not s:
                return None
            try:
                return datetime.fromisoformat(s)
            except:
                try:
                    return datetime.strptime(s, '%Y-%m-%d')
                except:
                    return None

        fd = _parse_dt(from_date)
        td = _parse_dt(to_date)

        date_expr = func.coalesce(
            namuna9_model.Namuna9Receipt.pavti_date,
            namuna9_model.Namuna9Receipt.createdAt
        )

        if fd:
            q = q.filter(date_expr >= fd)
        if td:
            td_end = td + timedelta(days=1)
            q = q.filter(date_expr < td_end)

    # Always sort receipts by receipt number (pavti_kramank) numerically
    results = q.all()
    try:
        results = sorted(results, key=lambda r: int(r.pavti_kramank or 0))
    except Exception:
        results = sorted(results, key=lambda r: r.pavti_kramank or 0)

    # ---------------- FILTER END ----------------

    # Fill snapshot missing, and attach the property's गाव/मोहल्ला (area) name so
    # a सर्व दाखवा search spanning multiple areas can be grouped by area on
    # the frontend.
    for rec in results:
        prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
        if prop:
            if not rec.malmatta_kramank:
                rec.malmatta_kramank = prop.malmattaKramank
            if not rec.owner_name:
                try:
                    if prop.owners and len(prop.owners) > 0 and getattr(prop.owners[0], 'name', None):
                        rec.owner_name = prop.owners[0].name
                except Exception:
                    pass
            village = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
            rec.village = getattr(village, 'name', None) if village else None
        else:
            rec.village = None

        # शिल्लक थकबाकी - थकित (shakti*) + चालू (chalu*) दोन्ही मिळून, तक्ता/प्रिंट प्रमाणेच
        ledger_row = db.query(namuna9_model.Namuna9PropertyData).filter(
            namuna9_model.Namuna9PropertyData.namuna9_id == rec.namuna9_id,
            namuna9_model.Namuna9PropertyData.property_id == rec.property_id
        ).first()
        if ledger_row:
            # दंड घरकर रोसोबतच धरतो - प्रिंट टेम्पलेट्समध्ये दंड नेहमी घरकर रोमध्येच दाखवला जातो.
            rec.remainingGhar = round((ledger_row.shaktiGhar or 0) + (ledger_row.chaluGhar or 0) + (ledger_row.dand or 0), 2)
            rec.remainingDiva = round((ledger_row.shaktiDiva or 0) + (ledger_row.chaluDiva or 0), 2)
            rec.remainingAarogyaKar = round((ledger_row.shaktiAarogyaKar or 0) + (ledger_row.chaluAarogyaKar or 0), 2)
            rec.remainingSapanikar = round((ledger_row.shaktiSapanikar or 0) + (ledger_row.chaluSapanikar or 0), 2)
            rec.remainingVpanikar = round((ledger_row.shaktiVpanikar or 0) + (ledger_row.chaluVpanikar or 0), 2)
            rec.remainingCleaningTax = round((ledger_row.shaktiCleaningTax or 0) + (ledger_row.chaluCleaningTax or 0), 2)
            rec.remainingTotal = round(
                rec.remainingGhar + rec.remainingDiva + rec.remainingAarogyaKar +
                rec.remainingSapanikar + rec.remainingVpanikar + rec.remainingCleaningTax, 2
            )

    db.commit()

    print(f"[DEBUG] Show All Mode: {show_all}")
    print(f"[DEBUG] Total receipts returned: {len(results)}")

    return results


@router.post("/append-village-data")
def append_village_data_to_namuna9(
    namuna9_id: int,
    village_id: int,
    district_id: int,
    taluka_id: int,
    gram_panchayat_id: int,
    db: Session = Depends(database.get_db)
):
    """Append all properties from a village to an existing Namuna 9 record"""
    
    # Validate Namuna9 record exists
    namuna9_record = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == namuna9_id).first()
    if not namuna9_record:
        raise HTTPException(status_code=404, detail="Namuna9 record not found")
    
    # Validate location hierarchy
    village = db.query(namuna8_model.Village).filter(
        namuna8_model.Village.id == village_id,
        namuna8_model.Village.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    
    # Get all properties from the village
    properties = db.query(namuna8_model.Property).filter(
        namuna8_model.Property.village_id == village_id
    ).all()
    
    if not properties:
        return {"message": "No properties found in village", "added_count": 0, "skipped_count": 0}
    
    # Get current property IDs in Namuna9
    current_property_ids = set(namuna9_record.property_ids or [])
    
    # Find properties not already in Namuna9
    new_properties = [prop for prop in properties if prop.id not in current_property_ids]
    
    if not new_properties:
        return {"message": "All properties already exist in Namuna9", "added_count": 0, "skipped_count": len(properties)}
    
    # Add new property IDs to Namuna9
    updated_property_ids = list(current_property_ids) + [prop.id for prop in new_properties]
    namuna9_record.property_ids = updated_property_ids
    
    # NOTE: Do NOT create blank Namuna9PropertyData rows here.
    # Blank rows with 0/None values cause the table-data API to trust saved zeros
    # and skip calculated taxes, which results in empty calculations in the UI.
    # Instead, let table-data compute taxes on the fly until user edits/saves,
    # at which point rows will be created/updated via bulk-update APIs.
    db.commit()
    
    added_count = len(new_properties)
    skipped_count = len(properties) - added_count
    return {
        "message": "Successfully appended properties to Namuna9",
        "added_count": added_count,
        "skipped_count": skipped_count,
        "total_properties_in_village": len(properties),
        "total_properties_in_namuna9": len(updated_property_ids)
    }

@router.get("/receipt/{receipt_id}", response_model=Namuna9ReceiptRead)
def get_receipt(receipt_id: int, db: Session = Depends(database.get_db)):
    """Fetch a single receipt by id with all fields."""
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if (not rec.owner_name) or (not rec.malmatta_kramank):
        prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
        if prop:
            if not rec.malmatta_kramank:
                rec.malmatta_kramank = prop.malmattaKramank
            if not rec.owner_name:
                try:
                    if prop.owners and len(prop.owners) > 0 and getattr(prop.owners[0], 'name', None):
                        rec.owner_name = prop.owners[0].name
                except Exception:
                    pass
        db.commit()
    # Enrich with grampanchayat, village and occupant
    prop2 = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
    result = Namuna9ReceiptRead.from_orm(rec)
    # Format pavti_date as YYYY-MM-DD string
    try:
        if result.pavti_date:
            # pydantic may give datetime or string; normalize to date-only string
            from datetime import datetime
            if isinstance(result.pavti_date, datetime):
                result.pavti_date = result.pavti_date.strftime('%Y-%m-%d')
            else:
                result.pavti_date = str(result.pavti_date)[:10]
    except Exception:
        pass
    if prop2:
        result.anuKramank = compute_display_sr_no(db, prop2.village_id, prop2.anuKramank)
        result.exServicemanTip = bool(getattr(prop2, 'exServiceman', False))
        # village
        v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop2.village_id).first()
        result.village = getattr(v, 'name', None)
        # district
        d = db.query(location_models.District).filter(location_models.District.id == v.district_id).first()
        result.district = getattr(d, 'name', None)
        # taluka
        t = db.query(location_models.Taluka).filter(location_models.Taluka.id == v.taluka_id).first()
        result.taluka = getattr(t, 'name', None)
        # grampanchayat
        if v:
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
            result.grampanchayat = getattr(gp, 'name', None) if gp else None
        else:
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == prop2.gram_panchayat_id).first()
            result.grampanchayat = getattr(gp, 'name', None) if gp else None
        # घर कर / पाणी कर Bank Scanner QR - only shown if the GP has turned this on
        # in Master settings (same toggle used across namuna8/namuna9 print routes).
        show_bank_scanner = bool(gp and gp.show_bank_scanner_in_reports)
        if show_bank_scanner and gp and gp.house_tax_qr_url:
            result.houseTaxQrUrl = f"{backend_url}/location/gram-panchayats/{gp.id}/qr/house"
        if show_bank_scanner and gp and gp.water_tax_qr_url:
            result.waterTaxQrUrl = f"{backend_url}/location/gram-panchayats/{gp.id}/qr/water"
        # occupant from owner occupantName if available, fallback to स्वतः (not the
        # owner's own name again - that duplicated the owner name on this line).
        try:
            if prop2.owners and len(prop2.owners) > 0:
                occ = getattr(prop2.owners[0], 'occupantName', None)
                result.occupant = occ or 'स्वतः'
        except Exception:
            result.occupant = None
        # yearslap from related Namuna9 record
        n9 = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == rec.namuna9_id).first()
        result.yearslap = getattr(n9, 'yearslap', None) if n9 else None
    # शिल्लक थकबाकी - या मालमत्तेच्या तक्त्यातील सध्याचे थकित (shakti*) + चालू (chalu*)
    # आकडे एकत्र (दोन्ही "अजून न भरलेली" रक्कम आहे - collect() दोन्ही कमी करतं),
    # जे ही पावती दिल्यानंतर उरलेली एकूण रक्कम दाखवतात.
    ledger_row = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == rec.namuna9_id,
        namuna9_model.Namuna9PropertyData.property_id == rec.property_id
    ).first()
    if ledger_row:
        # दंड (Dand) घरकर रो सोबतच धरतो - बाकीच्या रकान्यांत जसं प्रिंट टेम्पलेटमध्ये आधीपासूनच
        # दंड फक्त घरकर रोमध्येच दाखवला जातो, तोच नियम शिल्लक बाकीलाही लावला आहे.
        result.remainingGhar = round((ledger_row.shaktiGhar or 0) + (ledger_row.chaluGhar or 0) + (ledger_row.dand or 0), 2)
        result.remainingDiva = round((ledger_row.shaktiDiva or 0) + (ledger_row.chaluDiva or 0), 2)
        result.remainingAarogyaKar = round((ledger_row.shaktiAarogyaKar or 0) + (ledger_row.chaluAarogyaKar or 0), 2)
        result.remainingSapanikar = round((ledger_row.shaktiSapanikar or 0) + (ledger_row.chaluSapanikar or 0), 2)
        result.remainingVpanikar = round((ledger_row.shaktiVpanikar or 0) + (ledger_row.chaluVpanikar or 0), 2)
        result.remainingCleaningTax = round((ledger_row.shaktiCleaningTax or 0) + (ledger_row.chaluCleaningTax or 0), 2)
        result.remainingTotal = round(
            result.remainingGhar + result.remainingDiva + result.remainingAarogyaKar +
            result.remainingSapanikar + result.remainingVpanikar + result.remainingCleaningTax, 2
        )
    return result

def _enrich_receipt(rec, db: Session) -> Namuna9ReceiptRead:
    """Helper to convert ORM receipt to enriched schema object used by multiple endpoints."""
    # Backfill snapshot if missing
    prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
    if prop:
        if not rec.malmatta_kramank:
            rec.malmatta_kramank = prop.malmattaKramank
        if not rec.owner_name:
            try:
                if prop.owners and len(prop.owners) > 0 and getattr(prop.owners[0], 'name', None):
                    rec.owner_name = prop.owners[0].name
            except Exception:
                pass
    db.flush()

    result = Namuna9ReceiptRead.from_orm(rec)
    # Format date
    try:
        if result.pavti_date:
            from datetime import datetime
            if isinstance(result.pavti_date, datetime):
                result.pavti_date = result.pavti_date.strftime('%Y-%m-%d')
            else:
                result.pavti_date = str(result.pavti_date)[:10]
    except Exception:
        pass

    # Enrich names
    if prop:
        v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
        result.village = getattr(v, 'name', None)
        gp = None
        if v:
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
        else:
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == prop.gram_panchayat_id).first()
        result.grampanchayat = getattr(gp, 'name', None) if gp else None
        try:
            if prop.owners and len(prop.owners) > 0:
                occ = getattr(prop.owners[0], 'occupantName', None)
                result.occupant = occ or getattr(prop.owners[0], 'name', None)
        except Exception:
            result.occupant = None
        n9 = db.query(namuna9_model.Namuna9).filter(namuna9_model.Namuna9.id == rec.namuna9_id).first()
        result.yearslap = getattr(n9, 'yearslap', None) if n9 else None
    return result

@router.get("/receipts/by-date-village", response_model=list[Namuna9ReceiptRead])
def list_receipts_by_date_village(
    gram_panchayat_id: int,
    village_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """List enriched receipts for a village between dates (inclusive of from, exclusive of next day to)."""
    # Base query: receipts for GP and properties within village
    q = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id,
        namuna9_model.Namuna9Receipt.is_deleted == False
    )
    prop_ids_subq = db.query(namuna8_model.Property.id).filter(namuna8_model.Property.village_id == village_id).subquery()
    q = q.filter(namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq))

    # Date range
    def _parse_dt(s: Optional[str]):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            try:
                return datetime.strptime(s, '%Y-%m-%d')
            except Exception:
                return None
    fd = _parse_dt(from_date)
    td = _parse_dt(to_date)
    date_expr = func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt)
    if fd:
        q = q.filter(date_expr >= fd)
    if td:
        td_end = td
        if td.time().hour == 0 and td.time().minute == 0 and td.time().second == 0:
            td_end = td + timedelta(days=1)
        q = q.filter(date_expr < td_end)

    rows = q.all()
    try:
        rows = sorted(rows, key=lambda r: int(r.pavti_kramank or 0))
    except Exception:
        rows = sorted(rows, key=lambda r: r.pavti_kramank or 0)
    return [_enrich_receipt(r, db) for r in rows]

@router.get("/receipts/by-date-all", response_model=list[Namuna9ReceiptRead])
def list_receipts_by_date_all(
    gram_panchayat_id: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """List enriched receipts for the entire gram panchayat between dates (all villages)."""
    q = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id,
        namuna9_model.Namuna9Receipt.is_deleted == False
    )
    def _parse_dt(s: Optional[str]):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            try:
                return datetime.strptime(s, '%Y-%m-%d')
            except Exception:
                return None
    fd = _parse_dt(from_date)
    td = _parse_dt(to_date)
    date_expr = func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt)
    if fd:
        q = q.filter(date_expr >= fd)
    if td:
        td_end = td
        if td.time().hour == 0 and td.time().minute == 0 and td.time().second == 0:
            td_end = td + timedelta(days=1)
        q = q.filter(date_expr < td_end)
    rows = q.all()
    try:
        rows = sorted(rows, key=lambda r: int(r.pavti_kramank or 0))
    except Exception:
        rows = sorted(rows, key=lambda r: r.pavti_kramank or 0)
    return [_enrich_receipt(r, db) for r in rows]

@router.get("/receipt/by-date", response_model=list[Namuna9ReceiptRead])
def list_receipts_by_date(
    id: int,
    scope: str = "gram_panchayat", # one of: gram_panchayat | property | namuna9
    district_id: int = None,
    taluka_id: int = None,
    village_id: int = None,
    gram_panchayat_id: int = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """List receipts within a date range filtered by the provided id scope.

    - scope=gram_panchayat -> filter by gram_panchayat_id == id
    - scope=property      -> filter by property_id == id
    - scope=namuna9       -> filter by namuna9_id == id
    """
    # Optional location filters if provided
    if gram_panchayat_id is not None:
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first() if district_id is not None else None
        taluka = db.query(location_models.Taluka).filter(
            location_models.Taluka.id == taluka_id,
            location_models.Taluka.district_id == district_id
        ).first() if (taluka_id is not None and district_id is not None) else None
        gp = db.query(location_models.GramPanchayat).filter(
            location_models.GramPanchayat.id == gram_panchayat_id,
            location_models.GramPanchayat.taluka_id == (taluka_id if taluka_id is not None else location_models.GramPanchayat.taluka_id)
        ).first()
        if district_id is not None and not district:
            raise HTTPException(status_code=404, detail="District not found")
        if taluka_id is not None and not taluka:
            raise HTTPException(status_code=400, detail="Taluka does not belong to district")
        if not gp:
            raise HTTPException(status_code=400, detail="Gram Panchayat validation failed")

    q = db.query(namuna9_model.Namuna9Receipt).filter(namuna9_model.Namuna9Receipt.is_deleted == False)
    if scope == "gram_panchayat":
        q = q.filter(namuna9_model.Namuna9Receipt.gram_panchayat_id == id)
    elif scope == "property":
        q = q.filter(namuna9_model.Namuna9Receipt.property_id == id)
    elif scope == "namuna9":
        q = q.filter(namuna9_model.Namuna9Receipt.namuna9_id == id)
    else:
        raise HTTPException(status_code=400, detail="Invalid scope. Use one of: gram_panchayat | property | namuna9")

    # If both gram_panchayat_id and village_id provided, intersect with properties in village
    if gram_panchayat_id is not None:
        q = q.filter(namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id)
    if village_id is not None:
        prop_ids_subq2 = db.query(namuna8_model.Property.id).filter(namuna8_model.Property.village_id == village_id).subquery()
        q = q.filter(namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq2))

    def _parse_dt(s: Optional[str]):
        if not s:
            return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            try:
                return datetime.strptime(s, '%Y-%m-%d')
            except Exception:
                return None

    fd = _parse_dt(from_date)
    td = _parse_dt(to_date)
    date_expr = func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt)
    if fd:
        q = q.filter(date_expr >= fd)
    if td:
        td_end = td
        if td.time().hour == 0 and td.time().minute == 0 and td.time().second == 0:
            td_end = td + timedelta(days=1)
        q = q.filter(date_expr < td_end)

    rows = q.all()
    try:
        rows = sorted(rows, key=lambda r: int(r.pavti_kramank or 0))
    except Exception:
        rows = sorted(rows, key=lambda r: r.pavti_kramank or 0)
    return rows

@router.put("/receipt/{receipt_id}", response_model=Namuna9ReceiptRead)
def update_receipt(
    receipt_id: int,
    payload: Namuna9ReceiptCreate,
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    gram_panchayat_id: int | None = None,
    db: Session = Depends(database.get_db)
):
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if rec.is_deleted:
        raise HTTPException(status_code=400, detail="Deleted receipt cannot be edited")
    # Optional location validation
    if gram_panchayat_id is not None and rec.gram_panchayat_id != gram_panchayat_id:
        raise HTTPException(status_code=403, detail="Receipt does not belong to specified gram panchayat")
    if village_id is not None:
        prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
        if not prop or prop.village_id != village_id:
            raise HTTPException(status_code=403, detail="Receipt's property is not in specified village")
        # If taluka/district provided, validate the chain
        if taluka_id is not None or district_id is not None or gram_panchayat_id is not None:
            # Validate village in gram panchayat
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == (gram_panchayat_id or rec.gram_panchayat_id)).first()
            if not gp:
                raise HTTPException(status_code=400, detail="Gram Panchayat not found")
            v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == village_id).first()
            if not v or v.gram_panchayat_id != gp.id:
                raise HTTPException(status_code=400, detail="Village does not belong to gram panchayat")
            if taluka_id is not None:
                t = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
                if not t or gp.taluka_id != t.id:
                    raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to taluka")
                if district_id is not None:
                    d = db.query(location_models.District).filter(location_models.District.id == district_id).first()
                    if not d or t.district_id != d.id:
                        raise HTTPException(status_code=400, detail="Taluka does not belong to district")
    old_vasuli = {k: (getattr(rec, k, 0) or 0) for k in VASULI_TO_PROPERTY_FIELD}

    for f, v in payload.dict(exclude_unset=True).items():
        if f == 'pavti_date':
            dt = None
            if v:
                try:
                    dt = datetime.fromisoformat(str(v).replace('Z',''))
                except Exception:
                    dt = None
            setattr(rec, f, dt)
        else:
            setattr(rec, f, v)
    db.commit()
    db.refresh(rec)

    # Re-sync the property's ledger by the difference between the old and new
    # भरणा amounts - reducing a collected amount here restores थकित/चालू back
    # up, increasing it reduces them further.
    new_vasuli = {k: (getattr(rec, k, 0) or 0) for k in VASULI_TO_PROPERTY_FIELD}
    _adjust_property_data_for_receipt(db, rec.namuna9_id, rec.property_id, {
        k: old_vasuli[k] - new_vasuli[k] for k in VASULI_TO_PROPERTY_FIELD
    })

    return rec

@router.delete("/receipt/{receipt_id}")
def delete_receipt(
    receipt_id: int,
    reason: str = "",
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    gram_panchayat_id: int | None = None,
    db: Session = Depends(database.get_db)
):
    if not reason or not reason.strip():
        raise HTTPException(status_code=422, detail="डिलीट करण्याचे कारण आवश्यक आहे")
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if rec.is_deleted:
        raise HTTPException(status_code=400, detail="Receipt is already deleted")
    # Optional location validation
    if gram_panchayat_id is not None and rec.gram_panchayat_id != gram_panchayat_id:
        raise HTTPException(status_code=403, detail="Receipt does not belong to specified gram panchayat")
    if village_id is not None:
        prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == rec.property_id).first()
        if not prop or prop.village_id != village_id:
            raise HTTPException(status_code=403, detail="Receipt's property is not in specified village")
        if taluka_id is not None or district_id is not None or gram_panchayat_id is not None:
            gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == (gram_panchayat_id or rec.gram_panchayat_id)).first()
            if not gp:
                raise HTTPException(status_code=400, detail="Gram Panchayat not found")
            v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == village_id).first()
            if not v or v.gram_panchayat_id != gp.id:
                raise HTTPException(status_code=400, detail="Village does not belong to gram panchayat")
            if taluka_id is not None:
                t = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
                if not t or gp.taluka_id != t.id:
                    raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to taluka")
                if district_id is not None:
                    d = db.query(location_models.District).filter(location_models.District.id == district_id).first()
                    if not d or t.district_id != d.id:
                        raise HTTPException(status_code=400, detail="Taluka does not belong to district")

    # Restore whatever this receipt had marked as collected before removing it.
    _adjust_property_data_for_receipt(db, rec.namuna9_id, rec.property_id, {
        k: (getattr(rec, k, 0) or 0) for k in VASULI_TO_PROPERTY_FIELD
    })

    # सॉफ्ट-डिलीट - रो कायम ठेवतो (client requirement: पावती कधीच पूर्णपणे हरवायची
    # नाही), फक्त is_deleted=True करतो. बाकी सगळीकडे (बॅलन्स/याद्या/एक्सपोर्ट) ही
    # पावती is_deleted==False फिल्टरमुळे आपोआप वगळली जाते - पावती क्रमांकही रो तसाच
    # असल्यामुळे पुन्हा वापरला जाणार नाही.
    rec.is_deleted = True
    rec.deleted_at = datetime.utcnow()
    rec.deleted_by = "ऑपरेटर"
    rec.delete_reason = reason.strip()
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
