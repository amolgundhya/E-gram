from fastapi import APIRouter, Depends, status, Form, UploadFile, File, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from .good_conduct_certificate_model import GoodConductCertificate
from .good_conduct_certificate_schemas import GoodConductCertificateCreate, GoodConductCertificateRead
from datetime import datetime
import shutil
import os
from fastapi import Request
from fastapi.responses import FileResponse
from barcode import Code39
from barcode.writer import ImageWriter
from location_management.models import District, Taluka, GramPanchayat
import time
router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/good-conduct", response_model=GoodConductCertificateRead, status_code=status.HTTP_201_CREATED)
def create_good_conduct_certificate(
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
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_url = None
    cert = None
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    
    # Convert location fields to integers
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    cert_id = int(id) if id and id.strip() else None
    if image:
        safe_filename = image.filename.replace(' ', '_')
        # Temporarily create cert to get ID after commit
        cert = GoodConductCertificate(
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
            gram_panchayat_id=gram_panchayat_id_int,
            image_url=None
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        
        # Save image in location-based folder structure
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "good_conduct_certificates", "profiles", str(cert.id))
        else:
            image_dir = os.path.join(UPLOAD_DIR, "goodconduct", "profiles", str(cert.id))
        
        os.makedirs(image_dir, exist_ok=True)
        file_path = os.path.join(image_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        if file_path is not None:
            image_url = file_path.replace(os.sep, "/")
            setattr(cert, "image_url", image_url)
            db.commit()
            db.refresh(cert)
    else:
        cert = GoodConductCertificate(
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
            gram_panchayat_id=gram_panchayat_id_int,
            image_url=None
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
    # Generate and save barcode image in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "good_conduct_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "good_conduct_certificate_barcodes", str(cert.id))
    
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

@router.get("/good-conduct", response_model=List[GoodConductCertificateRead])
def list_good_conduct_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    query = db.query(GoodConductCertificate)
    if district_id:
        query = query.filter(GoodConductCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(GoodConductCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(GoodConductCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certificates = query.all()
    result = []
    
    for cert in certificates:
        cert_data = GoodConductCertificateRead.from_orm(cert)
        
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
        
        # Handle image URL
        image_url_val = getattr(cert, 'image_url', None)
        if image_url_val:
            if str(image_url_val).startswith("http"):
                cert_data.image_url = image_url_val
            else:
                # Construct image URL with location query parameters if available
                if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/good_conduct_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
                else:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/good_conduct_image/{cert.id}"
        else:
            cert_data.image_url = None
        
        # Handle barcode URL
        barcode_val = getattr(cert, 'barcode', None)
        if barcode_val:
            if str(barcode_val).startswith("http"):
                cert_data.barcode = barcode_val
            else:
                # Construct barcode URL with location query parameters if available
                if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                    cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/good_conduct_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
                else:
                    cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/good_conduct_barcode/{cert.id}"
        else:
            cert_data.barcode = None
        
        cert_data.gramPanchayat = gramPanchayat
        cert_data.taluka = taluka
        cert_data.jilha = jilha
        result.append(cert_data)
    
    return result

@router.put("/good-conduct/{id}", response_model=GoodConductCertificateRead)
def update_good_conduct_certificate(id: int,
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
    image: UploadFile = File(None),
    remove_image: bool = Form(False),
    db: Session = Depends(get_db)):
    cert = db.query(GoodConductCertificate).filter(GoodConductCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Certificate not found")
    
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
    # Handle image update/removal
    if remove_image and getattr(cert, 'image_url', None):
        try:
            os.remove(getattr(cert, 'image_url'))
        except Exception:
            pass
        setattr(cert, 'image_url', None)
    elif image:
        safe_filename = image.filename.replace(' ', '_')
        timestamp = int(time.time())
        filename_with_timestamp = f"{timestamp}_{safe_filename}"
        # Save image in location-based folder structure
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "good_conduct_certificates", "profiles", str(cert.id))
        else:
            image_dir = os.path.join(UPLOAD_DIR, "goodconduct", "profiles", str(cert.id))
        os.makedirs(image_dir, exist_ok=True)
        
        # Clean up old images in the directory before saving new one
        if os.path.exists(image_dir):
            for file in os.listdir(image_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    try:
                        os.remove(os.path.join(image_dir, file))
                    except Exception:
                        pass  # Continue even if deletion fails
        
        file_path = os.path.join(image_dir, filename_with_timestamp)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        if file_path is not None:
            image_url = file_path.replace(os.sep, "/")
            setattr(cert, "image_url", image_url)
        db.commit()
        db.refresh(cert)
    
    # Regenerate barcode in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "good_conduct_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "good_conduct_certificate_barcodes", str(cert.id))
    
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

@router.get("/good-conduct/{id}", response_model=GoodConductCertificateRead)
def get_good_conduct_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(GoodConductCertificate).filter(GoodConductCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Good Conduct certificate not found")
    
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
    
    cert_data = GoodConductCertificateRead.from_orm(cert)
    
    # Handle image URL
    image_url_val = getattr(cert, 'image_url', None)
    if image_url_val:
        if str(image_url_val).startswith("http"):
            cert_data.image_url = image_url_val
        else:
            # Construct image URL with location query parameters if available
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/good_conduct_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/good_conduct_image/{cert.id}"
    else:
        cert_data.image_url = None
    
    # Handle barcode URL
    barcode_val = getattr(cert, 'barcode', None)
    if barcode_val:
        if str(barcode_val).startswith("http"):
            cert_data.barcode = barcode_val
        else:
            # Construct barcode URL with location query parameters if available
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/good_conduct_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/good_conduct_barcode/{cert.id}"
    else:
        cert_data.barcode = None
    
    cert_data.gramPanchayat = gramPanchayat
    cert_data.taluka = taluka
    cert_data.jilha = jilha
    return cert_data

@router.get("/good_conduct_image/{id}")
def get_good_conduct_certificate_image(
    id: int,
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(GoodConductCertificate).filter(GoodConductCertificate.id == id).first()
    if not cert or not getattr(cert, "image_url", None):
        raise HTTPException(status_code=404, detail="Good Conduct certificate image not found")

    # If location parameters are provided, validate them
    if district_id is not None and taluka_id is not None and gram_panchayat_id is not None:
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
        if cert.district_id != district_id or cert.taluka_id != taluka_id or cert.gram_panchayat_id != gram_panchayat_id:
            raise HTTPException(status_code=404, detail="Good Conduct certificate image not found in the specified location")

        # Use location-based image path
        image_dir = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "good_conduct_certificates", "profiles", str(id))

        # If file doesn't exist in new location, check old location and migrate
        if not os.path.exists(image_dir):
            old_image_dir = os.path.join("uploaded_images", "goodconduct", "profiles", str(id))
            if os.path.exists(old_image_dir):
                os.makedirs(image_dir, exist_ok=True)
                import shutil
                for file in os.listdir(old_image_dir):
                    old_file = os.path.join(old_image_dir, file)
                    new_file = os.path.join(image_dir, file)
                    shutil.copy2(old_file, new_file)
            else:
                raise HTTPException(status_code=404, detail="Image not found")
    else:
        # Use certificate's own location data or fallback to old structure
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "good_conduct_certificates", "profiles", str(id))
        else:
            image_dir = os.path.join("uploaded_images", "goodconduct", "profiles", str(id))

        if not os.path.exists(image_dir):
            raise HTTPException(status_code=404, detail="Image not found")

    # Find the image file in the directory
    if os.path.exists(image_dir) and os.path.isdir(image_dir):
        # First, try to use the image_url from database if it points to a file in this directory
        image_url_val = getattr(cert, 'image_url', None)
        if image_url_val and not str(image_url_val).startswith("http"):
            # Extract filename from the stored path
            stored_filename = os.path.basename(image_url_val)
            stored_file_path = os.path.join(image_dir, stored_filename)
            if os.path.exists(stored_file_path):
                return FileResponse(stored_file_path, media_type="image/png")
        
        # If stored path doesn't work, fallback to finding the latest image by filename (timestamped)
        image_files = [file for file in os.listdir(image_dir) if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
        if image_files:
            latest_file = sorted(image_files, reverse=True)[0]
            return FileResponse(os.path.join(image_dir, latest_file), media_type="image/png")

    raise HTTPException(status_code=404, detail="Image file not found")
@router.get("/good_conduct_barcode/{id}")
def get_good_conduct_certificate_barcode(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(GoodConductCertificate).filter(GoodConductCertificate.id == id).first()
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
        new_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "good_conduct_certificates", "barcodes", str(id), "barcode.png")
        if os.path.exists(new_path):
            barcode_path = new_path
        else:
            # Try to migrate from old path to new path
            old_path = os.path.join(UPLOAD_DIR, "good_conduct_certificate_barcodes", str(id), "barcode.png")
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

@router.put("/good-conduct/{id}/fix-location")
def fix_good_conduct_certificate_location(
    id: int,
    district_id: int = Form(...),
    taluka_id: int = Form(...),
    gram_panchayat_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Fix location IDs for existing good conduct certificates and migrate their files"""
    cert = db.query(GoodConductCertificate).filter(GoodConductCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Good Conduct certificate not found")
    
    # Update location IDs
    cert.district_id = district_id
    cert.taluka_id = taluka_id
    cert.gram_panchayat_id = gram_panchayat_id
    
    # Migrate image file to new location
    old_image_path = os.path.join(UPLOAD_DIR, "goodconduct", "profiles", str(id))
    new_image_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "good_conduct_certificates", "profiles", str(id))
    
    if os.path.exists(old_image_path):
        os.makedirs(new_image_dir, exist_ok=True)
        for file in os.listdir(old_image_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                old_file_path = os.path.join(old_image_path, file)
                new_file_path = os.path.join(new_image_dir, file)
                shutil.copy2(old_file_path, new_file_path)
                cert.image_url = new_file_path.replace(os.sep, "/")
                break
    
    # Migrate barcode file to new location
    old_barcode_path = os.path.join(UPLOAD_DIR, "good_conduct_certificate_barcodes", str(id), "barcode.png")
    new_barcode_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "good_conduct_certificates", "barcodes", str(id))
    new_barcode_path = os.path.join(new_barcode_dir, "barcode.png")
    
    if os.path.exists(old_barcode_path):
        os.makedirs(new_barcode_dir, exist_ok=True)
        shutil.copy2(old_barcode_path, new_barcode_path)
        cert.barcode = new_barcode_path.replace(os.sep, "/")
    
    db.commit()
    db.refresh(cert)
    
    return {"message": "Location updated and files migrated successfully"}

@router.get("/good-conduct-all")
def list_all_good_conduct_certificates(db: Session = Depends(get_db)):
    """List all good conduct certificates without any filters for debugging"""
    certificates = db.query(GoodConductCertificate).all()
    
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