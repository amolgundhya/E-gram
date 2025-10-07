from fastapi import APIRouter, Depends, status, UploadFile, File, Form, Request, HTTPException, Query
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from .resident_certificate_model import ResidentCertificate
from .resident_certificate_schemas import ResidentCertificateCreate, ResidentCertificateRead
import shutil
import os
from datetime import datetime
from barcode import Code39
from barcode.writer import ImageWriter
from location_management import models as location_models
from starlette.responses import FileResponse

router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/resident", response_model=ResidentCertificateRead, status_code=status.HTTP_201_CREATED)
def create_resident_certificate(
    id: str = Form(None),
    dispatch_no: str = Form(...),
    date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_no: str = Form(...),
    adhar_no_en: str = Form(...),
    image: UploadFile = File(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)
):
    image_url = None
    
    # Convert location fields to integers
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    
    # Create a temp cert to get the id after commit
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    cert_id = int(id) if id and id.strip() else None
    cert = ResidentCertificate(
        id=cert_id,
        dispatch_no=dispatch_no,
        date=date_obj,
        village=village,
        village_en=village_en,
        applicant_name=applicant_name,
        applicant_name_en=applicant_name_en,
        adhar_no=adhar_no,
        adhar_no_en=adhar_no_en,
        district_id=district_id_int,
        taluka_id=taluka_id_int,
        gram_panchayat_id=gram_panchayat_id_int,
        image_url=None,
        barcode=None
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    # Save image in location-based structure: uploaded_images/{district_id}/{taluka_id}/{gram_panchayat_id}/resident_certificates/profiles/{cert_id}/
    if image:
        profile_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "resident_certificates", "profiles", str(cert.id))
        os.makedirs(profile_dir, exist_ok=True)
        safe_filename = image.filename.replace(" ", "_")
        file_path = os.path.join(profile_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        cert.image_url = file_path.replace(os.sep, "/")
        db.commit()
        db.refresh(cert)
    # Generate barcode in location-based structure: uploaded_images/{district_id}/{taluka_id}/{gram_panchayat_id}/resident_certificates/barcodes/{cert_id}/
    barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "resident_certificates", "barcodes", str(cert.id))
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
    cert.barcode = barcode_path.replace(os.sep, "/")
    db.commit()
    db.refresh(cert)
    return cert

