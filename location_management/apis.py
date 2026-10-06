import os
import bcrypt
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from . import models, schemas, helpers

router = APIRouter(prefix="/location", tags=["Location Management"])

# ==================== DISTRICT APIs ====================

@router.get("/districts", response_model=List[schemas.DistrictRead])
def get_all_districts(db: Session = Depends(get_db)):
    """Get all districts"""
    districts = db.query(models.District).all()
    return districts

# --- Update the existing (single) district without ID ---
@router.put("/districts/existing", response_model=schemas.DistrictRead)
def update_existing_district(district: schemas.DistrictUpdate, db: Session = Depends(get_db)):
    """Update the only existing district (no ID in path)."""
    db_district = db.query(models.District).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")

    update_data = district.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_district, field, value)

    db.commit()
    db.refresh(db_district)
    return db_district

@router.get("/districts/{district_id}", response_model=schemas.DistrictRead)
def get_district(district_id: int, db: Session = Depends(get_db)):
    """Get a specific district by ID"""
    district = db.query(models.District).filter(models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    return district

@router.post("/districts", response_model=schemas.DistrictRead, status_code=status.HTTP_201_CREATED)
def create_district(district: schemas.DistrictCreate, db: Session = Depends(get_db)):
    """Create a new district - Only one district allowed"""
    # Check if any district already exists
    existing_district = db.query(models.District).first()
    if existing_district:
        raise HTTPException(status_code=400, detail="Only one district is allowed. Please use the existing district.")
    
    # Check if district with same name already exists
    existing_district_by_name = db.query(models.District).filter(models.District.name == district.name).first()
    if existing_district_by_name:
        raise HTTPException(status_code=400, detail="District with this name already exists")
    
    db_district = models.District(**district.dict())
    db.add(db_district)
    db.commit()
    db.refresh(db_district)
    return db_district

@router.put("/districts/{district_id}", response_model=schemas.DistrictRead)
def update_district(district_id: int, district: schemas.DistrictUpdate, db: Session = Depends(get_db)):
    """Update a district"""
    db_district = db.query(models.District).filter(models.District.id == district_id).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")
    
    update_data = district.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_district, field, value)
    
    db.commit()
    db.refresh(db_district)
    return db_district

@router.delete("/districts/{district_id}")
def delete_district(district_id: int, db: Session = Depends(get_db)):
    """Delete a district"""
    db_district = db.query(models.District).filter(models.District.id == district_id).first()
    if not db_district:
        raise HTTPException(status_code=404, detail="District not found")
    
    db.delete(db_district)
    db.commit()
    return {"message": "District deleted successfully"}

 

# ==================== TALUKA APIs ====================

@router.get("/talukas", response_model=List[schemas.TalukaRead])
def get_all_talukas(db: Session = Depends(get_db)):
    """Get all talukas"""
    talukas = db.query(models.Taluka).all()
    return talukas

@router.get("/talukas/district/{district_id}", response_model=List[schemas.TalukaRead])
def get_talukas_by_district(district_id: int, db: Session = Depends(get_db)):
    """Get all talukas for a specific district"""
    talukas = db.query(models.Taluka).filter(models.Taluka.district_id == district_id).all()
    return talukas

# --- Update the existing (single) taluka without ID ---
@router.put("/talukas/existing", response_model=schemas.TalukaRead)
def update_existing_taluka(taluka: schemas.TalukaUpdate, db: Session = Depends(get_db)):
    """Update the only existing taluka (no ID in path)."""
    db_taluka = db.query(models.Taluka).first()
    if not db_taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")

    update_data = taluka.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_taluka, field, value)

    db.commit()
    db.refresh(db_taluka)
    return db_taluka

@router.get("/talukas/{taluka_id}", response_model=schemas.TalukaRead)
def get_taluka(taluka_id: int, db: Session = Depends(get_db)):
    """Get a specific taluka by ID"""
    taluka = db.query(models.Taluka).filter(models.Taluka.id == taluka_id).first()
    if not taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    return taluka

