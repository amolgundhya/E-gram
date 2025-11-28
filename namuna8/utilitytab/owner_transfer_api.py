from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from ..namuna8_model import Owner, Property, ConstructionType
import os
from pydantic import BaseModel
from Utility.QRcodeGeneration import QRCodeGeneration
from namuna8.recordresponses.property_record_response import get_property_record
from namuna8.namuna8_apis import build_property_response
import qrcode
from namuna8.PropertyDocuments.property_document_model import PropertyDocument
import shutil

router = APIRouter()

class OwnerTransferRequest(BaseModel):
    from_village_id: int
    to_village_id: int
    owner_ids: List[int]
    district_id: int = None
    taluka_id: int = None
    gram_panchayat_id: int = None

# @router.post("/owners/transfer/")
# def transfer_owners(request: OwnerTransferRequest, db: Session = Depends(get_db)):
#     owners = db.query(Owner).filter(Owner.id.in_(request.owner_ids), Owner.village_id == request.from_village_id).all()
#     if not owners:
#         raise HTTPException(status_code=404, detail="No owners found for transfer.")
#     for owner in owners:
#         owner.village_id = request.to_village_id
#         # Update location fields if provided
#         if request.district_id is not None:
#             owner.district_id = request.district_id
#         if request.taluka_id is not None:
#             owner.taluka_id = request.taluka_id
#         if request.gram_panchayat_id is not None:
#             owner.gram_panchayat_id = request.gram_panchayat_id
        
#     db.commit()
#     return {"success": True, "transferred_owner_ids": [owner.id for owner in owners]} 

# @router.post("/owners/transfer/")
# def transfer_owners(request: OwnerTransferRequest, db: Session = Depends(get_db)):
#     # First get all owners to transfer
#     owners = db.query(Owner).filter(
#         Owner.id.in_(request.owner_ids), 
#         Owner.village_id == request.from_village_id
#     ).all()
    
#     if not owners:
#         raise HTTPException(status_code=404, detail="No owners found for transfer.")

#     # Get all existing anuKramank values in the target village
#     existing_anukramanks = set(
#         p.anuKramank for p in db.query(Property).filter(
#             Property.village_id == request.to_village_id
#         ).all()
#     )

#     properties = []
#     for owner in owners:
#         properties.extend(owner.properties)

#     # Update owners
#     for owner in owners:
#         owner.village_id = request.to_village_id
#         if request.district_id is not None:
#             owner.district_id = request.district_id
#         if request.taluka_id is not None:
#             owner.taluka_id = request.taluka_id
#         if request.gram_panchayat_id is not None:
#             owner.gram_panchayat_id = request.gram_panchayat_id

#     # Dictionary to track anukramank changes for reporting
#     anukramank_changes = {}
    
#     # Update properties
#     for property in properties:
#         if property.village_id == request.from_village_id:
#             # Check if anuKramank exists in target village
#             original_anukramank = property.anuKramank
#             new_anukramank = original_anukramank
            
#             # Keep incrementing until we find an unused anuKramank
#             while new_anukramank in existing_anukramanks:
#                 new_anukramank += 1
            
#             # Update the property's anuKramank if it changed
#             if new_anukramank != original_anukramank:
#                 anukramank_changes[original_anukramank] = new_anukramank
#                 property.anuKramank = new_anukramank
            
#             # Add the new anuKramank to existing set
#             existing_anukramanks.add(new_anukramank)
            
#             # Update location fields
#             property.village_id = request.to_village_id
#             if request.district_id is not None:
#                 property.district_id = request.district_id
#             if request.taluka_id is not None:
#                 property.taluka_id = request.taluka_id
#             if request.gram_panchayat_id is not None:
#                 property.gram_panchayat_id = request.gram_panchayat_id

#     db.commit()
    
#     return {
#         "success": True, 
#         "transferred_owner_ids": [owner.id for owner in owners],
#         "transferred_property_count": len(properties),
#         "anukramank_changes": anukramank_changes  # Report which anuKramank values were changed
#     }

