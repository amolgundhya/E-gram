from fastapi import APIRouter, Depends, status, Form, HTTPException, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from .life_certificate_model import LifeCertificate
from .life_certificate_schemas import LifeCertificateCreate, LifeCertificateRead
from datetime import datetime
import shutil
import os
from barcode import Code39
from barcode.writer import ImageWriter
from location_management.models import District, Taluka, GramPanchayat

router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/life", response_model=LifeCertificateRead, status_code=status.HTTP_201_CREATED)
def create_life_certificate(
    id: str = Form(None),
    registration_date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_number: str = Form(...),
    adhar_number_en: str = Form(...),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)
):
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    
    # Convert location fields to integers
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    cert_id = int(id) if id and id.strip() else None
    cert = LifeCertificate(
        id=cert_id,
        registration_date=reg_date_obj,
        village=village,
        village_en=village_en,
        applicant_name=applicant_name,
        applicant_name_en=applicant_name_en,
        adhar_number=adhar_number,
        adhar_number_en=adhar_number_en,
        district_id=district_id_int,
        taluka_id=taluka_id_int,
        gram_panchayat_id=gram_panchayat_id_int
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    
    # Generate and save barcode image in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "life_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "life_certificate_barcodes", str(cert.id))
    
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

@router.get("/life", response_model=list[LifeCertificateRead])
def list_life_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    db: Session = Depends(get_db)
):
    query = db.query(LifeCertificate)
    if district_id:
        query = query.filter(LifeCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(LifeCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(LifeCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certificates = query.all()
    
    # Add location names and construct URLs with query parameters
    for cert in certificates:
        # Fetch location names
        if cert.district_id:
            district = db.query(District).filter(District.id == cert.district_id).first()
            cert.gramPanchayat = district.name if district else None
        if cert.taluka_id:
            taluka = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
            cert.taluka = taluka.name if taluka else None
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
            cert.jilha = gram_panchayat.name if gram_panchayat else None
        
        # Construct barcode URL with location query parameters if available
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            cert.barcode_url = f"/certificates/life_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
        else:
            cert.barcode_url = f"/certificates/life_barcode/{cert.id}"
    
    return certificates

@router.get("/life/{id}", response_model=LifeCertificateRead)
def get_life_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(LifeCertificate).filter(LifeCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Life certificate not found")
    
    # Fetch location names
    gramPanchayat = None
    taluka = None
    jilha = None
    
    if cert.district_id:
        district = db.query(District).filter(District.id == cert.district_id).first()
        gramPanchayat = district.name if district else None
    if cert.taluka_id:
        taluka_obj = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
        taluka = taluka_obj.name if taluka_obj else None
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
        jilha = gram_panchayat.name if gram_panchayat else None
    
    cert_data = LifeCertificateRead.from_orm(cert)
    
    # Construct barcode URL with location query parameters if available
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/life_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    else:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/life_barcode/{cert.id}"
    
    cert_data.gramPanchayat = gramPanchayat
    cert_data.taluka = taluka
    cert_data.jilha = jilha
    return cert_data

@router.put("/life/{id}", response_model=LifeCertificateRead)
def update_life_certificate(
    id: int,
    request: Request,
    registration_date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_number: str = Form(...),
    adhar_number_en: str = Form(...),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)
):
    cert = db.query(LifeCertificate).filter(LifeCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Life certificate not found")
    
    # Convert location fields to integers
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    setattr(cert, "registration_date", reg_date_obj)
    setattr(cert, "village", village)
    setattr(cert, "village_en", village_en)
    setattr(cert, "applicant_name", applicant_name)
    setattr(cert, "applicant_name_en", applicant_name_en)
    setattr(cert, "adhar_number", adhar_number)
    setattr(cert, "adhar_number_en", adhar_number_en)
    setattr(cert, "district_id", district_id_int)
    setattr(cert, "taluka_id", taluka_id_int)
    setattr(cert, "gram_panchayat_id", gram_panchayat_id_int)
    db.commit()
    db.refresh(cert)
    
    # Regenerate barcode in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "life_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "life_certificate_barcodes", str(cert.id))
    
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
    
    # Fetch location names
    gramPanchayat = None
    taluka = None
    jilha = None
    
    if cert.district_id:
        district = db.query(District).filter(District.id == cert.district_id).first()
        gramPanchayat = district.name if district else None
    if cert.taluka_id:
        taluka_obj = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
        taluka = taluka_obj.name if taluka_obj else None
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
        jilha = gram_panchayat.name if gram_panchayat else None
    
    cert_data = LifeCertificateRead.from_orm(cert)
    
    # Construct barcode URL with location query parameters if available
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/life_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    else:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/life_barcode/{cert.id}"
    
    cert_data.gramPanchayat = gramPanchayat
    cert_data.taluka = taluka
    cert_data.jilha = jilha
    return cert_data

@router.get("/life_barcode/{id}")
def get_life_certificate_barcode(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(LifeCertificate).filter(LifeCertificate.id == id).first()
    if not cert or not getattr(cert, "barcode", None):
        raise HTTPException(status_code=404, detail="Barcode not found")
    
    barcode_path = getattr(cert, "barcode", None)
    
    # If location parameters are provided, validate them
    if district_id is not None and taluka_id is not None and gram_panchayat_id is not None:
        if (cert.district_id != district_id or 
            cert.taluka_id != taluka_id or 
            cert.gram_panchayat_id != gram_panchayat_id):
            raise HTTPException(status_code=400, detail="Location parameters do not match certificate location")
        
        # Check if file exists in new location-based path
        new_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "life_certificates", "barcodes", str(id), "barcode.png")
        if os.path.exists(new_path):
            barcode_path = new_path
        else:
            # Try to migrate from old path to new path
            old_path = os.path.join(UPLOAD_DIR, "life_certificate_barcodes", str(id), "barcode.png")
            if os.path.exists(old_path):
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.copy2(old_path, new_path)
                barcode_path = new_path
                # Update the database record
                setattr(cert, "barcode", new_path.replace(os.sep, "/"))
                db.commit()
    
    if not barcode_path or not os.path.exists(barcode_path):
        raise HTTPException(status_code=404, detail="Barcode file not found")
    
    return FileResponse(barcode_path, media_type="image/png")

@router.put("/life/{id}/fix-location")
def fix_life_certificate_location(
    id: int,
    district_id: int = Form(...),
    taluka_id: int = Form(...),
    gram_panchayat_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Fix location IDs for existing life certificates and migrate their files"""
    cert = db.query(LifeCertificate).filter(LifeCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Life certificate not found")
    
    # Update location IDs
    cert.district_id = district_id
    cert.taluka_id = taluka_id
    cert.gram_panchayat_id = gram_panchayat_id
    
    # Migrate barcode file to new location
    old_barcode_path = os.path.join(UPLOAD_DIR, "life_certificate_barcodes", str(id), "barcode.png")
    new_barcode_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "life_certificates", "barcodes", str(id))
    new_barcode_path = os.path.join(new_barcode_dir, "barcode.png")
    
    if os.path.exists(old_barcode_path):
        os.makedirs(new_barcode_dir, exist_ok=True)
        shutil.copy2(old_barcode_path, new_barcode_path)
        cert.barcode = new_barcode_path.replace(os.sep, "/")
    
    db.commit()
    db.refresh(cert)
    
    return {"message": "Location updated and files migrated successfully"}

@router.get("/life-all")
def list_all_life_certificates(db: Session = Depends(get_db)):
    """List all life certificates without any filters for debugging"""
    certificates = db.query(LifeCertificate).all()
    
    # Add location names for debugging
    for cert in certificates:
        if cert.district_id:
            district = db.query(District).filter(District.id == cert.district_id).first()
            cert.gramPanchayat = district.name if district else None
        if cert.taluka_id:
            taluka = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
            cert.taluka = taluka.name if taluka else None
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
            cert.jilha = gram_panchayat.name if gram_panchayat else None
    
    return certificates 