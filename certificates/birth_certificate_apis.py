from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from database import get_db
from .birth_certificate_model import BirthCertificate
from .birth_certificate_schemas import BirthCertificateCreate, BirthCertificateRead
from Utility.QRcodeGeneration import QRCodeGeneration
import os
from fastapi.responses import FileResponse
from barcode import Code39
from barcode.writer import ImageWriter
from location_management import models as location_models

router = APIRouter(prefix="/certificates", tags=["certificates"])

def _build_birth_qrcode_url(request: Request, cert: BirthCertificate, qr_path: str) -> str:
    version = int(os.path.getmtime(qr_path))
    return (
        str(request.base_url)[:-1]
        + f"/certificates/birth_qrcode/{cert.id}"
        + f"?district_id={cert.district_id}&taluka_id={cert.taluka_id}"
        + f"&gram_panchayat_id={cert.gram_panchayat_id}&v={version}"
    )

@router.post("/birth", response_model=BirthCertificateRead, status_code=status.HTTP_201_CREATED)
def create_birth_certificate(data: BirthCertificateCreate, db: Session = Depends(get_db)):
    # Check for duplicate ID
    if data.id is not None:
        existing = db.query(BirthCertificate).filter(BirthCertificate.id == data.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="A birth certificate with this ID already exists.")
    cert = BirthCertificate(**data.dict())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    # Set barcode to id after save
    barcode_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "birth_certificate_barcodes", str(cert.id))
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
            "write_text": False,
            "module_height": 18,
            "module_width": 1.2,
            "quiet_zone": 6.5
        }
    )
    setattr(cert, "barcode", barcode_path.replace(os.sep, "/"))
    db.commit()
    db.refresh(cert)
    # --- QR CODE GENERATION ---
    try:
        qr_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "birth_certificates", str(cert.id))
        qr_path = os.path.join(qr_dir, "qrcode.png")
        qr_data = {
            "SRNo": cert.id,
            "Reg Date": str(cert.register_date) if cert.register_date is not None else "",
            "Birth Date": str(cert.birth_date) if cert.birth_date is not None else "",
            "Child Name": cert.child_name_en or "",
            "Sex": cert.gender_en or "",
            "Place Of Birth": cert.birth_place_en or "",
            "Mother Name": cert.mother_name_en or "",
            "Father Name": cert.father_name_en or "",
        }
        QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
        # --- Save QR path in DB ---
        setattr(cert, "qrcode", qr_path.replace(os.sep, "/"))
        db.commit()
        db.refresh(cert)
    except Exception as e:
        print(f"QR code generation failed: {e}")
    return cert

