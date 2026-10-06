import os
import re
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from database import get_db
from namuna8.staff_model import GramPanchayatStaff
from namuna8 import staff_schemas as schemas

router = APIRouter(prefix="/gp_staff", tags=["gp_staff"])

# फोटो/PDF अपलोड मर्यादा - जास्त मोठ्या फाईलमुळे local storage/backup फुगू नये म्हणून.
ALLOWED_STAFF_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
MAX_STAFF_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/", response_model=list[schemas.StaffRead])
def list_staff(gram_panchayat_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(GramPanchayatStaff).filter(
        GramPanchayatStaff.gram_panchayat_id == gram_panchayat_id
    ).order_by(GramPanchayatStaff.id).all()


@router.post("/", response_model=schemas.StaffRead)
def create_staff(data: schemas.StaffCreate, db: Session = Depends(get_db)):
    obj = GramPanchayatStaff(**data.dict())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.put("/{staff_id}", response_model=schemas.StaffRead)
def update_staff(staff_id: int, data: schemas.StaffUpdate, db: Session = Depends(get_db)):
    obj = db.query(GramPanchayatStaff).filter(GramPanchayatStaff.id == staff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Staff not found")
    for k, v in data.dict(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{staff_id}")
def delete_staff(staff_id: int, db: Session = Depends(get_db)):
    obj = db.query(GramPanchayatStaff).filter(GramPanchayatStaff.id == staff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Staff not found")
    if obj.photo and os.path.exists(obj.photo):
        try:
            os.remove(obj.photo)
        except Exception:
            pass
    db.delete(obj)
    db.commit()
    return {"message": "Staff deleted successfully"}


@router.post("/upload_photo/", response_model=str)
def upload_staff_photo(staff_id: int = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    obj = db.query(GramPanchayatStaff).filter(GramPanchayatStaff.id == staff_id).first()
    if not obj:
        raise HTTPException(status_code=400, detail="Staff not found")

    ext = (os.path.splitext(file.filename)[1] if file.filename else '').lower()
    if ext not in ALLOWED_STAFF_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="फक्त JPG, JPEG, PNG किंवा PDF फाईल अपलोड करता येईल.")

    contents = file.file.read()
    if len(contents) > MAX_STAFF_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="फाईलचा आकार 5 MB पेक्षा जास्त असू नये.")

    image_dir = os.path.join(
        "uploaded_images", "staff",
        str(obj.district_id), str(obj.taluka_id), str(obj.gram_panchayat_id), str(staff_id)
    )
    os.makedirs(image_dir, exist_ok=True)

    staffname = re.sub(r'[^\w\-_]', '_', obj.name) if obj.name else f"staff_{staff_id}"
    timestamp = int(time.time())
    filename = f"{staffname}_{timestamp}{ext}"
    file_path = os.path.join(image_dir, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    file_location = file_path.replace(os.sep, '/')
    obj.photo = file_location
    db.commit()
    return file_location


@router.delete("/{staff_id}/photo")
def delete_staff_photo(staff_id: int, db: Session = Depends(get_db)):
    obj = db.query(GramPanchayatStaff).filter(GramPanchayatStaff.id == staff_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Staff not found")
    if obj.photo:
        if os.path.exists(obj.photo):
            try:
                os.remove(obj.photo)
            except Exception:
                pass
        obj.photo = None
        db.commit()
    return {"message": "Photo removed successfully"}
