# ...existing code...
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from database import get_db
from .property_document_model import PropertyDocument
from .property_document_schemas import PropertyDocumentCreate, PropertyDocumentResponse
from typing import List, Optional
import shutil
import os

router = APIRouter(prefix="/namuna8/property_documents", tags=["PropertyDocuments"])

UPLOAD_DIR = "uploaded_images/property_documents"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/", response_model=PropertyDocumentResponse)
def create_property_document(doc: PropertyDocumentCreate, db: Session = Depends(get_db)):
    # Normalize any absolute paths to relative and ensure forward slashes
    def to_rel(p):
        if not p:
            return p
        if os.path.isabs(p):
            try:
                return os.path.relpath(p, start=os.getcwd()).replace(os.sep, "/")
            except Exception:
                return p.replace(os.sep, "/")
        return p.replace(os.sep, "/")

    if getattr(doc, "document_image", None):
        doc.document_image = to_rel(doc.document_image)
    if getattr(doc, "document_path", None):
        doc.document_path = to_rel(doc.document_path)

    db_doc = PropertyDocument(**doc.dict())
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

@router.get("/", response_model=List[PropertyDocumentResponse])
def list_property_documents(property_anuKramank: int, village_id: Optional[int] = None, db: Session = Depends(get_db)):
    # Match numeric or string stored anuKramank
    q = db.query(PropertyDocument).filter(
        (PropertyDocument.property_anuKramank == property_anuKramank) |
        (PropertyDocument.property_anuKramank == str(property_anuKramank))
    )
    if village_id is not None and hasattr(PropertyDocument, "village_id"):
        q = q.filter(PropertyDocument.village_id == village_id)
    return q.all()

@router.delete("/delete/{id}")
def delete_property_document(id: int, db: Session = Depends(get_db)):
    doc = db.query(PropertyDocument).get(id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # remove files if present (document_image and document_path)
    # for attr in ("document_image", "document_path"):
    #     path_val = getattr(doc, attr, None)
    #     if not path_val:
    #         continue
    #     # resolve absolute path
    #     abs_path = path_val if os.path.isabs(path_val) else os.path.join(os.getcwd(), path_val)
    #     if os.path.exists(abs_path):
    #         try:
    #             os.remove(abs_path)
    #         except Exception:
    #             pass
    #         # try to remove parent dir if empty
    #         try:
    #             parent = os.path.dirname(abs_path)
    #             if parent.startswith(os.path.join(os.getcwd(), UPLOAD_DIR)) and not os.listdir(parent):
    #                 os.rmdir(parent)
    #         except Exception:
    #             pass

    db.delete(doc)
    db.commit()
    return {"ok": True}

@router.post("/upload_image/", response_model=str)
def upload_document_image(
    file: UploadFile = File(...),
    village_id: int = Form(...),
    property_anuKramank: int = Form(...),
):
    filename = (file.filename or "uploaded_file").replace(" ", "_")
    # build path: uploaded_images/property_documents/<village_id>/<anuKramank>/<filename>
    subdir = os.path.join(UPLOAD_DIR, str(village_id), str(property_anuKramank))
    os.makedirs(subdir, exist_ok=True)
    file_location = os.path.join(subdir, filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    # return relative path using forward slashes
    rel_path = os.path.relpath(file_location, start=os.getcwd()).replace(os.sep, "/")
    return rel_path
# ...existing code...