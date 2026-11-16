# Helper functions for location management database operations
import os
import shutil
from sqlalchemy.orm import Session
from typing import List, Optional
from fastapi import UploadFile
from . import models, schemas


def get_district_by_name(db: Session, name: str) -> Optional[models.District]:
    """Get district by name"""
    return db.query(models.District).filter(models.District.name == name).first()


def get_taluka_by_name_and_district(db: Session, name: str, district_id: int) -> Optional[models.Taluka]:
    """Get taluka by name and district"""
    return db.query(models.Taluka).filter(
        models.Taluka.name == name,
        models.Taluka.district_id == district_id
    ).first()


def get_gram_panchayat_by_name_and_taluka(db: Session, name: str, taluka_id: int) -> Optional[models.GramPanchayat]:
    """Get gram panchayat by name and taluka"""
    return db.query(models.GramPanchayat).filter(
        models.GramPanchayat.name == name,
        models.GramPanchayat.taluka_id == taluka_id
    ).first()


def get_districts_with_talukas(db: Session) -> List[models.District]:
    """Get all districts with their talukas"""
    return db.query(models.District).options(
        db.joinedload(models.District.talukas)
    ).all()


def get_talukas_with_gram_panchayats(db: Session) -> List[models.Taluka]:
    """Get all talukas with their gram panchayats"""
    return db.query(models.Taluka).options(
        db.joinedload(models.Taluka.gram_panchayats)
    ).all()


def get_location_hierarchy(db: Session) -> List[dict]:
    """Get complete location hierarchy for frontend"""
    districts = get_districts_with_talukas(db)
    result = []
    
    for district in districts:
        district_data = {
            "id": district.id,
            "name": district.name,
            "code": district.code,
            "talukas": []
        }
        
        for taluka in district.talukas:
            taluka_data = {
                "id": taluka.id,
                "name": taluka.name,
                "code": taluka.code,
                "district_id": taluka.district_id,
                "gram_panchayats": []
            }
            
            # Get gram panchayats for this taluka
            gram_panchayats = db.query(models.GramPanchayat).filter(
                models.GramPanchayat.taluka_id == taluka.id
            ).all()
            
            for gram_panchayat in gram_panchayats:
                taluka_data["gram_panchayats"].append({
                    "id": gram_panchayat.id,
                    "name": gram_panchayat.name,
                    "code": gram_panchayat.code,
                    "taluka_id": gram_panchayat.taluka_id
                })
            
            district_data["talukas"].append(taluka_data)
        
        result.append(district_data)
    
    return result


# Image upload helper functions
#
# ग्रामपंचायत लोगो / घर कर-पाणी कर QR / स्वाक्षरी - या फाईल्स DB सोबत
# (~/Databasessqllite/uploaded_images/...) ठेवतो, app च्या चालू फोल्डरमध्ये नाही.
# DB सगळ्या app प्रती (dev E-gram फोल्डर, installed main.exe) मिळून एकच वापरतात,
# पण आधी फाईल्स "uploaded_images/..." अशा relative path ने चालू फोल्डरमध्ये
# जात - त्यामुळे एका प्रतीतून अपलोड केलेला QR दुसऱ्या प्रतीत 404 (broken image)
# येत होता. DB मध्ये path आधीसारखाच "uploaded_images/..." साठवतो; वाचताना आधी
# DB फोल्डर, मग जुना चालू-फोल्डर path पाहतो (जुनी फाईल सापडली तर DB फोल्डरमध्ये
# copy करतो, म्हणजे पुढे सगळ्या प्रतींना दिसेल).
UPLOAD_DIR = "uploaded_images"


def _shared_root() -> str:
    from database import database_path
    return database_path


def _shared_path(stored: str) -> str:
    return os.path.join(_shared_root(), stored.replace("/", os.sep))