@router.get("/birth", response_model=list[BirthCertificateRead])
def list_birth_certificates(
    district_id: int = Query(None, description="Filter by district ID"),
    taluka_id: int = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: int = Query(None, description="Filter by gram panchayat ID"),
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
    
    query = db.query(BirthCertificate)
    if district_id:
        query = query.filter(BirthCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(BirthCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(BirthCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certificates = query.all()
    
    # Add location names to each certificate
    result = []
    for cert in certificates:
        cert_data = BirthCertificateRead.from_orm(cert)
        
        # Fetch location names
        district_name = None
        taluka_name = None
        gram_panchayat_name = None
        
        if cert.district_id:
            district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
            if district:
                district_name = district.name
        
        if cert.taluka_id:
            taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
            if taluka:
                taluka_name = taluka.name
        
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
            if gram_panchayat:
                gram_panchayat_name = gram_panchayat.name
        
        # Set location names
        cert_data.jilha = district_name
        cert_data.taluka = taluka_name
        cert_data.gramPanchayat = gram_panchayat_name
        
        result.append(cert_data)
    
    return result

@router.get("/birth/{id}", response_model=BirthCertificateRead)
def get_birth_certificate(
    id: int, 
    district_id: int = Query(None, description="Filter by district ID"),
    taluka_id: int = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: int = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(get_db), 
    request: Request = None
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
    
    query = db.query(BirthCertificate).filter(BirthCertificate.id == id)
    if district_id:
        query = query.filter(BirthCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(BirthCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(BirthCertificate.gram_panchayat_id == gram_panchayat_id)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Birth certificate not found")
    
    # Fetch location names
    district_name = None
    taluka_name = None
    gram_panchayat_name = None
    
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        if district:
            district_name = district.name
    
    if cert.taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        if taluka:
            taluka_name = taluka.name
    
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        if gram_panchayat:
            gram_panchayat_name = gram_panchayat.name
    
    cert_data = BirthCertificateRead.from_orm(cert)
    
    # Set location names
    cert_data.jilha = district_name
    cert_data.taluka = taluka_name
    cert_data.gramPanchayat = gram_panchayat_name
    
    if getattr(cert, "qrcode", None) and os.path.exists(cert.qrcode):
        cert_data.qrcode = _build_birth_qrcode_url(request, cert, cert.qrcode)
    else:
        cert_data.qrcode = None
    # Add barcode_url
    cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/birth_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    return cert_data

@router.put("/birth/{id}", response_model=BirthCertificateRead)
def update_birth_certificate(
    id: int, 
    data: BirthCertificateCreate, 
    district_id: int = Query(None, description="Filter by district ID"),
    taluka_id: int = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: int = Query(None, description="Filter by gram panchayat ID"),
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
    
    query = db.query(BirthCertificate).filter(BirthCertificate.id == id)
    if district_id:
        query = query.filter(BirthCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(BirthCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(BirthCertificate.gram_panchayat_id == gram_panchayat_id)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Birth certificate not found")
    
    # Update with location fields
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cert, field, value)
    db.commit()
    db.refresh(cert)
    
    # Fetch location names
    district_name = None
    taluka_name = None
    gram_panchayat_name = None
    
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        if district:
            district_name = district.name
    
    if cert.taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        if taluka:
            taluka_name = taluka.name
    
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        if gram_panchayat:
            gram_panchayat_name = gram_panchayat.name
    
    cert_data = BirthCertificateRead.from_orm(cert)
    
    # Set location names
    cert_data.jilha = district_name
    cert_data.taluka = taluka_name
    cert_data.gramPanchayat = gram_panchayat_name
    
    # Regenerate QR code with latest info
    try:
        qr_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "birth_certificates", str(cert.id))
        qr_path = os.path.join(qr_dir, "qrcode.png")
        qr_data = {
            "SRNo": cert.id,
            "Reg Date": str(cert.register_date) if cert.register_date is not None else "",
            "Birth Date": str(cert.birth_date) if cert.birth_date is not None else "",
            "Child Name": cert.child_name_en or "",
            "Sex": cert.gender_en or "",
            "Place Of Birth": cert.birth_place_en or "",
            "Mother Name": cert.mother_name_en or "",
            "Father Name": cert.father_name_en or "",
        }
        QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
        setattr(cert, "qrcode", qr_path.replace(os.sep, "/"))
        db.commit()
        db.refresh(cert)
    except Exception as e:
        print(f"QR code regeneration failed: {e}")
    
    return cert_data

@router.get("/birth_qrcode/{id}")
def get_birth_certificate_qrcode(
    id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy
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
    cert = db.query(BirthCertificate).filter(
        BirthCertificate.id == id,
        BirthCertificate.district_id == district_id,
        BirthCertificate.taluka_id == taluka_id,
        BirthCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Birth certificate not found in the specified location")
    
    # Use location-based QR path
    qr_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "birth_certificates", str(id), "qrcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(qr_path):
        old_qr_path = os.path.join("uploaded_images", "birth_certificates_qr", str(id), "qrcode.png")
        if os.path.exists(old_qr_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(qr_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_qr_path, qr_path)
        else:
            raise HTTPException(status_code=404, detail="QR code not found")
    
    return FileResponse(
        qr_path,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@router.get("/birth_barcode/{id}")
def get_birth_certificate_barcode(
    id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy
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
    cert = db.query(BirthCertificate).filter(
        BirthCertificate.id == id,
        BirthCertificate.district_id == district_id,
        BirthCertificate.taluka_id == taluka_id,
        BirthCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Birth certificate not found in the specified location")
    
    # Use location-based barcode path
    barcode_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "birth_certificate_barcodes", str(id), "barcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join("uploaded_images", "birth_certificate_barcodes", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(barcode_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode not found")
    
    return FileResponse(barcode_path, media_type="image/png") 