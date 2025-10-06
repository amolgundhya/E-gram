from fastapi import APIRouter, Depends, status, Form, UploadFile, File, HTTPException, Request, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import get_db
from .no_objection_certificate_model import NoObjectionCertificate
from .no_objection_certificate_schemas import NoObjectionCertificateCreate, NoObjectionCertificateRead
from datetime import datetime
import shutil
import os
from barcode import Code39
from barcode.writer import ImageWriter

router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/no-objection", response_model=NoObjectionCertificateRead, status_code=status.HTTP_201_CREATED)
def create_no_objection_certificate(
    id: str = Form(None),
    registration_date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_number: str = Form(...),
    adhar_number_en: str = Form(...),
    prop_gut_number: str = Form(None),
    subject: str = Form(...),
    subject_en: str = Form(...),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_url = None
    
    # Convert location fields to integers
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    cert_id = int(id) if id and id.strip() else None
    if image:
        # Always replace spaces with underscores in filename
        safe_filename = image.filename.replace(' ', '_')
        # Create cert with location IDs
        reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
        cert = NoObjectionCertificate(
            id=cert_id,
            registration_date=reg_date_obj,
            village=village,
            village_en=village_en,
            applicant_name=applicant_name,
            applicant_name_en=applicant_name_en,
            adhar_number=adhar_number,
            adhar_number_en=adhar_number_en,
            prop_gut_number=prop_gut_number,
            subject=subject,
            subject_en=subject_en,
            district_id=district_id_int,
            taluka_id=taluka_id_int,
            gram_panchayat_id=gram_panchayat_id_int,
            image_url=None
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
        # Now save image in the correct folder
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "profiles", str(cert.id))
        else:
            image_dir = os.path.join(UPLOAD_DIR, "noobjection", "profiles", str(cert.id))
        os.makedirs(image_dir, exist_ok=True)
        file_path = os.path.join(image_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = file_path.replace(os.sep, "/")
        setattr(cert, "image_url", image_url)
        db.commit()
        db.refresh(cert)
    else:
        reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
        cert = NoObjectionCertificate(
            id=cert_id,
            registration_date=reg_date_obj,
            village=village,
            village_en=village_en,
            applicant_name=applicant_name,
            applicant_name_en=applicant_name_en,
            adhar_number=adhar_number,
            adhar_number_en=adhar_number_en,
            prop_gut_number=prop_gut_number,
            subject=subject,
            subject_en=subject_en,
            district_id=district_id_int,
            taluka_id=taluka_id_int,
            gram_panchayat_id=gram_panchayat_id_int,
            image_url=None
        )
        db.add(cert)
        db.commit()
        db.refresh(cert)
    # Generate and save barcode image
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "noobjection", "barcodes", str(cert.id))
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

@router.get("/no-objection", response_model=list[NoObjectionCertificateRead])
def list_no_objection_certificates(
    district_id: int = None,
    taluka_id: int = None,
    gram_panchayat_id: int = None,
    request: Request = None,
    db: Session = Depends(get_db)
):
    query = db.query(NoObjectionCertificate)
    if district_id:
        query = query.filter(NoObjectionCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(NoObjectionCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(NoObjectionCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certs = query.all()
    result = []
    for cert in certs:
        cert_data = NoObjectionCertificateRead.from_orm(cert)
        # Add barcode_url
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/no_objection_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
        else:
            cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/no_objection_barcode/{cert.id}"
        
        # Add image_url
        image_url_val = getattr(cert, 'image_url', None)
        if image_url_val and isinstance(image_url_val, str):
            if image_url_val.startswith("http"):
                cert_data.image_url = image_url_val
            else:
                if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/no_objection_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
                else:
                    cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/no_objection_image/{cert.id}"
        else:
            cert_data.image_url = None
        
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

@router.get("/no-objection/{id}", response_model=NoObjectionCertificateRead)
def get_no_objection_certificate(id: int, request: Request, db: Session = Depends(get_db)):
    cert = db.query(NoObjectionCertificate).filter(NoObjectionCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="No Objection certificate not found")
    cert_data = NoObjectionCertificateRead.from_orm(cert)
    # Add barcode_url
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/no_objection_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    else:
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/no_objection_barcode/{cert.id}"
    
    # Add image_url as absolute URL if present
    image_url_val = getattr(cert, 'image_url', None)
    if image_url_val and isinstance(image_url_val, str):
        if image_url_val.startswith("http"):
            cert_data.image_url = image_url_val
        else:
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/no_objection_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/no_objection_image/{cert.id}"
    else:
        cert_data.image_url = None
    
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

@router.put("/no-objection/{id}", response_model=NoObjectionCertificateRead)
def update_no_objection_certificate(id: int,
    registration_date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_number: str = Form(...),
    adhar_number_en: str = Form(...),
    prop_gut_number: str = Form(None),
    subject: str = Form(...),
    subject_en: str = Form(...),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    image: UploadFile = File(None),
    remove_image: bool = Form(False),
    db: Session = Depends(get_db)):
    cert = db.query(NoObjectionCertificate).filter(NoObjectionCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="No Objection certificate not found")
    
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
    setattr(cert, "prop_gut_number", prop_gut_number)
    setattr(cert, "subject", subject)
    setattr(cert, "subject_en", subject_en)
    setattr(cert, "district_id", district_id_int)
    setattr(cert, "taluka_id", taluka_id_int)
    setattr(cert, "gram_panchayat_id", gram_panchayat_id_int)
    # Handle image update/removal
    if remove_image and cert.image_url:
        try:
            os.remove(cert.image_url)
        except Exception:
            pass
        setattr(cert, "image_url", None)
    elif image:
        # Always replace spaces with underscores in filename
        safe_filename = image.filename.replace(' ', '_')
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "profiles", str(cert.id))
        else:
            image_dir = os.path.join(UPLOAD_DIR, "noobjection", "profiles", str(cert.id))
        os.makedirs(image_dir, exist_ok=True)
        file_path = os.path.join(image_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        setattr(cert, "image_url", file_path.replace(os.sep, "/"))
    db.commit()
    db.refresh(cert)
    # Regenerate barcode
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "noobjection", "barcodes", str(cert.id))
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

@router.get("/no_objection_barcode/{id}")
def get_no_objection_certificate_barcode(
    id: int,
    district_id: int = Query(None, description="District ID"),
    taluka_id: int = Query(None, description="Taluka ID"),
    gram_panchayat_id: int = Query(None, description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Get the certificate first
    cert = db.query(NoObjectionCertificate).filter(NoObjectionCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="No Objection certificate not found")
    
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
            raise HTTPException(status_code=404, detail="No Objection certificate not found in the specified location")
        
        # Use location-based barcode path
        barcode_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "no_objection_certificates", "barcodes", str(id), "barcode.png")
    else:
        # Use certificate's own location data or fallback to old structure
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            barcode_path = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "barcodes", str(id), "barcode.png")
        else:
            barcode_path = os.path.join("uploaded_images", "noobjection", "barcodes", str(id), "barcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join("uploaded_images", "no_objection_certificate_barcodes", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(barcode_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode not found")
    
    return FileResponse(barcode_path, media_type="image/png")

@router.get("/no_objection_image/{id}")
def get_no_objection_certificate_image(
    id: int,
    district_id: int = Query(None, description="District ID"),
    taluka_id: int = Query(None, description="Taluka ID"),
    gram_panchayat_id: int = Query(None, description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Get the certificate first
    cert = db.query(NoObjectionCertificate).filter(NoObjectionCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="No Objection certificate not found")

    # ✅ If image_url is saved and file exists, directly serve it
    if cert.image_url and os.path.exists(cert.image_url):
        return FileResponse(cert.image_url, media_type="image/png")

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
            raise HTTPException(status_code=404, detail="No Objection certificate not found in the specified location")
        
        # Use location-based image path
        image_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "no_objection_certificates", "profiles", str(id))
    else:
        # Use certificate's own location data or fallback to old structure
        if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
            image_path = os.path.join("uploaded_images", str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "no_objection_certificates", "profiles", str(id))
        else:
            image_path = os.path.join("uploaded_images", "noobjection", "profiles", str(id))
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(image_path):
        old_image_path = os.path.join("uploaded_images", "noobjection", "profiles", str(id))
        if os.path.exists(old_image_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            # Copy files from old location to new location
            import shutil
            for file in os.listdir(old_image_path):
                old_file = os.path.join(old_image_path, file)
                new_file = os.path.join(image_path, file)
                shutil.copy2(old_file, new_file)
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    
    # Find the image file in the directory
    if os.path.exists(image_path) and os.path.isdir(image_path):
        for file in os.listdir(image_path):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                return FileResponse(os.path.join(image_path, file), media_type="image/png")
    
    raise HTTPException(status_code=404, detail="Image file not found")

@router.put("/no-objection-fix-location/{id}")
def fix_no_objection_certificate_location(
    id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    """Fix location data for existing No Objection certificates"""
    cert = db.query(NoObjectionCertificate).filter(NoObjectionCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="No Objection certificate not found")
    
    # Update location fields
    cert.district_id = district_id
    cert.taluka_id = taluka_id
    cert.gram_panchayat_id = gram_panchayat_id
    
    # Move files to correct location if they exist
    old_barcode_path = os.path.join("uploaded_images", "no_objection_certificate_barcodes", str(id), "barcode.png")
    new_barcode_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "no_objection_certificates", "barcodes", str(id), "barcode.png")
    
    if os.path.exists(old_barcode_path):
        os.makedirs(os.path.dirname(new_barcode_path), exist_ok=True)
        import shutil
        shutil.copy2(old_barcode_path, new_barcode_path)
        cert.barcode = new_barcode_path.replace(os.sep, "/")
    
    old_image_path = os.path.join("uploaded_images", "noobjection", "profiles", str(id))
    new_image_path = os.path.join("uploaded_images", str(district_id), str(taluka_id), str(gram_panchayat_id), "no_objection_certificates", "profiles", str(id))
    
    if os.path.exists(old_image_path):
        os.makedirs(new_image_path, exist_ok=True)
        import shutil
        for file in os.listdir(old_image_path):
            old_file = os.path.join(old_image_path, file)
            new_file = os.path.join(new_image_path, file)
            shutil.copy2(old_file, new_file)
        cert.image_url = new_image_path.replace(os.sep, "/")
    
    db.commit()
    db.refresh(cert)
    
    return {"message": f"Certificate {id} location updated successfully", "certificate": cert} 