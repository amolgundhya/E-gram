from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session
from database import get_db
from ..namuna8_model import Owner
from ..namuna8_apis import build_property_response
from .. import namuna8_model
from location_management import models
from typing import List

router = APIRouter()

@router.get("/owners_with_properties_by_village/")
def owners_with_properties_by_village(
    village_id: int, 
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(models.District).filter(models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    taluka = db.query(models.Taluka).filter(
        models.Taluka.id == taluka_id,
        models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    gram_panchayat = db.query(models.GramPanchayat).filter(
        models.GramPanchayat.id == gram_panchayat_id,
        models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    owners = db.query(namuna8_model.Owner).filter(namuna8_model.Owner.village_id == village_id).all()
    result = []
    for owner in owners:
        owner_dict = {
            "id": owner.id,
            "name": owner.name,
            "aadhaarNumber": owner.aadhaarNumber,
            "mobileNumber": owner.mobileNumber,
            "wifeName": owner.wifeName,
            "occupantName": owner.occupantName,
            "ownerPhoto": owner.ownerPhoto,
            "village_id": owner.village_id,
            "properties": [build_property_response(p, db, gram_panchayat_id) for p in owner.properties]
        }
        result.append(owner_dict)
    return result

# @router.delete("/owners/delete/")
# def delete_owners(owner_ids: List[int] = Body(...), db: Session = Depends(get_db)):
#     for owner_id in owner_ids:
#         owner = db.query(namuna8_model.Owner).filter(namuna8_model.Owner.id == owner_id).first()
#         if not owner:
#             continue
#         # Remove owner from all properties
#         for prop in owner.properties:
#             prop.owners = [o for o in prop.owners if o.id != owner_id]
#         db.delete(owner)
#     db.commit()
#     return {"success": True, "deleted_owner_ids": owner_ids} 


@router.delete("/owners/delete/")
def delete_owners(owner_ids: List[int] = Body(...), db: Session = Depends(get_db)):
    deleted_properties = []

    for owner_id in owner_ids:
        owner = db.query(namuna8_model.Owner).filter(
            namuna8_model.Owner.id == owner_id
        ).first()

        if not owner:
            continue

        # Collect all properties owned by this owner
        properties = list(owner.properties)

        # Delete each property
        for prop in properties:
            deleted_properties.append(prop.id)
            db.delete(prop)

        # Finally delete the owner
        db.delete(owner)

    db.commit()

    return {
        "success": True,
        "deleted_owner_ids": owner_ids,
        "deleted_property_ids": deleted_properties
    }
