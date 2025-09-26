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
        # Include dand in ekunGhar (house total)
        existing.ekunGhar = (existing.shaktiGhar or 0) + (existing.chaluGhar or 0) + (existing.dand or 0)
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
    # Include dand in ekunGhar (house total)
    db_property_data.ekunGhar = (db_property_data.shaktiGhar or 0) + (db_property_data.chaluGhar or 0) + (db_property_data.dand or 0)
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
    # Include dand in ekunGhar recompute
    data.ekunGhar = (data.shaktiGhar or 0) + (data.chaluGhar or 0) + (data.dand or 0)
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
    # Normalize pavti_date to datetime if provided as ISO string
    pavti_dt = None
    if payload.pavti_date:
        try:
            pavti_dt = datetime.fromisoformat(str(payload.pavti_date).replace('Z',''))
        except Exception:
            pavti_dt = None
    rec = namuna9_model.Namuna9Receipt(
        namuna9_id=payload.namuna9_id,
        property_id=payload.property_id,
        gram_panchayat_id=payload.gram_panchayat_id,
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
    return rec

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
    village = db.query(location_models.Village).filter(
        location_models.Village.id == village_id,
        location_models.Village.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not village:
        raise HTTPException(status_code=400, detail="Village does not belong to gram panchayat")

    q = db.query(namuna9_model.Namuna9Receipt).filter(
        namuna9_model.Namuna9Receipt.gram_panchayat_id == gram_panchayat_id
    )
    # Further restrict to receipts for properties in this village
    prop_ids_subq = db.query(namuna8_model.Property.id).filter(namuna8_model.Property.village_id == village_id).subquery()
    q = q.filter(namuna9_model.Namuna9Receipt.property_id.in_(prop_ids_subq))
    if receipt_id:
        q = q.filter(namuna9_model.Namuna9Receipt.id == receipt_id)
    if not show_all:
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
            # include the whole day if only date provided
            td_end = td
            if td.time().hour == 0 and td.time().minute == 0 and td.time().second == 0:
                td_end = td + timedelta(days=1)
            q = q.filter(date_expr < td_end)
    return q.order_by(func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt).desc()).all()

@router.get("/receipt/{receipt_id}", response_model=Namuna9ReceiptRead)
def get_receipt(receipt_id: int, db: Session = Depends(database.get_db)):
    """Fetch a single receipt by id with all fields."""
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return rec

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

    q = db.query(namuna9_model.Namuna9Receipt)
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

    return q.order_by(func.coalesce(namuna9_model.Namuna9Receipt.pavti_date, namuna9_model.Namuna9Receipt.createdAt).desc()).all()

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
            v = db.query(location_models.Village).filter(location_models.Village.id == village_id).first()
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
    return rec

@router.delete("/receipt/{receipt_id}")
def delete_receipt(
    receipt_id: int,
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    gram_panchayat_id: int | None = None,
    db: Session = Depends(database.get_db)
):
    rec = db.query(namuna9_model.Namuna9Receipt).get(receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Receipt not found")
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
            v = db.query(location_models.Village).filter(location_models.Village.id == village_id).first()
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
