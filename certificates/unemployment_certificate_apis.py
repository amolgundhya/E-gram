from fastapi import APIRouter, Depends, status, Form, HTTPException, Request, File, UploadFile, Query
from typing import List
from fastapi.responses import FileResponse
import os
import shutil
from sqlalchemy.orm import Session
from database import get_db
from .unemployment_certificate_model import UnemploymentCertificate
from .unemployment_certificate_schemas import UnemploymentCertificateCreate, UnemploymentCertificateRead
from datetime import datetime
from barcode import Code39
from barcode.writer import ImageWriter
from location_management.models import District, Taluka, GramPanchayat

router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/unemployment", response_model=UnemploymentCertificateRead, status_code=status.HTTP_201_CREATED)
def create_unemployment_certificate(
    id: str = Form(None),
    registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    applicant_name: str = Form(None),
    applicant_name_en: str = Form(None),
    adhar_number: str = Form(None),
    adhar_number_en: str = Form(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    # Convert empty strings to None for location fields
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    cert_id = int(id) if id and id.strip() else None
    cert = UnemploymentCertificate(
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
    # Handle image upload in location-based folder structure
    image_path = None
    if image:
        filename = image.filename.replace(" ", "_") if image.filename else "image.png"
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "unemployment_certificates", "images", str(cert.id))
        else:
            image_dir = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(cert.id))
        os.makedirs(image_dir, exist_ok=True)
        image_path = os.path.join(image_dir, filename)
        with open(image_path, "wb") as f:
            f.write(image.file.read())
        setattr(cert, "image", image_path.replace(os.sep, "/"))
    
    # Generate and save barcode image in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "unemployment_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(cert.id))
    
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

@router.get("/unemployment", response_model=List[UnemploymentCertificateRead])
def list_unemployment_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    request: Request = None, 
    db: Session = Depends(get_db)
):
    query = db.query(UnemploymentCertificate)
    
    # Apply location filters if provided
    if district_id:
        query = query.filter(UnemploymentCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(UnemploymentCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(UnemploymentCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certs = query.all()
    result = []
    for cert in certs:
        # Populate location names
        if cert.district_id:
            district = db.query(District).filter(District.id == cert.district_id).first()
            cert.gramPanchayat = district.name if district else None
        if cert.taluka_id:
            taluka = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
            cert.taluka = taluka.name if taluka else None
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
            cert.jilha = gram_panchayat.name if gram_panchayat else None
        
        cert_data = UnemploymentCertificateRead.from_orm(cert)
        
        # Construct URLs with location query parameters if available
        barcode_val = str(getattr(cert, 'barcode', ''))
        if barcode_val:
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/unemployment_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/unemployment_barcode/{cert.id}"
        else:
            cert_data.barcode_url = None
            
        image_val = str(getattr(cert, 'image', ''))
        if image_val:
            # Check if the image file actually exists
            image_file_path = image_val
            if not os.path.isabs(image_file_path):
                image_file_path = os.path.join(UPLOAD_DIR, image_file_path) if not image_file_path.startswith(UPLOAD_DIR) else image_file_path
            if os.path.exists(image_file_path):
                if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/unemployment_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
                else:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/unemployment_image/{cert.id}"
            else:
                cert_data.image_url = None
        else:
            cert_data.image_url = None
            
        result.append(cert_data)
    return result

@router.get("/unemployment/{id}", response_model=UnemploymentCertificateRead)
def get_unemployment_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(UnemploymentCertificate).filter(UnemploymentCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Unemployment certificate not found")
    
    # Populate location names
    if cert.district_id:
        district = db.query(District).filter(District.id == cert.district_id).first()
        cert.gramPanchayat = district.name if district else None
    if cert.taluka_id:
        taluka = db.query(Taluka).filter(Taluka.id == cert.taluka_id).first()
        cert.taluka = taluka.name if taluka else None
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(GramPanchayat).filter(GramPanchayat.id == cert.gram_panchayat_id).first()
        cert.jilha = gram_panchayat.name if gram_panchayat else None
    
    cert_data = UnemploymentCertificateRead.from_orm(cert)
    
    # Construct URLs with location query parameters if available
    barcode_val = str(getattr(cert, 'barcode', ''))
    if barcode_val:
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/unemployment_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
        else:
            cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/unemployment_barcode/{cert.id}"
    else:
        cert_data.barcode_url = None
        
    image_val = str(getattr(cert, 'image', ''))
    if image_val:
        image_file_path = image_val
        if not os.path.isabs(image_file_path):
            image_file_path = os.path.join(UPLOAD_DIR, image_file_path) if not image_file_path.startswith(UPLOAD_DIR) else image_file_path
        if os.path.exists(image_file_path):
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/unemployment_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/unemployment_image/{cert.id}"
        else:
            cert_data.image_url = None
    else:
        cert_data.image_url = None
    
    return cert_data

@router.put("/unemployment/{id}", response_model=UnemploymentCertificateRead)
def update_unemployment_certificate(id: int, registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    applicant_name: str = Form(None),
    applicant_name_en: str = Form(None),
    adhar_number: str = Form(None),
    adhar_number_en: str = Form(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)):
    cert = db.query(UnemploymentCertificate).filter(UnemploymentCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Unemployment certificate not found")
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    setattr(cert, "registration_date", reg_date_obj)
    setattr(cert, "village", village)
    setattr(cert, "village_en", village_en)
    setattr(cert, "applicant_name", applicant_name)
    setattr(cert, "applicant_name_en", applicant_name_en)
    setattr(cert, "adhar_number", adhar_number)
    setattr(cert, "adhar_number_en", adhar_number_en)
    setattr(cert, "district_id", int(district_id) if district_id and district_id.strip() else None)
    setattr(cert, "taluka_id", int(taluka_id) if taluka_id and taluka_id.strip() else None)
    setattr(cert, "gram_panchayat_id", int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None)
    # Handle image upload and removal in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "unemployment_certificates", "images", str(cert.id))
    else:
        image_dir = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(cert.id))
    
    os.makedirs(image_dir, exist_ok=True)
    old_image_path = getattr(cert, "image", None)
    if image:
        filename = image.filename.replace(" ", "_") if image.filename else "image.png"
        image_path = os.path.join(image_dir, filename)
        # Remove old image if exists and is different
        if old_image_path and os.path.exists(old_image_path) and old_image_path != image_path:
            try:
                os.remove(old_image_path)
            except Exception:
                pass
        with open(image_path, "wb") as f:
            f.write(image.file.read())
        setattr(cert, "image", image_path.replace(os.sep, "/"))
    else:
        # If no image provided, remove old image and clear DB field
        if old_image_path and os.path.exists(old_image_path):
            try:
                os.remove(old_image_path)
            except Exception:
                pass
        setattr(cert, "image", None)
    
    # Regenerate barcode in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "unemployment_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(cert.id))
    
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

@router.get("/unemployment_barcode/{id}")
def get_unemployment_certificate_barcode(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(UnemploymentCertificate).filter(UnemploymentCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Unemployment certificate not found")
    
    # Determine the barcode path based on location parameters or certificate's stored location
    if district_id and taluka_id and gram_panchayat_id:
        # Validate that provided location matches certificate's location
        if cert.district_id != district_id or cert.taluka_id != taluka_id or cert.gram_panchayat_id != gram_panchayat_id:
            raise HTTPException(status_code=400, detail="Location parameters do not match certificate location")
        barcode_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "unemployment_certificates", "barcodes", str(id), "barcode.png")
    elif cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        # Use certificate's stored location
        barcode_path = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "unemployment_certificates", "barcodes", str(id), "barcode.png")
    else:
        # Fallback to old path
        barcode_path = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(id), "barcode.png")
    
    # Check if file exists in new location, if not try to migrate from old location
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Migrate file to new location
            new_dir = os.path.dirname(barcode_path)
            os.makedirs(new_dir, exist_ok=True)
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode file not found")
    
    return FileResponse(barcode_path, media_type="image/png")

@router.get("/unemployment_image/{id}")
def get_unemployment_certificate_image(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(UnemploymentCertificate).filter(UnemploymentCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Unemployment certificate not found")
    
    # Determine the image path based on location parameters or certificate's stored location
    if district_id and taluka_id and gram_panchayat_id:
        # Validate that provided location matches certificate's location
        if cert.district_id != district_id or cert.taluka_id != taluka_id or cert.gram_panchayat_id != gram_panchayat_id:
            raise HTTPException(status_code=400, detail="Location parameters do not match certificate location")
        # For images, we need to check the actual image filename from the database
        image_path = getattr(cert, "image", None)
        if image_path:
            # Extract filename from the stored path
            filename = os.path.basename(image_path)
            image_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "unemployment_certificates", "images", str(id), filename)
    elif cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        # Use certificate's stored location
        image_path = getattr(cert, "image", None)
    else:
        # Fallback to old path
        image_path = getattr(cert, "image", None)
    
    if not image_path:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Check if file exists in new location, if not try to migrate from old location
    if not os.path.exists(image_path):
        old_image_path = getattr(cert, "image", None)
        if old_image_path and os.path.exists(old_image_path):
            # Migrate file to new location
            new_dir = os.path.dirname(image_path)
            os.makedirs(new_dir, exist_ok=True)
            shutil.copy2(old_image_path, image_path)
        else:
            raise HTTPException(status_code=404, detail="Image file not found")
    
    return FileResponse(image_path, media_type="image/png")

@router.put("/unemployment/{id}/fix-location")
def fix_unemployment_certificate_location(
    id: int,
    district_id: int = Form(...),
    taluka_id: int = Form(...),
    gram_panchayat_id: int = Form(...),
    db: Session = Depends(get_db)
):
    cert = db.query(UnemploymentCertificate).filter(UnemploymentCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Unemployment certificate not found")
    
    # Update location IDs
    cert.district_id = district_id
    cert.taluka_id = taluka_id
    cert.gram_panchayat_id = gram_panchayat_id
    
    # Migrate image file to new location
    old_image_path = getattr(cert, "image", None)
    if old_image_path and os.path.exists(old_image_path):
        filename = os.path.basename(old_image_path)
        new_image_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "unemployment_certificates", "images", str(id))
        new_image_path = os.path.join(new_image_dir, filename)
        os.makedirs(new_image_dir, exist_ok=True)
        shutil.copy2(old_image_path, new_image_path)
        # Update the image path in database
        cert.image = new_image_path.replace(os.sep, "/")
    
    # Migrate barcode file to new location
    old_barcode_path = os.path.join(UPLOAD_DIR, "unemployment_certificates", str(id), "barcode.png")
    if os.path.exists(old_barcode_path):
        new_barcode_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "unemployment_certificates", "barcodes", str(id))
        new_barcode_path = os.path.join(new_barcode_dir, "barcode.png")
        os.makedirs(new_barcode_dir, exist_ok=True)
        shutil.copy2(old_barcode_path, new_barcode_path)
        # Update the barcode path in database
        cert.barcode = new_barcode_path.replace(os.sep, "/")
    
    db.commit()
    db.refresh(cert)
    
    return {"message": "Location updated and files migrated successfully"}

@router.get("/unemployment-all")
def list_all_unemployment_certificates(db: Session = Depends(get_db)):
    """Get all Unemployment certificates without filters for debugging"""
    certificates = db.query(UnemploymentCertificate).all()
    
    # Populate location names for each certificate
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