@router.get("/resident", response_model=List[ResidentCertificateRead])
def list_resident_certificates(
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
    
    query = db.query(ResidentCertificate)
    if district_id:
        query = query.filter(ResidentCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(ResidentCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(ResidentCertificate.gram_panchayat_id == gram_panchayat_id)

    certificates = query.all()

    # enrich with location names
    result = []
    for cert in certificates:
        cert_data = ResidentCertificateRead.from_orm(cert)

        district_name = None
        taluka_name = None
        gram_panchayat_name = None

        if cert.district_id:
            district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
            if district:
                district_name = getattr(district, "name", None)

        if cert.taluka_id:
            taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
            if taluka:
                taluka_name = getattr(taluka, "name", None)

        if cert.gram_panchayat_id:
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
            if gram_panchayat:
                gram_panchayat_name = getattr(gram_panchayat, "name", None)

        cert_data.jilha = district_name
        cert_data.taluka = taluka_name
        cert_data.gramPanchayat = gram_panchayat_name

        result.append(cert_data)

    return result

@router.get("/resident/{id}", response_model=ResidentCertificateRead)
def get_resident_certificate(
    id: int, 
    district_id: int = Query(None, description="Filter by district ID"),
    taluka_id: int = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: int = Query(None, description="Filter by gram panchayat ID"),
    request: Request = None, 
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
    
    query = db.query(ResidentCertificate).filter(ResidentCertificate.id == id)
    if district_id:
        query = query.filter(ResidentCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(ResidentCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(ResidentCertificate.gram_panchayat_id == gram_panchayat_id)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Resident certificate not found")
    cert_data = ResidentCertificateRead.from_orm(cert)
    # location names
    district_name = None
    taluka_name = None
    gram_panchayat_name = None
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        if district:
            district_name = getattr(district, "name", None)
    if cert.taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        if taluka:
            taluka_name = getattr(taluka, "name", None)
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        if gram_panchayat:
            gram_panchayat_name = getattr(gram_panchayat, "name", None)
    cert_data.jilha = district_name
    cert_data.taluka = taluka_name
    cert_data.gramPanchayat = gram_panchayat_name
    # Add image_url and barcode_url as absolute URLs if present
    if getattr(cert, "image_url", None):
        cert_data.image_url = str(request.base_url)[:-1] + f"/certificates/resident_image/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    else:
        cert_data.image_url = None
    if getattr(cert, "barcode", None):
        cert_data.barcode_url = str(request.base_url)[:-1] + f"/certificates/resident_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
    else:
        cert_data.barcode_url = None
    return cert_data

@router.put("/resident/{id}", response_model=ResidentCertificateRead)
def update_resident_certificate(
    id: int,
    dispatch_no: str = Form(...),
    date: str = Form(...),
    village: str = Form(...),
    village_en: str = Form(...),
    applicant_name: str = Form(...),
    applicant_name_en: str = Form(...),
    adhar_no: str = Form(...),
    adhar_no_en: str = Form(...),
    image: UploadFile = File(None),
    remove_image: str = Form(None),
    district_id: str = Form(None),
    taluka_id: str = Form(None),
    gram_panchayat_id: str = Form(None),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy if any of the three fields are provided
    district_id_int = int(district_id) if district_id and district_id.strip() else None
    taluka_id_int = int(taluka_id) if taluka_id and taluka_id.strip() else None
    gram_panchayat_id_int = int(gram_panchayat_id) if gram_panchayat_id and gram_panchayat_id.strip() else None
    
    if district_id_int is not None:
        district = db.query(location_models.District).filter(location_models.District.id == district_id_int).first()
        if not district:
            raise HTTPException(status_code=404, detail="District not found")
    
    if taluka_id_int is not None:
        if district_id_int is None:
            raise HTTPException(status_code=400, detail="District ID is required when Taluka ID is provided")
        taluka = db.query(location_models.Taluka).filter(
            location_models.Taluka.id == taluka_id_int,
            location_models.Taluka.district_id == district_id_int
        ).first()
        if not taluka:
            raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    if gram_panchayat_id_int is not None:
        if taluka_id_int is None:
            raise HTTPException(status_code=400, detail="Taluka ID is required when Gram Panchayat ID is provided")
        gram_panchayat = db.query(location_models.GramPanchayat).filter(
            location_models.GramPanchayat.id == gram_panchayat_id_int,
            location_models.GramPanchayat.taluka_id == taluka_id_int
        ).first()
        if not gram_panchayat:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    query = db.query(ResidentCertificate).filter(ResidentCertificate.id == id)
    if district_id_int:
        query = query.filter(ResidentCertificate.district_id == district_id_int)
    if taluka_id_int:
        query = query.filter(ResidentCertificate.taluka_id == taluka_id_int)
    if gram_panchayat_id_int:
        query = query.filter(ResidentCertificate.gram_panchayat_id == gram_panchayat_id_int)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Resident certificate not found")
    setattr(cert, "dispatch_no", dispatch_no)
    setattr(cert, "date", datetime.strptime(date, "%Y-%m-%d").date())
    setattr(cert, "village", village)
    setattr(cert, "village_en", village_en)
    setattr(cert, "applicant_name", applicant_name)
    setattr(cert, "applicant_name_en", applicant_name_en)
    setattr(cert, "adhar_no", adhar_no)
    setattr(cert, "adhar_no_en", adhar_no_en)
    # If a new image is uploaded, replace the old image
    if image and image.filename:
        profile_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "resident_certificates", "profiles", str(cert.id))
        os.makedirs(profile_dir, exist_ok=True)
        safe_filename = image.filename.replace(" ", "_")
        file_path = os.path.join(profile_dir, safe_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        setattr(cert, "image_url", file_path.replace(os.sep, "/"))
    # If remove_image is true, delete the image file and clear image_url
    if remove_image and remove_image.lower() == "true":
        if cert.image_url and os.path.exists(cert.image_url):
            try:
                os.remove(cert.image_url)
            except Exception:
                pass
        setattr(cert, "image_url", None)
    db.commit()
    db.refresh(cert)

    # Include location names in response
    cert_data = ResidentCertificateRead.from_orm(cert)
    district_name = None
    taluka_name = None
    gram_panchayat_name = None
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        if district:
            district_name = getattr(district, "name", None)
    if cert.taluka_id:
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        if taluka:
            taluka_name = getattr(taluka, "name", None)
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        if gram_panchayat:
            gram_panchayat_name = getattr(gram_panchayat, "name", None)
    cert_data.jilha = district_name
    cert_data.taluka = taluka_name
    cert_data.gramPanchayat = gram_panchayat_name
    return cert_data 

@router.get("/resident_image/{id}")
def get_resident_certificate_image(
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
    cert = db.query(ResidentCertificate).filter(
        ResidentCertificate.id == id,
        ResidentCertificate.district_id == district_id,
        ResidentCertificate.taluka_id == taluka_id,
        ResidentCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert or not getattr(cert, "image_url", None):
        raise HTTPException(status_code=404, detail="Resident certificate image not found in the specified location")
    
    # Use location-based image path
    image_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "resident_certificates", "profiles", str(id))
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(image_path):
        old_image_path = os.path.join(UPLOAD_DIR, "ResidentCertificates", "profiles", str(id))
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

@router.get("/resident_barcode/{id}")
def get_resident_certificate_barcode(
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
    cert = db.query(ResidentCertificate).filter(
        ResidentCertificate.id == id,
        ResidentCertificate.district_id == district_id,
        ResidentCertificate.taluka_id == taluka_id,
        ResidentCertificate.gram_panchayat_id == gram_panchayat_id
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Resident certificate not found in the specified location")
    
    # Use location-based barcode path
    barcode_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "resident_certificates", "barcodes", str(id), "barcode.png")
    
    # If file doesn't exist in new location, check old location and migrate
    if not os.path.exists(barcode_path):
        old_barcode_path = os.path.join(UPLOAD_DIR, "ResidentCertificates", "barcodes", str(id), "barcode.png")
        if os.path.exists(old_barcode_path):
            # Create new directory structure
            os.makedirs(os.path.dirname(barcode_path), exist_ok=True)
            # Copy file from old location to new location
            import shutil
            shutil.copy2(old_barcode_path, barcode_path)
        else:
            raise HTTPException(status_code=404, detail="Barcode not found")
    
    return FileResponse(barcode_path, media_type="image/png") 