@router.post("/owners/transfer/")
def transfer_owners(request: OwnerTransferRequest, db: Session = Depends(get_db)):
    owners = db.query(Owner).filter(
        Owner.id.in_(request.owner_ids), 
        Owner.village_id == request.from_village_id
    ).all()
    
    if not owners:
        raise HTTPException(status_code=404, detail="No owners found for transfer.")

    # Get all existing anuKramank values in the target village
    existing_anukramanks = set(
        p.anuKramank for p in db.query(Property).filter(
            Property.village_id == request.to_village_id
        ).all()
    )
    max_anukramank = max(existing_anukramanks) if existing_anukramanks else 0

    properties = []
    for owner in owners:
        properties.extend(owner.properties)

    # Update owners
    for owner in owners:
        owner.village_id = request.to_village_id
        if request.district_id is not None:
            owner.district_id = request.district_id
        if request.taluka_id is not None:
            owner.taluka_id = request.taluka_id
        if request.gram_panchayat_id is not None:
            owner.gram_panchayat_id = request.gram_panchayat_id

    # Dictionary to track anukramank changes for reporting
    anukramank_changes = {}
    
    # Update properties
    for property in properties:
        if property.village_id == request.from_village_id:
            original_anukramank = property.anuKramank
            new_anukramank = original_anukramank

            if original_anukramank in existing_anukramanks:
                max_anukramank += 1
                new_anukramank = max_anukramank

            # Update the property's anuKramank if it changed
            if new_anukramank != original_anukramank:
                anukramank_changes[original_anukramank] = new_anukramank
                property.anuKramank = new_anukramank
            # Add the new anuKramank to existing set
            existing_anukramanks.add(new_anukramank)

            # Update location fields
            property.village_id = request.to_village_id
            if request.district_id is not None:
                property.district_id = request.district_id
            if request.taluka_id is not None:
                property.taluka_id = request.taluka_id
            if request.gram_panchayat_id is not None:
                property.gram_panchayat_id = request.gram_panchayat_id
                
            # --------------------------------------
            # TRANSFER PROPERTY DOCUMENTS AS WELL
            # --------------------------------------
            docs = db.query(PropertyDocument).filter(
            PropertyDocument.property_anuKramank == original_anukramank,
            PropertyDocument.village_id == request.from_village_id
            ).all()

            for doc in docs:

                old_village = doc.village_id
                old_anu = doc.property_anuKramank

                # Update DB fields to new village + new anuKramank
                doc.village_id = request.to_village_id
                doc.property_anuKramank = new_anukramank

                # Move files (both document_image & document_path)
                for attr in ("document_image", "document_path"):
                    val = getattr(doc, attr)
                    if not val:
                        continue

                    old_abs = val if os.path.isabs(val) else os.path.join(os.getcwd(), val)
                    if not os.path.exists(old_abs):
                        continue

                    filename = os.path.basename(old_abs)

                    # NEW TARGET DIR based on new village + new anuKramank  
                    new_dir = os.path.join(
                        "uploaded_images",
                        "property_documents",
                        str(request.to_village_id),
                        str(new_anukramank)
                    )

                    os.makedirs(new_dir, exist_ok=True)
                    new_abs = os.path.join(new_dir, filename)

                    try:
                        shutil.move(old_abs, new_abs)
                    except:
                        pass

                    new_rel = os.path.relpath(new_abs, os.getcwd()).replace(os.sep, "/")
                    setattr(doc, attr, new_rel)

            if docs:
                last_doc = docs[-1]
                old_village = last_doc.village_id
                old_anu = last_doc.property_anuKramank

                # Remove old folder if empty
                old_dir = os.path.join(
                    "uploaded_images",
                    "property_documents",
                    str(old_village),
                    str(old_anu)
                )


            try:
                if os.path.exists(old_dir) and not os.listdir(old_dir):
                    os.rmdir(old_dir)
            except:
                pass


    db.commit()
    
    # Always re-generate QR for all transferred properties:
    try:
        for prop in properties:
            db_property = db.query(Property).filter(
                Property.id == prop.id
            ).first()
            if not db_property:
                continue

            record_response = get_property_record(
                db_property.anuKramank,
                db_property.village_id,
                district_id=db_property.district_id,
                taluka_id=db_property.taluka_id,
                gram_panchayat_id=db_property.gram_panchayat_id,
                db=db
            )
            owner_name = record_response.get('ownerName') or (db_property.owners[0].name if db_property.owners else "")
            wife_name = record_response.get('ownerWifeName') or (db_property.owners[0].wifeName if db_property.owners else "")
            mobile_number = record_response.get('mobileNumber')
            vpanikar_qr = record_response.get('vpanikar',0)
            totalTax_qr = record_response.get('totaltax',0)
            # electricityTax = record_response.get('electricityTax', 0)
            totalTax = totalTax_qr - vpanikar_qr
            response = build_property_response(db_property, db, db_property.gram_panchayat_id)
            totalArea = round(record_response.get('totalArea', 0) or 0, 2)
            constructionArea = sum(
                (c['length'] or 0) * (c['width'] or 0)
                for c in response.get('constructions', [])
                if not (c.get('constructionType', '').strip().startswith('खाली जागा'))
            )
            constructionArea = round(constructionArea, 2)
            openArea = round(totalArea - constructionArea, 2)

            qr_data = {
                # Marathi labels for QR display
                "मा. धा. ना.": owner_name,
                "Mal. Kr." : getattr(db_property, 'malmattaKramank', None),
                "T. A.": totalArea,
                "T. T.": totalTax
            }

            qr_dir = os.path.join(
                "uploaded_images", "qrcode",
                str(db_property.district_id),
                str(db_property.taluka_id),
                str(db_property.gram_panchayat_id),
                str(db_property.village_id),
                str(db_property.anuKramank)
            )
            os.makedirs(qr_dir, exist_ok=True)
            qr_path = os.path.join(qr_dir, "qrcode.png")
            # Remove any old QR path if exists
            old_qr_path = getattr(db_property, 'qrcode', None)
            if old_qr_path and os.path.exists(old_qr_path):
                try:
                    os.remove(old_qr_path)
                except Exception:
                    pass
            QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
            db_property.qrcode = qr_path.replace(os.sep, "/")
            db.flush()
    except Exception:
        pass
    
    return {
        "success": True, 
        "transferred_owner_ids": [owner.id for owner in owners],
        "transferred_property_count": len(properties),
        "anukramank_changes": anukramank_changes
    }