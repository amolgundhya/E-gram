from fastapi import APIRouter, Depends, status, Form, Request, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from .marriage_certificate_model import MarriageCertificate
from .marriage_certificate_schemas import MarriageCertificateCreate, MarriageCertificateRead
from datetime import datetime
import os
import shutil
from barcode import Code39
from barcode.writer import ImageWriter
import qrcode
from location_management import models as location_models
from fastapi.responses import FileResponse

router = APIRouter(prefix="/certificates", tags=["certificates"])

UPLOAD_DIR = "uploaded_images"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def _build_marriage_qrcode_url(request: Request, cert: MarriageCertificate, qr_path: str) -> str:
    version = int(os.path.getmtime(qr_path))
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        return (
            str(request.base_url)[:-1]
            + f"/certificates/marriage_qrcode/{cert.id}"
            + f"?district_id={cert.district_id}&taluka_id={cert.taluka_id}"
            + f"&gram_panchayat_id={cert.gram_panchayat_id}&v={version}"
        )
    return str(request.base_url)[:-1] + f"/certificates/marriage_qrcode/{cert.id}?v={version}"

@router.post("/marriage", response_model=MarriageCertificateRead, status_code=status.HTTP_201_CREATED)
def create_marriage_certificate(
    id: int = Form(...),
    registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    husband_name: str = Form(None),
    husband_name_en: str = Form(None),
    husband_adhar: str = Form(None),
    husband_adhar_en: str = Form(None),
    husband_address: str = Form(None),
    husband_address_en: str = Form(None),
    wife_name: str = Form(None),
    wife_name_en: str = Form(None),
    wife_adhar: str = Form(None),
    wife_adhar_en: str = Form(None),
    wife_address: str = Form(None),
    wife_address_en: str = Form(None),
    marriage_date: str = Form(...),
    marriage_register_no: str = Form(None),
    marriage_register_subno: str = Form(None),
    marriage_place: str = Form(None),
    marriage_place_en: str = Form(None),
    remark: str = Form(None),
    remark_en: str = Form(None),
    district_id: int = Form(None),
    taluka_id: int = Form(None),
    gram_panchayat_id: int = Form(None),
    db: Session = Depends(get_db)
):
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    marriage_date_obj = datetime.strptime(marriage_date, "%Y-%m-%d").date()
    cert = MarriageCertificate(
        id=id,
        registration_date=reg_date_obj,
        village=village,
        village_en=village_en,
        husband_name=husband_name,
        husband_name_en=husband_name_en,
        husband_adhar=husband_adhar,
        husband_adhar_en=husband_adhar_en,
        husband_address=husband_address,
        husband_address_en=husband_address_en,
        wife_name=wife_name,
        wife_name_en=wife_name_en,
        wife_adhar=wife_adhar,
        wife_adhar_en=wife_adhar_en,
        wife_address=wife_address,
        wife_address_en=wife_address_en,
        marriage_date=marriage_date_obj,
        marriage_register_no=marriage_register_no,
        marriage_register_subno=marriage_register_subno,
        marriage_place=marriage_place,
        marriage_place_en=marriage_place_en,
        remark=remark,
        remark_en=remark_en,
        district_id=district_id,
        taluka_id=taluka_id,
        gram_panchayat_id=gram_panchayat_id
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    
    # Generate and save barcode image in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "marriage_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "marriage_certificates", "barcodes", str(cert.id))
    
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
    setattr(cert, 'barcode', barcode_path.replace(os.sep, "/"))
    
    # Generate and save QR code image in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        qrcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "marriage_certificates", "qrcodes", str(cert.id))
    else:
        qrcode_dir = os.path.join(UPLOAD_DIR, "marriage_certificates", "qrcodes", str(cert.id))
    
    os.makedirs(qrcode_dir, exist_ok=True)
    qrcode_path = os.path.join(qrcode_dir, "qrcode.png")
    qr_data = f"srno: {cert.id}\nreg date: {cert.registration_date}\nmarriage date: {cert.marriage_date}\nhusband name: {cert.husband_name_en or ''}\nwife name: {cert.wife_name_en or ''}\nmarriage place: {cert.marriage_place_en or ''}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    with open(qrcode_path, "wb") as f:
        img.save(f)
    setattr(cert, 'qrcode', qrcode_path.replace(os.sep, "/"))
    db.commit()
    db.refresh(cert)
    return cert

@router.get("/marriage", response_model=list[MarriageCertificateRead])
def list_marriage_certificates(
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
    
    query = db.query(MarriageCertificate)
    
    # Apply location filters if provided
    if district_id:
        query = query.filter(MarriageCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(MarriageCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(MarriageCertificate.gram_panchayat_id == gram_panchayat_id)
    
    certificates = query.all()
    result = []
    
    for cert in certificates:
        cert_data = MarriageCertificateRead.from_orm(cert)
        
        # Fetch location names
        gramPanchayat = None
        taluka = None
        jilha = None
        
        if cert.district_id:
            district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
            gramPanchayat = district.name if district else None
        if cert.taluka_id:
            taluka_obj = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
            taluka = taluka_obj.name if taluka_obj else None
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
            jilha = gram_panchayat.name if gram_panchayat else None
        
        # Handle barcode URL
        barcode_val = getattr(cert, 'barcode', None)
        if barcode_val:
            if str(barcode_val).startswith("http"):
                cert_data.barcode = barcode_val
            else:
                # Construct barcode URL with location query parameters if available
                if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                    cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
                else:
                    cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}"
        else:
            cert_data.barcode = None
        
        # Handle QR code URL
        qrcode_val = getattr(cert, 'qrcode', None)
        if qrcode_val:
            if str(qrcode_val).startswith("http"):
                cert_data.qrcode = qrcode_val
            else:
                # Construct QR code URL with location query parameters if available
                cert_data.qrcode = _build_marriage_qrcode_url(request, cert, qrcode_val) if os.path.exists(qrcode_val) else None
        else:
            cert_data.qrcode = None
        
        cert_data.gramPanchayat = gramPanchayat
        cert_data.taluka = taluka
        cert_data.jilha = jilha
        result.append(cert_data)
    
    return result

@router.get("/marriage/{id}", response_model=MarriageCertificateRead)
def get_marriage_certificate(
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
    
    query = db.query(MarriageCertificate).filter(MarriageCertificate.id == id)
    if district_id:
        query = query.filter(MarriageCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(MarriageCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(MarriageCertificate.gram_panchayat_id == gram_panchayat_id)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Marriage certificate not found")
    
    # Fetch location names
    gramPanchayat = None
    taluka = None
    jilha = None
    
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        gramPanchayat = district.name if district else None
    if cert.taluka_id:
        taluka_obj = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        taluka = taluka_obj.name if taluka_obj else None
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        jilha = gram_panchayat.name if gram_panchayat else None
    
    cert_data = MarriageCertificateRead.from_orm(cert)
    
    # Handle barcode URL
    barcode_val = getattr(cert, 'barcode', None)
    if barcode_val:
        if str(barcode_val).startswith("http"):
            cert_data.barcode = barcode_val
        else:
            # Construct barcode URL with location query parameters if available
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}"
    else:
        cert_data.barcode = None
    
    # Handle QR code URL
    qrcode_val = getattr(cert, 'qrcode', None)
    if qrcode_val:
        if str(qrcode_val).startswith("http"):
            cert_data.qrcode = qrcode_val
        else:
            # Construct QR code URL with location query parameters if available
            cert_data.qrcode = _build_marriage_qrcode_url(request, cert, qrcode_val) if os.path.exists(qrcode_val) else None
    else:
        cert_data.qrcode = None
    
    cert_data.gramPanchayat = gramPanchayat
    cert_data.taluka = taluka
    cert_data.jilha = jilha
    return cert_data

@router.get("/marriage_barcode/{id}")
def get_marriage_certificate_barcode(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(MarriageCertificate).filter(MarriageCertificate.id == id).first()
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
        new_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "marriage_certificates", "barcodes", str(id), "barcode.png")
        if os.path.exists(new_path):
            barcode_path = new_path
        else:
            # Try to migrate from old path to new path
            old_path = os.path.join(UPLOAD_DIR, "marriage_certificates", "barcode", str(id), "barcode.png")
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

@router.get("/marriage_qrcode/{id}")
def get_marriage_certificate_qrcode(
    id: int, 
    district_id: int = Query(None),
    taluka_id: int = Query(None),
    gram_panchayat_id: int = Query(None),
    db: Session = Depends(get_db)
):
    cert = db.query(MarriageCertificate).filter(MarriageCertificate.id == id).first()
    if not cert or not getattr(cert, "qrcode", None):
        raise HTTPException(status_code=404, detail="QR code not found")
    
    qrcode_path = getattr(cert, "qrcode", None)
    
    # If location parameters are provided, validate them
    if district_id is not None and taluka_id is not None and gram_panchayat_id is not None:
        if (cert.district_id != district_id or 
            cert.taluka_id != taluka_id or 
            cert.gram_panchayat_id != gram_panchayat_id):
            raise HTTPException(status_code=400, detail="Location parameters do not match certificate location")
        
        # Check if file exists in new location-based path
        new_path = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "marriage_certificates", "qrcodes", str(id), "qrcode.png")
        if os.path.exists(new_path):
            qrcode_path = new_path
        else:
            # Try to migrate from old path to new path
            old_path = os.path.join(UPLOAD_DIR, "marriage_certificates", "qrcode", str(id), "qrcode.png")
            if os.path.exists(old_path):
                os.makedirs(os.path.dirname(new_path), exist_ok=True)
                shutil.copy2(old_path, new_path)
                qrcode_path = new_path
                # Update the database record
                setattr(cert, "qrcode", new_path.replace(os.sep, "/"))
                db.commit()
    
    if not qrcode_path or not os.path.exists(qrcode_path):
        raise HTTPException(status_code=404, detail="QR code file not found")
    
    return FileResponse(
        qrcode_path,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

@router.put("/marriage/{id}/fix-location")
def fix_marriage_certificate_location(
    id: int,
    district_id: int = Form(...),
    taluka_id: int = Form(...),
    gram_panchayat_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Fix location IDs for existing marriage certificates and migrate their files"""
    cert = db.query(MarriageCertificate).filter(MarriageCertificate.id == id).first()
    if not cert:
        raise HTTPException(status_code=404, detail="Marriage certificate not found")
    
    # Update location IDs
    cert.district_id = district_id
    cert.taluka_id = taluka_id
    cert.gram_panchayat_id = gram_panchayat_id
    
    # Migrate barcode file to new location
    old_barcode_path = os.path.join(UPLOAD_DIR, "marriage_certificates", "barcode", str(id), "barcode.png")
    new_barcode_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "marriage_certificates", "barcodes", str(id))
    new_barcode_path = os.path.join(new_barcode_dir, "barcode.png")
    
    if os.path.exists(old_barcode_path):
        os.makedirs(new_barcode_dir, exist_ok=True)
        shutil.copy2(old_barcode_path, new_barcode_path)
        cert.barcode = new_barcode_path.replace(os.sep, "/")
    
    # Migrate QR code file to new location
    old_qrcode_path = os.path.join(UPLOAD_DIR, "marriage_certificates", "qrcode", str(id), "qrcode.png")
    new_qrcode_dir = os.path.join(UPLOAD_DIR, str(district_id), str(taluka_id), str(gram_panchayat_id), "marriage_certificates", "qrcodes", str(id))
    new_qrcode_path = os.path.join(new_qrcode_dir, "qrcode.png")
    
    if os.path.exists(old_qrcode_path):
        os.makedirs(new_qrcode_dir, exist_ok=True)
        shutil.copy2(old_qrcode_path, new_qrcode_path)
        cert.qrcode = new_qrcode_path.replace(os.sep, "/")
    
    db.commit()
    db.refresh(cert)
    
    return {"message": "Location updated and files migrated successfully"}

@router.get("/marriage-all")
def list_all_marriage_certificates(db: Session = Depends(get_db)):
    """List all marriage certificates without any filters for debugging"""
    certificates = db.query(MarriageCertificate).all()
    
    # Add location names for debugging
    for cert in certificates:
        if cert.district_id:
            district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
            cert.gramPanchayat = district.name if district else None
        if cert.taluka_id:
            taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
            cert.taluka = taluka.name if taluka else None
        if cert.gram_panchayat_id:
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
            cert.jilha = gram_panchayat.name if gram_panchayat else None
    
    return certificates

@router.put("/marriage/{id}", response_model=MarriageCertificateRead)
def update_marriage_certificate(
    id: int,
    request: Request,
    registration_date: str = Form(...),
    village: str = Form(None),
    village_en: str = Form(None),
    husband_name: str = Form(None),
    husband_name_en: str = Form(None),
    husband_adhar: str = Form(None),
    husband_adhar_en: str = Form(None),
    husband_address: str = Form(None),
    husband_address_en: str = Form(None),
    wife_name: str = Form(None),
    wife_name_en: str = Form(None),
    wife_adhar: str = Form(None),
    wife_adhar_en: str = Form(None),
    wife_address: str = Form(None),
    wife_address_en: str = Form(None),
    marriage_date: str = Form(...),
    marriage_register_no: str = Form(None),
    marriage_register_subno: str = Form(None),
    marriage_place: str = Form(None),
    marriage_place_en: str = Form(None),
    remark: str = Form(None),
    remark_en: str = Form(None),
    district_id: int = Form(None),
    taluka_id: int = Form(None),
    gram_panchayat_id: int = Form(None),
    db: Session = Depends(get_db)):
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
    
    query = db.query(MarriageCertificate).filter(MarriageCertificate.id == id)
    if district_id:
        query = query.filter(MarriageCertificate.district_id == district_id)
    if taluka_id:
        query = query.filter(MarriageCertificate.taluka_id == taluka_id)
    if gram_panchayat_id:
        query = query.filter(MarriageCertificate.gram_panchayat_id == gram_panchayat_id)
    
    cert = query.first()
    if not cert:
        raise HTTPException(status_code=404, detail="Marriage certificate not found")
    reg_date_obj = datetime.strptime(registration_date, "%Y-%m-%d").date()
    marriage_date_obj = datetime.strptime(marriage_date, "%Y-%m-%d").date()
    setattr(cert, "registration_date", reg_date_obj)
    setattr(cert, "village", village)
    setattr(cert, "village_en", village_en)
    setattr(cert, "husband_name", husband_name)
    setattr(cert, "husband_name_en", husband_name_en)
    setattr(cert, "husband_adhar", husband_adhar)
    setattr(cert, "husband_adhar_en", husband_adhar_en)
    setattr(cert, "husband_address", husband_address)
    setattr(cert, "husband_address_en", husband_address_en)
    setattr(cert, "wife_name", wife_name)
    setattr(cert, "wife_name_en", wife_name_en)
    setattr(cert, "wife_adhar", wife_adhar)
    setattr(cert, "wife_adhar_en", wife_adhar_en)
    setattr(cert, "wife_address", wife_address)
    setattr(cert, "wife_address_en", wife_address_en)
    setattr(cert, "marriage_date", marriage_date_obj)
    setattr(cert, "marriage_register_no", marriage_register_no)
    setattr(cert, "marriage_register_subno", marriage_register_subno)
    setattr(cert, "marriage_place", marriage_place)
    setattr(cert, "marriage_place_en", marriage_place_en)
    setattr(cert, "remark", remark)
    setattr(cert, "remark_en", remark_en)
    setattr(cert, "district_id", district_id)
    setattr(cert, "taluka_id", taluka_id)
    setattr(cert, "gram_panchayat_id", gram_panchayat_id)
    
    # Regenerate barcode in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        barcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "marriage_certificates", "barcodes", str(cert.id))
    else:
        barcode_dir = os.path.join(UPLOAD_DIR, "marriage_certificates", "barcodes", str(cert.id))
    
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
    setattr(cert, 'barcode', barcode_path.replace(os.sep, "/"))
    
    # Regenerate QR code in location-based folder structure
    if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
        qrcode_dir = os.path.join(UPLOAD_DIR, str(cert.district_id), str(cert.taluka_id), str(cert.gram_panchayat_id), "marriage_certificates", "qrcodes", str(cert.id))
    else:
        qrcode_dir = os.path.join(UPLOAD_DIR, "marriage_certificates", "qrcodes", str(cert.id))
    
    os.makedirs(qrcode_dir, exist_ok=True)
    qrcode_path = os.path.join(qrcode_dir, "qrcode.png")
    qr_data = f"srno: {cert.id}\nreg date: {cert.registration_date}\nmarriage date: {cert.marriage_date}\nhusband name: {cert.husband_name_en or ''}\nwife name: {cert.wife_name_en or ''}\nmarriage place: {cert.marriage_place_en or ''}"
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    with open(qrcode_path, "wb") as f:
        img.save(f)
    setattr(cert, 'qrcode', qrcode_path.replace(os.sep, "/"))
    db.commit()
    db.refresh(cert)
    
    # Fetch location names
    gramPanchayat = None
    taluka = None
    jilha = None
    
    if cert.district_id:
        district = db.query(location_models.District).filter(location_models.District.id == cert.district_id).first()
        gramPanchayat = district.name if district else None
    if cert.taluka_id:
        taluka_obj = db.query(location_models.Taluka).filter(location_models.Taluka.id == cert.taluka_id).first()
        taluka = taluka_obj.name if taluka_obj else None
    if cert.gram_panchayat_id:
        gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == cert.gram_panchayat_id).first()
        jilha = gram_panchayat.name if gram_panchayat else None
    
    cert_data = MarriageCertificateRead.from_orm(cert)
    
    # Handle barcode URL
    barcode_val = getattr(cert, 'barcode', None)
    if barcode_val:
        if str(barcode_val).startswith("http"):
            cert_data.barcode = barcode_val
        else:
            # Construct barcode URL with location query parameters if available
            if cert.district_id and cert.taluka_id and cert.gram_panchayat_id:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}?district_id={cert.district_id}&taluka_id={cert.taluka_id}&gram_panchayat_id={cert.gram_panchayat_id}"
            else:
                cert_data.barcode = str(request.base_url)[:-1] + f"/certificates/marriage_barcode/{cert.id}"
    else:
        cert_data.barcode = None
    
    # Handle QR code URL
    qrcode_val = getattr(cert, 'qrcode', None)
    if qrcode_val:
        if str(qrcode_val).startswith("http"):
            cert_data.qrcode = qrcode_val
        else:
            # Construct QR code URL with location query parameters if available
            cert_data.qrcode = _build_marriage_qrcode_url(request, cert, qrcode_val) if os.path.exists(qrcode_val) else None
    else:
        cert_data.qrcode = None
    
    cert_data.gramPanchayat = gramPanchayat
    cert_data.taluka = taluka
    cert_data.jilha = jilha
    return cert_data 