@router.post("/talukas", response_model=schemas.TalukaRead, status_code=status.HTTP_201_CREATED)
def create_taluka(taluka: schemas.TalukaCreate, db: Session = Depends(get_db)):
    """Create a new taluka - Only one taluka allowed"""
    # Check if any taluka already exists
    existing_taluka_any = db.query(models.Taluka).first()
    if existing_taluka_any:
        raise HTTPException(status_code=400, detail="Only one taluka is allowed. Please use the existing taluka.")
    
    # Check if district exists
    district = db.query(models.District).filter(models.District.id == taluka.district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    # Check if taluka with same name in same district already exists
    existing_taluka = db.query(models.Taluka).filter(
        models.Taluka.name == taluka.name,
        models.Taluka.district_id == taluka.district_id
    ).first()
    if existing_taluka:
        raise HTTPException(status_code=400, detail="Taluka with this name already exists in this district")
    
    db_taluka = models.Taluka(**taluka.dict())
    db.add(db_taluka)
    db.commit()
    db.refresh(db_taluka)
    return db_taluka

@router.put("/talukas/{taluka_id}", response_model=schemas.TalukaRead)
def update_taluka(taluka_id: int, taluka: schemas.TalukaUpdate, db: Session = Depends(get_db)):
    """Update a taluka"""
    db_taluka = db.query(models.Taluka).filter(models.Taluka.id == taluka_id).first()
    if not db_taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    
    update_data = taluka.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_taluka, field, value)
    
    db.commit()
    db.refresh(db_taluka)
    return db_taluka

@router.delete("/talukas/{taluka_id}")
def delete_taluka(taluka_id: int, db: Session = Depends(get_db)):
    """Delete a taluka"""
    db_taluka = db.query(models.Taluka).filter(models.Taluka.id == taluka_id).first()
    if not db_taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    
    db.delete(db_taluka)
    db.commit()
    return {"message": "Taluka deleted successfully"}

 

# ==================== GRAM PANCHAYAT APIs ====================

@router.get("/gram-panchayats", response_model=List[schemas.GramPanchayatRead])
def get_all_gram_panchayats(db: Session = Depends(get_db)):
    """Get all gram panchayats"""
    gram_panchayats = db.query(models.GramPanchayat).all()
    return gram_panchayats

@router.get("/gram-panchayats/taluka/{taluka_id}", response_model=List[schemas.GramPanchayatRead])
def get_gram_panchayats_by_taluka(taluka_id: int, db: Session = Depends(get_db)):
    """Get all gram panchayats for a specific taluka"""
    gram_panchayats = db.query(models.GramPanchayat).filter(models.GramPanchayat.taluka_id == taluka_id).all()
    return gram_panchayats

# --- Update the existing (single) gram panchayat without ID ---
@router.put("/gram-panchayats/existing", response_model=schemas.GramPanchayatRead)
def update_existing_gram_panchayat(gram_panchayat: schemas.GramPanchayatUpdate, db: Session = Depends(get_db)):
    """Update the only existing gram panchayat (no ID in path)."""
    db_gp = db.query(models.GramPanchayat).first()
    if not db_gp:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")

    update_data = gram_panchayat.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_gp, field, value)

    db.commit()
    db.refresh(db_gp)
    return db_gp

@router.get("/gram-panchayats/{gram_panchayat_id}", response_model=schemas.GramPanchayatRead)
def get_gram_panchayat(gram_panchayat_id: int, request: Request, db: Session = Depends(get_db)):
    """Get a specific gram panchayat by ID"""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    # Convert to response model
    gram_panchayat_data = schemas.GramPanchayatRead.from_orm(gram_panchayat)
    
    # Add absolute URL for image if present
    if gram_panchayat.image_url:
        if gram_panchayat.image_url.startswith("http"):
            gram_panchayat_data.image_url = gram_panchayat.image_url
        else:
            gram_panchayat_data.image_url = str(request.base_url)[:-1] + f"/{gram_panchayat.image_url}"
    
    return gram_panchayat_data

@router.post("/gram-panchayats", response_model=schemas.GramPanchayatRead, status_code=status.HTTP_201_CREATED)
def create_gram_panchayat(gram_panchayat: schemas.GramPanchayatCreate, db: Session = Depends(get_db)):
    """Create a new gram panchayat - Only one gram panchayat allowed"""
    # Check if any gram panchayat already exists
    existing_gram_panchayat_any = db.query(models.GramPanchayat).first()
    if existing_gram_panchayat_any:
        raise HTTPException(status_code=400, detail="Only one gram panchayat is allowed. Please use the existing gram panchayat.")
    
    # Check if taluka exists
    taluka = db.query(models.Taluka).filter(models.Taluka.id == gram_panchayat.taluka_id).first()
    if not taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    
    # Check if gram panchayat with same name in same taluka already exists
    existing_gram_panchayat = db.query(models.GramPanchayat).filter(
        models.GramPanchayat.name == gram_panchayat.name,
        models.GramPanchayat.taluka_id == gram_panchayat.taluka_id
    ).first()
    if existing_gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat with this name already exists in this taluka")
    
    # Calculate year slaps automatically
    current_year = datetime.now().year
    from_yearslap = f"{current_year}-{current_year + 1}"
    to_yearslap = f"{current_year + 3}-{current_year + 4}"
    
    # Create gram panchayat with calculated year slaps
    gram_panchayat_data = gram_panchayat.dict()
    gram_panchayat_data['from_yearslap'] = from_yearslap
    gram_panchayat_data['to_yearslap'] = to_yearslap
    
    db_gram_panchayat = models.GramPanchayat(**gram_panchayat_data)
    db.add(db_gram_panchayat)
    db.commit()
    db.refresh(db_gram_panchayat)
    return db_gram_panchayat

