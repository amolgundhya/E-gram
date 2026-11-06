import io
import os
import re
import time
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image as PILImage
from database import get_db
from namuna8.staff_model import GramPanchayatStaff
from namuna8 import staff_schemas as schemas
from namuna8 import namuna8_model
from Yadi.ReportCreationUsingJinja.yadi_xlsx_export import workbook_to_bytes

router = APIRouter(prefix="/gp_staff", tags=["gp_staff"])

# फोटो/PDF अपलोड मर्यादा - जास्त मोठ्या फाईलमुळे local storage/backup फुगू नये म्हणून.
ALLOWED_STAFF_UPLOAD_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.pdf'}
MAX_STAFF_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/", response_model=list[schemas.StaffRead])
def list_staff(gram_panchayat_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(GramPanchayatStaff).filter(
        GramPanchayatStaff.gram_panchayat_id == gram_panchayat_id
    ).order_by(GramPanchayatStaff.id).all()


# Excel export - सर्व फिल्ड + फोटो (इमेज असेल तर सेलमध्ये लहान फोटो, PDF असेल तर "PDF").
EXPORT_COLUMNS = [
    ("sr", "अ.क्र.", 7),
    ("photo", "फोटो", 14),
    ("name", "ग्रामपंचायत अधिकाऱ्याचे नांव", 30),
    ("designation", "पद", 20),
    ("mobileNumber", "मोबाईल नंबर", 16),
    ("tenure", "कार्यकाळ", 16),
    ("duration", "कालावधी", 16),
    ("email", "मेल", 26),
    ("remarks", "शेरा", 30),
]
EXPORT_PHOTO_PX = 80


def _staff_photo_for_excel(photo_path):
    """फोटो फाईल असेल तर Excel मध्ये टाकण्यासारखी लहान PNG इमेज परत करतो, नाहीतर None."""
    if not photo_path or photo_path.lower().endswith('.pdf') or not os.path.exists(photo_path):
        return None
    try:
        from openpyxl.drawing.image import Image as XLImage
        with PILImage.open(photo_path) as src:
            img = src.convert("RGB")
        img.thumbnail((EXPORT_PHOTO_PX, EXPORT_PHOTO_PX))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return XLImage(buf)
    except Exception:
        return None


@router.get("/export-xlsx")
def export_staff_xlsx(gram_panchayat_id: int = Query(...), db: Session = Depends(get_db)):
    rows = db.query(GramPanchayatStaff).filter(
        GramPanchayatStaff.gram_panchayat_id == gram_panchayat_id
    ).order_by(GramPanchayatStaff.id).all()

    # Master मध्ये सेट केलेला export पासवर्ड (गाव पंचायतीनुसार) - नसेल तर पासवर्डशिवाय export (इतर एक्सपोर्ट्स प्रमाणेच).
    password = None
    checklist = db.query(namuna8_model.Namuna8SettingChecklist).filter(
        namuna8_model.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id
    ).first()
    if checklist and getattr(checklist, 'exportPassword', None):
        password = checklist.exportPassword

    # openpyxl फक्त export वेळीच लोड (सर्व्हर स्टार्टअप जलद).
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "अधिकारी व कर्मचारी"
    thin = Side(style="thin", color="999999")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_font = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_align = Alignment(vertical="center", wrap_text=True)

    for col_idx, (_, label, width) in enumerate(EXPORT_COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=label)
        cell.font = header_font
        cell.alignment = center
        cell.border = border
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.freeze_panes = "A2"

    for sr, obj in enumerate(rows, start=1):
        row_idx = sr + 1
        for col_idx, (key, _, _) in enumerate(EXPORT_COLUMNS, start=1):
            if key == "sr":
                value = sr
            elif key == "photo":
                value = None
            else:
                value = getattr(obj, key, None) or None
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = center if key in ("sr", "photo") else cell_align
            cell.border = border

        img = _staff_photo_for_excel(obj.photo)
        if img is not None:
            ws.add_image(img, f"B{row_idx}")
            ws.row_dimensions[row_idx].height = EXPORT_PHOTO_PX * 0.75 + 6  # px -> points
        elif obj.photo and obj.photo.lower().endswith('.pdf'):
            ws.cell(row=row_idx, column=2, value="PDF")

    xlsx_bytes = workbook_to_bytes(wb, password=password)
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="gp_staff.xlsx"'},
    )


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
