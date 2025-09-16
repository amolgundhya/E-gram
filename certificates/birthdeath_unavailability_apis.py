from fastapi import APIRouter, Depends, status, Request, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from .birthdeath_unavailability_model import BirthDeathUnavailabilityCertificate
from .birthdeath_unavailability_schemas import BirthDeathUnavailabilityCertificateCreate, BirthDeathUnavailabilityCertificateRead
import os
from barcode import Code39
from barcode.writer import ImageWriter

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.post("/birthdeath-unavailability", response_model=BirthDeathUnavailabilityCertificateRead, status_code=status.HTTP_201_CREATED)
def create_certificate(data: BirthDeathUnavailabilityCertificateCreate, db: Session = Depends(get_db)):
    cert = BirthDeathUnavailabilityCertificate(**data.dict())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    # Generate and save barcode image
    barcode_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "birthdeath_unavailability_barcodes", str(cert.id))
    os.makedirs(barcode_dir, exist_ok=True)
    barcode_path = os.path.join(barcode_dir, "barcode.png")
    barcode_obj = Code39(
        str(cert.id),
        writer=ImageWriter(),
        add_checksum=False
    )
    barcode_obj.save(
        barcode_path.replace('.png', ''),
        options={
            "write_text": False,      # No number below barcode
            "module_height": 18,     # Shorter bars, like original
            "module_width": 1.2,     # Wider barcode, like original
            "quiet_zone": 6.5        # Standard margin
        }
    )
    # Store barcode image path in DB
    setattr(cert, "barcode", barcode_path.replace(os.sep, "/"))
    db.commit()
    db.refresh(cert)
    return cert

@router.get("/birthdeath-unavailability", response_model=List[BirthDeathUnavailabilityCertificateRead])
def list_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(BirthDeathUnavailabilityCertificate)
    
    if district_id:
        query = query.filter(BirthDeathUnavailabilityCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(BirthDeathUnavailabilityCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(BirthDeathUnavailabilityCertificate.gram_panchayat_id == gram_panchayat_id)

    certs = query.all()

   
    return [BirthDeathUnavailabilityCertificateRead.from_orm(cert) for cert in certs]


@router.get("/birthdeath-unavailability/{id}", response_model=BirthDeathUnavailabilityCertificateRead)
def get_birthdeath_unavailability_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(BirthDeathUnavailabilityCertificate).filter(BirthDeathUnavailabilityCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    cert_data = BirthDeathUnavailabilityCertificateRead.from_orm(cert)
    # Add barcode_url
    cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/birthdeath-unavailability_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    return cert_data

@router.put("/birthdeath-unavailability/{id}", response_model=BirthDeathUnavailabilityCertificateRead)
def update_birthdeath_unavailability_certificate(id: int, data: BirthDeathUnavailabilityCertificateCreate, db: Session = Depends(get_db)):
    cert = db.query(BirthDeathUnavailabilityCertificate).filter(BirthDeathUnavailabilityCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    for field, value in data.dict(exclude_unset=True).items():
        setattr(cert, field, value)
    db.commit()
    db.refresh(cert)
    return cert

@router.get("/birthdeath-unavailability_barcode/{id}")
def get_birthdeath_unavailability_barcode(
    id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy
    from location_management import models as location_models
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    # Validate that the certificate belongs to the specified location hierarchy
    cert = db.query(BirthDeathUnavailabilityCertificate).filter(
        BirthDeathUnavailabilityCertificate.id == id,
        BirthDeathUnavailabilityCertificate.district_id == district_id,
        BirthDeathUnavailabilityCertificate.taluka_id == taluka_id,
        BirthDeathUnavailabilityCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Birth Death Unavailability certificate not found in the specified location")
    
    # Use location-based barcode path
    barcode_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "birthdeath_unavailability_barcodes", str(id), "barcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join("uploaded_images", "birthdeath_unavailability_barcodes", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(barcode_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(barcode_path, media_type="image/png") 