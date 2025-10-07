from fastapi import APIRouter, Depends, status, Form, HTTPException, Request, Query
from typing import List
from fastapi.responses import FileResponse
import os
from sqlalchemy.orm import Session
from database import get_db
from .family_certificate_model import FamilyCertificate
from .family_certificate_schemas import FamilyCertificateCreate, FamilyCertificateRead
from datetime import datetime
from barcode import Code39
from barcode.writer import ImageWriter

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.post("/family", response_model=FamilyCertificateRead, status_code=status.HTTP_201_CREATED)
def create_family_certificate(
    id: str = Form(None),
    registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    family_name: str = Form(None),
    family_name_en: str = Form(None),
    adhar_number: str = Form(None),
    adhar_number_en: str = Form(None),
    record_no: str = Form(None),
    applicant_name: str = Form(None),
    applicant_name_en: str = Form(None),
    relation: str = Form(None),
    relation_en: str = Form(None),
    year: str = Form(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)
):
    # Convert empty strings to None for location fields
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    
    # Convert registration_date string to date object
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    cert_id = int(id) if id and id.strip() else None
    cert = FamilyCertificate(
        id=cert_id,
        registration_date=reg_date_obj,
        village=village,
        village_en=village_en,
        family_name=family_name,
        family_name_en=family_name_en,
        adhar_number=adhar_number,
        adhar_number_en=adhar_number_en,
        record_no=record_no,
        applicant_name=applicant_name,
        applicant_name_en=applicant_name_en,
        relation=relation,
        relation_en=relation_en,
        year=year,
        district_id=district_id_int,
        taluka_id=taluka_id_int,
        gram_panchayat_id=gram_panchayat_id_int
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    # Generate and save barcode image
    barcode_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "family_certificates", str(cert.id))
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
    return cert

@router.get("/family", response_model=List[FamilyCertificateRead])
def list_family_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    query = db.query(FamilyCertificate)
    
    # Apply location filters if provided
    if district_id:
        query = query.filter(FamilyCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(FamilyCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(FamilyCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certs = query.all()
    result = []
    for cert in certs:
        cert_data = FamilyCertificateRead.from_orm(cert)
        # Add barcode_url
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/family_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
        
        # Fetch location data
        from location_management import models as location_models
        if cert.district_id:
            district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
            cert_data.jilha = district.name if district else None
        else:
            cert_data.jilha = None
            
        if cert.taluka_id:
            taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
            cert_data.taluka = taluka.name if taluka else None
        else:
            cert_data.taluka = None
            
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
            cert_data.gramPanchayat = gram_panchayat.name if gram_panchayat else None
        else:
            cert_data.gramPanchayat = None
            
        result.append(cert_data)
    return result 

@router.get("/family/{id}", response_model=FamilyCertificateRead)
def get_family_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(FamilyCertificate).filter(FamilyCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Family certificate not found")
    cert_data = FamilyCertificateRead.from_orm(cert)
    # Add barcode_url
    cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/family_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    
    # Fetch location data
    from location_management import models as location_models
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        cert_data.jilha = district.name if district else None
    else:
        cert_data.jilha = None
        
    if cert.taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        cert_data.taluka = taluka.name if taluka else None
    else:
        cert_data.taluka = None
        
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        cert_data.gramPanchayat = gram_panchayat.name if gram_panchayat else None
    else:
        cert_data.gramPanchayat = None
        
    return cert_data

@router.put("/family/{id}", response_model=FamilyCertificateRead)
def update_family_certificate(id: int, registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    family_name: str = Form(None),
    family_name_en: str = Form(None),
    adhar_number: str = Form(None),
    adhar_number_en: str = Form(None),
    record_no: str = Form(None),
    applicant_name: str = Form(None),
    applicant_name_en: str = Form(None),
    relation: str = Form(None),
    relation_en: str = Form(None),
    year: str = Form(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)):
    cert = db.query(FamilyCertificate).filter(FamilyCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Family certificate not found")
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    setattr(cert, "registration_date", reg_date_obj)
    setattr(cert, "village", village)
    setattr(cert, "village_en", village_en)
    setattr(cert, "family_name", family_name)
    setattr(cert, "family_name_en", family_name_en)
    setattr(cert, "adhar_number", adhar_number)
    setattr(cert, "adhar_number_en", adhar_number_en)
    setattr(cert, "record_no", record_no)
    setattr(cert, "applicant_name", applicant_name)
    setattr(cert, "applicant_name_en", applicant_name_en)
    setattr(cert, "relation", relation)
    setattr(cert, "relation_en", relation_en)
    setattr(cert, "year", year)
    setattr(cert, "district_id", int(district_id) if district_id and district_id.strip() else None)
    setattr(cert, "taluka_id", int(taluka_id) if taluka_id and taluka_id.strip() else None)
    setattr(cert, "gram_panchayat_id", int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None)
    db.commit()
    db.refresh(cert)
    # Regenerate barcode
    barcode_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "family_certificates", str(cert.id))
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
    return cert

@router.get("/family_barcode/{id}")
def get_family_certificate_barcode(
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
    cert = db.query(FamilyCertificate).filter(
        FamilyCertificate.id == id,
        FamilyCertificate.district_id == district_id,
        FamilyCertificate.taluka_id == taluka_id,
        FamilyCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Family certificate not found in the specified location")
    
    # Use location-based barcode path
    barcode_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "family_certificates", str(id), "barcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join("uploaded_images", "family_certificate_barcodes", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(barcode_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode not found")
    
    return FileResponse(barcode_path, media_type="image/png") 