def resolve_stored_image_path(stored: Optional[str]) -> Optional[str]:
    """DB मधल्या "uploaded_images/..." path ची खरी फाईल शोधा (DB फोल्डर, मग चालू फोल्डर)."""
    if not stored:
        return None
    if os.path.isabs(stored):
        return stored
    shared = _shared_path(stored)
    if os.path.exists(shared):
        return shared
    legacy = os.path.abspath(stored.replace("/", os.sep))
    if os.path.exists(legacy):
        try:
            os.makedirs(os.path.dirname(shared), exist_ok=True)
            shutil.copy2(legacy, shared)
            return shared
        except Exception:
            return legacy
    return shared


def _remove_stored_image(stored: Optional[str]) -> bool:
    """DB फोल्डर आणि जुन्या चालू-फोल्डर दोन्ही ठिकाणची प्रत काढा.
    फाईल आधीच नसली तरी True - नाहीतर गहाळ फाईलचा QR कधीच काढता येत नाही."""
    if not stored:
        return False
    candidates = [stored] if os.path.isabs(stored) else [
        _shared_path(stored), os.path.abspath(stored.replace("/", os.sep))
    ]
    ok = True
    for p in candidates:
        try:
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            ok = False
    return ok


def _gp_image_dir(db: Session, gram_panchayat_id: int, *sub: str) -> str:
    """uploaded_images/{district_id}/{taluka_id}/{gram_panchayat_id}/<sub> (relative, '/' separated)."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise ValueError("Gram panchayat not found")
    taluka = db.query(models.Taluka).filter(models.Taluka.id == gram_panchayat.taluka_id).first()
    if not taluka:
        raise ValueError("Taluka not found")
    return "/".join([UPLOAD_DIR, str(taluka.district_id), str(taluka.id), str(gram_panchayat_id), *sub])


def _save_upload(rel_dir: str, image: UploadFile) -> str:
    safe_filename = os.path.basename(image.filename or "image.png").replace(' ', '_')
    stored = f"{rel_dir}/{safe_filename}"
    file_path = _shared_path(stored)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    return stored


def save_gram_panchayat_image(db: Session, gram_panchayat_id: int, image: UploadFile) -> str:
    """Save gram panchayat image and return the stored (relative) path"""
    return _save_upload(_gp_image_dir(db, gram_panchayat_id), image)


def remove_gram_panchayat_image(db: Session, gram_panchayat_id: int) -> bool:
    """Remove gram panchayat image file"""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat or not gram_panchayat.image_url:
        return False
    return _remove_stored_image(gram_panchayat.image_url)


def get_gram_panchayat_image_path(db: Session, gram_panchayat_id: int) -> Optional[str]:
    """Get gram panchayat image file path"""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat or not gram_panchayat.image_url:
        return None
    return resolve_stored_image_path(gram_panchayat.image_url)


# घर कर / पाणी कर Bank Scanner QR uploads - separate from the generic gram
# panchayat logo/image above, since a GP may collect the two taxes into
# different bank accounts and needs two distinct scannable QR codes.
QR_URL_FIELD = {
    "house": "house_tax_qr_url",
    "water": "water_tax_qr_url",
    "signature": "signature_url",
}


def save_gram_panchayat_qr_image(db: Session, gram_panchayat_id: int, image: UploadFile, qr_type: str) -> str:
    """Save the घर कर or पाणी कर Bank Scanner QR image and return the stored (relative) path."""
    return _save_upload(_gp_image_dir(db, gram_panchayat_id, f"qr_{qr_type}"), image)


def remove_gram_panchayat_qr_image(db: Session, gram_panchayat_id: int, qr_type: str) -> bool:
    """Remove the घर कर or पाणी कर Bank Scanner QR image file."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    url = getattr(gram_panchayat, QR_URL_FIELD[qr_type], None) if gram_panchayat else None
    if not url:
        return False
    return _remove_stored_image(url)


def get_gram_panchayat_qr_image_path(db: Session, gram_panchayat_id: int, qr_type: str) -> Optional[str]:
    """Get the घर कर or पाणी कर Bank Scanner QR image file path."""
    gram_panchayat = db.query(models.GramPanchayat).filter(models.GramPanchayat.id == gram_panchayat_id).first()
    url = getattr(gram_panchayat, QR_URL_FIELD[qr_type], None) if gram_panchayat else None
    return resolve_stored_image_path(url)