@router.put("/gram-panchayats/{gram_panchayat_id}", response_model=schemas.GramPanchayatRead)
def update_gram_panchayat(gram_panchayat_id: int, gram_panchayat: schemas.GramPanchayatUpdate, db: Session = Depends(get_db)):
    """Update a gram panchayat"""
    db_gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not db_gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    update_data = gram_panchayat.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_gram_panchayat, field, value)
    
    db.commit()
    db.refresh(db_gram_panchayat)
    return db_gram_panchayat

@router.delete("/gram-panchayats/{gram_panchayat_id}")
def delete_gram_panchayat(gram_panchayat_id: int, db: Session = Depends(get_db)):
    """Delete a gram panchayat"""
    db_gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not db_gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    # Remove image file if exists
    if db_gram_panchayat.image_url:
        helpers.remove_gram_panchayat_image(db, gram_panchayat_id)
    
    db.delete(db_gram_panchayat)
    db.commit()
    return {"message": "Gram Panchayat deleted successfully"}

 


# ==================== GRAM PANCHAYAT IMAGE APIs ====================

@router.post("/gram-panchayats/{gram_panchayat_id}/image", response_model=schemas.GramPanchayatRead)
def upload_gram_panchayat_image(
    gram_panchayat_id: int,
    image: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Upload image for a gram panchayat"""
    # Check if gram panchayat exists
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    # Validate image file
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Remove existing image if any
        if gram_panchayat.image_url:
            helpers.remove_gram_panchayat_image(db, gram_panchayat_id)
        
        # Save new image
        image_path = helpers.save_gram_panchayat_image(db, gram_panchayat_id, image)
        
        # Update database
        gram_panchayat.image_url = image_path
        db.commit()
        db.refresh(gram_panchayat)
        
        # Convert to response model
        gram_panchayat_data = schemas.GramPanchayatRead.from_orm(gram_panchayat)
        
        # Add absolute URL for image
        if request:
            gram_panchayat_data.image_url = str(request.base_url)[:-1] + f"/{image_path}"
        
        return gram_panchayat_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")


@router.put("/gram-panchayats/{gram_panchayat_id}/image", response_model=schemas.GramPanchayatRead)
def update_gram_panchayat_image(
    gram_panchayat_id: int,
    image: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Update image for a gram panchayat"""
    # Check if gram panchayat exists
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    # Validate image file
    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Remove existing image
        if gram_panchayat.image_url:
            helpers.remove_gram_panchayat_image(db, gram_panchayat_id)
        
        # Save new image
        image_path = helpers.save_gram_panchayat_image(db, gram_panchayat_id, image)
        
        # Update database
        gram_panchayat.image_url = image_path
        db.commit()
        db.refresh(gram_panchayat)
        
        # Convert to response model
        gram_panchayat_data = schemas.GramPanchayatRead.from_orm(gram_panchayat)
        
        # Add absolute URL for image
        if request:
            gram_panchayat_data.image_url = str(request.base_url)[:-1] + f"/{image_path}"
        
        return gram_panchayat_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update image: {str(e)}")


@router.delete("/gram-panchayats/{gram_panchayat_id}/image")
def remove_gram_panchayat_image(gram_panchayat_id: int, db: Session = Depends(get_db)):
    """Remove image from a gram panchayat"""
    # Check if gram panchayat exists
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    if not gram_panchayat.image_url:
        raise HTTPException(status_code=404, detail="No image found for this gram panchayat")
    
    try:
        # Remove image file
        if helpers.remove_gram_panchayat_image(db, gram_panchayat_id):
            # Update database
            gram_panchayat.image_url = None
            db.commit()
            return {"message": "Image removed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to remove image file")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to remove image: {str(e)}")


@router.get("/gram-panchayats/{gram_panchayat_id}/image")
def serve_gram_panchayat_image(
    gram_panchayat_id: int, 
    district_id: int = None,
    taluka_id: int = None,
    db: Session = Depends(get_db)
):
    """Serve gram panchayat image with optional district and taluka validation"""
    # Get image path
    image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Optional validation: Check if the gram panchayat belongs to the specified district and taluka
    if district_id is not None or taluka_id is not None:
        gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
        if not gram_panchayat:
            raise HTTPException(status_code=404, detail="Gram Panchayat not found")
        
        # Validate taluka_id if provided
        if taluka_id is not None and gram_panchayat.taluka_id != taluka_id:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
        
        # Validate district_id if provided
        if district_id is not None:
            taluka = db.query(models.Taluka).filter(models.Taluka.id == gram_panchayat.taluka_id).first()
            if not taluka or taluka.district_id != district_id:
                raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified district")
    
    return FileResponse(image_path)


@router.get("/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image")
def serve_gram_panchayat_image_with_path_params(
    district_id: int,
    taluka_id: int,
    gram_panchayat_id: int,
    db: Session = Depends(get_db)
):
    """Serve gram panchayat image with district, taluka, and gram panchayat validation"""
    # Get image path
    image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Validate that the gram panchayat belongs to the specified district and taluka
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    
    # Validate taluka_id
    if gram_panchayat.taluka_id != taluka_id:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    
    # Validate district_id
    taluka = db.query(models.Taluka).filter(models.Taluka.id == taluka_id).first()
    if not taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    
    if taluka.district_id != district_id:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")

    return FileResponse(image_path)


# ==================== घर कर / पाणी कर BANK SCANNER (QR) APIs ====================
# Separate from the generic gram panchayat logo/image above - a GP may
# collect house tax and water tax into different bank accounts, so each
# gets its own scannable QR upload.

def _validate_qr_type(qr_type: str):
    if qr_type not in ("house", "water", "signature"):
        raise HTTPException(status_code=400, detail="qr_type must be 'house', 'water', or 'signature'")


# ---- Bank Scanner पासवर्ड (protects घर कर / पाणी कर QR + the report-visibility
# tick from being changed without the GP's own password; डिजिटल स्वाक्षरी is a
# separate feature and is intentionally NOT covered by this). ----

def _verify_bank_scanner_password(gram_panchayat: models.GramPanchayat, password: Optional[str]):
    """Raise if `password` doesn't match the GP's stored Bank Scanner password.
    428 = no password has been created yet (frontend should prompt to create one first)."""
    if not gram_panchayat.bank_scanner_password_hash:
        raise HTTPException(status_code=428, detail="Bank Scanner पासवर्ड आधी सेट करा")
    if not password or not bcrypt.checkpw(password.encode('utf-8'), gram_panchayat.bank_scanner_password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="चुकीचा पासवर्ड")


@router.get("/gram-panchayats/{gram_panchayat_id}/bank-scanner-password/status", response_model=schemas.BankScannerPasswordStatus)
def get_bank_scanner_password_status(gram_panchayat_id: int, db: Session = Depends(get_db)):
    """Whether this GP has already created a Bank Scanner password."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    return schemas.BankScannerPasswordStatus(has_password=bool(gram_panchayat.bank_scanner_password_hash))


@router.post("/gram-panchayats/{gram_panchayat_id}/bank-scanner-password")
def create_bank_scanner_password(gram_panchayat_id: int, payload: schemas.BankScannerPasswordCreate, db: Session = Depends(get_db)):
    """First-time creation of the Bank Scanner password. Refuses if one already exists (use the change endpoint instead)."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    if gram_panchayat.bank_scanner_password_hash:
        raise HTTPException(status_code=409, detail="पासवर्ड आधीच सेट केलेला आहे. बदलण्यासाठी जुना पासवर्ड वापरा.")
    if not payload.new_password or len(payload.new_password) < 4:
        raise HTTPException(status_code=400, detail="पासवर्ड किमान ४ अक्षरी असावा")

    gram_panchayat.bank_scanner_password_hash = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.commit()
    return {"success": True, "message": "Bank Scanner पासवर्ड सेट झाला"}


@router.put("/gram-panchayats/{gram_panchayat_id}/bank-scanner-password")
def change_bank_scanner_password(gram_panchayat_id: int, payload: schemas.BankScannerPasswordChange, db: Session = Depends(get_db)):
    """Change the Bank Scanner password - requires the old password."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    _verify_bank_scanner_password(gram_panchayat, payload.old_password)
    if not payload.new_password or len(payload.new_password) < 4:
        raise HTTPException(status_code=400, detail="नवीन पासवर्ड किमान ४ अक्षरी असावा")

    gram_panchayat.bank_scanner_password_hash = bcrypt.hashpw(payload.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    db.commit()
    return {"success": True, "message": "पासवर्ड बदलला"}


@router.post("/gram-panchayats/{gram_panchayat_id}/qr/{qr_type}", response_model=schemas.GramPanchayatRead)
def upload_gram_panchayat_qr(
    gram_panchayat_id: int,
    qr_type: str,
    image: UploadFile = File(...),
    password: Optional[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Upload the घर कर (house) or पाणी कर (water) Bank Scanner QR image.
    Requires the Bank Scanner password for house/water; the separate
    डिजिटल स्वाक्षरी (signature) upload is not password-protected."""
    _validate_qr_type(qr_type)
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")

    if qr_type in ("house", "water"):
        _verify_bank_scanner_password(gram_panchayat, password)

    if not image.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")

    try:
        field = helpers.QR_URL_FIELD[qr_type]
        if getattr(gram_panchayat, field):
            helpers.remove_gram_panchayat_qr_image(db, gram_panchayat_id, qr_type)

        image_path = helpers.save_gram_panchayat_qr_image(db, gram_panchayat_id, image, qr_type)
        setattr(gram_panchayat, field, image_path)
        db.commit()
        db.refresh(gram_panchayat)

        gram_panchayat_data = schemas.GramPanchayatRead.from_orm(gram_panchayat)
        if request:
            base = str(request.base_url)[:-1]
            gram_panchayat_data.house_tax_qr_url = f"{base}/{gram_panchayat.house_tax_qr_url}" if gram_panchayat.house_tax_qr_url else None
            gram_panchayat_data.water_tax_qr_url = f"{base}/{gram_panchayat.water_tax_qr_url}" if gram_panchayat.water_tax_qr_url else None
            gram_panchayat_data.signature_url = f"{base}/{gram_panchayat.signature_url}" if gram_panchayat.signature_url else None
        return gram_panchayat_data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload QR image: {str(e)}")


@router.delete("/gram-panchayats/{gram_panchayat_id}/qr/{qr_type}")
def remove_gram_panchayat_qr(gram_panchayat_id: int, qr_type: str, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Remove the घर कर or पाणी कर Bank Scanner QR image. Requires the Bank
    Scanner password for house/water; स्वाक्षरी removal is not protected."""
    _validate_qr_type(qr_type)
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")

    if qr_type in ("house", "water"):
        _verify_bank_scanner_password(gram_panchayat, password)

    field = helpers.QR_URL_FIELD[qr_type]
    if not getattr(gram_panchayat, field):
        raise HTTPException(status_code=404, detail="No QR image found for this gram panchayat")

    if helpers.remove_gram_panchayat_qr_image(db, gram_panchayat_id, qr_type):
        setattr(gram_panchayat, field, None)
        db.commit()
        return {"message": "QR image removed successfully"}
    raise HTTPException(status_code=500, detail="Failed to remove QR image file")


@router.get("/gram-panchayats/{gram_panchayat_id}/qr/{qr_type}")
def serve_gram_panchayat_qr(
    gram_panchayat_id: int,
    qr_type: str,
    district_id: int = None,
    taluka_id: int = None,
    db: Session = Depends(get_db)
):
    """Serve the घर कर or पाणी कर Bank Scanner QR image."""
    _validate_qr_type(qr_type)
    image_path = helpers.get_gram_panchayat_qr_image_path(db, gram_panchayat_id, qr_type)
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="QR image not found")

    if district_id is not None or taluka_id is not None:
        gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
        if not gram_panchayat:
            raise HTTPException(status_code=404, detail="Gram Panchayat not found")
        if taluka_id is not None and gram_panchayat.taluka_id != taluka_id:
            raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
        if district_id is not None:
            taluka = db.query(models.Taluka).filter(models.Taluka.id == gram_panchayat.taluka_id).first()
            if not taluka or taluka.district_id != district_id:
                raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified district")

    return FileResponse(image_path)


@router.put("/gram-panchayats/{gram_panchayat_id}/bank-scanner-setting", response_model=schemas.GramPanchayatRead)
def set_bank_scanner_setting(gram_panchayat_id: int, show: bool, password: Optional[str] = None, db: Session = Depends(get_db)):
    """Toggle whether the Bank Scanner QR codes should appear on नमुना-8/नमुना-9 All Report prints. Requires the Bank Scanner password."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    _verify_bank_scanner_password(gram_panchayat, password)
    gram_panchayat.show_bank_scanner_in_reports = show
    db.commit()
    db.refresh(gram_panchayat)
    return gram_panchayat