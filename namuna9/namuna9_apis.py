from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import database
from namuna9 import namuna9_model, namuna9_schemas
from namuna9.namuna9settings import Namuna9Settings
from namuna9.namuna9_schemas import Namuna9SettingsCreate, Namuna9SettingsRead, Namuna9SettingsUpdate, Namuna9PropertyDataCreate, Namuna9PropertyDataUpdate, Namuna9PropertyDataRead, Namuna9BulkPropertyDataUpdate
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from sqlalchemy.exc import IntegrityError
from namuna8.namuna8_apis import build_property_response
from namuna8.recordresponses.property_record_response import get_property_record, compute_display_sr_no
from Utility.tax_rounding import round_tax_amount
from Utility.QRcodeGeneration import QRCodeGeneration
from Utility.qr_text import build_property_qr_text
from location_management import models as location_models
from natural_sort import malmatta_kramank_sort_key
import os
import logging

logging.basicConfig(
    filename="namuna9_logs.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter(
    prefix="/namuna9",
    tags=["namuna9"]
)

# Display an owner's name, with the भोगवटदार name appended when a separate
# occupant is present, e.g. "साईबाबा मंदीर देवस्थान राजापुर – भोगवटदार : शोभा".
# "स्वतः" is the default भोगवटदार value for a normal (self-occupied) owner, so it
# must not trigger the "- भोगवटदार :" suffix - only a real occupant name should.
# No brackets around the owner name (client-reported bug - see conversation
# history around 2026-09-30).
def _owner_display_name(owner: dict) -> str:
    name = owner.get('name', '') or ''
    occupant = (owner.get('occupantName') or '').strip()
    if occupant and occupant != 'स्वतः':
        return f"{name} – भोगवटदार : {occupant}"
    return name
backend_url = os.environ.get('BACKEND_URL', 'http://localhost:8000')

# दिलेल्या property साठी source_rec (मागचं वर्ष) वरून थकित मध्ये जाणारी रक्कम (शक्ती+चालू,
# घरासाठी +दंड) काढतो - get_table_data च्या थकित लॉजिकसारखीच: आधी त्या वर्षातली साठवलेली
# रो (असेल तर, युजरने भरलेली/दुरुस्त केलेली), नसेल तर सध्याच्या namuna8 वरून ताजी गणना
# (fallback - ती मालमत्ता मागच्या वर्षी कधीच उघडली नव्हती तरच). /copy-from-year
# (बदला व सेट करा) आणि get_table_data दोन्हीकडे सुसंगत राहावं म्हणून हीच पद्धत वापरतो.
def _compute_thakit_source_amounts(db: Session, source_rec, property_id: int, gram_panchayat_id):
    saved = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == source_rec.id,
        namuna9_model.Namuna9PropertyData.property_id == property_id
    ).first()
    if saved:
        return {
            'ghar': round((saved.shaktiGhar or 0) + (saved.chaluGhar or 0) + (saved.dand or 0), 2),
            'diva': round((saved.shaktiDiva or 0) + (saved.chaluDiva or 0), 2),
            'aarogyaKar': round((saved.shaktiAarogyaKar or 0) + (saved.chaluAarogyaKar or 0), 2),
            'sapanikar': round((saved.shaktiSapanikar or 0) + (saved.chaluSapanikar or 0), 2),
            'vpanikar': round((saved.shaktiVpanikar or 0) + (saved.chaluVpanikar or 0), 2),
            'cleaningTax': round((saved.shaktiCleaningTax or 0) + (saved.chaluCleaningTax or 0), 2),
        }
    prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == property_id).first()
    if not prop:
        return None
    prop_data = build_property_response(prop, db, gram_panchayat_id)
    constructions = db.query(namuna8_model.Construction).filter(
        namuna8_model.Construction.property_id == prop.id
    ).all()
    karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
    return {
        'ghar': round(0 if karLaguNahi else sum([c.houseTax or 0 for c in constructions]), 2),
        'diva': round(0 if karLaguNahi else (prop_data.get('divaKar', 0) or 0), 2),
        'aarogyaKar': round(0 if karLaguNahi else (prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0), 2),
        'sapanikar': round(0 if karLaguNahi else (prop_data.get('sapanikar', 0) or 0), 2),
        'vpanikar': round(0 if karLaguNahi else (prop_data.get('vpanikar', 0) or 0), 2),
        'cleaningTax': round(0 if karLaguNahi else (prop_data.get('cleaningTax', 0) or 0), 2),
    }


@router.post("/copy-from-year")
def copy_from_year(
    payload: dict,
    db: Session = Depends(database.get_db)
):
    """
    Copy property_ids from a source yearslap to a target yearslap for a given village,
    and update thakit fields on the target.

    Expected payload keys:
    - villageId (or village): str/int
    - fromYearslap (or from): str, e.g., "2017-2018"
    - toYearslap (or to): str, e.g., "2018-2019"
    - thakitValues (optional): str, value to set on target
    - doesThakit will always be set to True
    """
    villageId = payload.get("villageId") or payload.get("village")
    from_year = payload.get("fromYearslap") or payload.get("from")
    to_year = payload.get("toYearslap") or payload.get("to")
    thakit_values = payload.get("thakitValues") or ""
    # doesThakit will always be set to True for this API
    does_thakit_raw = True

    if not villageId or not from_year or not to_year:
        raise HTTPException(status_code=400, detail="Required fields: villageId, fromYearslap, toYearslap")
    
    def parse_yes_no(value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"yes", "true", "1", "y"}:
                return True
            if lowered in {"no", "false", "0", "n"}:
                return False
        return None

    source = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == str(villageId),
        namuna9_model.Namuna9.yearslap == from_year
    ).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source (fromYearslap) record not found for the given villageId")

    target = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == str(villageId),
        namuna9_model.Namuna9.yearslap == to_year
    ).first()
    if not target:
        raise HTTPException(status_code=404, detail="Target (toYearslap) record not found for the given villageId")

    # Copy property IDs and update thakit fields
    target.property_ids = list(source.property_ids or [])
    if thakit_values is not None:
        target.thakitValues = thakit_values
    # Always set doesThakit to True for this API
    target.doesThakit = True
    # Set thakitYear to the from_year (source year)
    target.thakitYear = from_year

    db.commit()
    db.refresh(target)

    # टार्गेट वर्षात आधीच सेव्ह झालेल्या (उघडलेल्या/संपादित) रोंचं थकित get_table_data
    # आपोआप पुन्हा काढत नाही (only "not saved_data" रोंसाठी लागू होतं) - म्हणून इथे
    # त्याच रोंनाच स्पष्टपणे अपडेट करतो. चालू/दंड/इतर वर्षांना अजिबात स्पर्श करत नाही,
    # फक्त शक्ती (+ त्यावर अवलंबून एकूण/total) बदलतो. टार्गेट वर्षात या मालमत्तेवर आधीच
    # काही भरणा (receipts) झाला असेल, तो नव्या थकितमधून वजा करतो - नाहीतर आधीच भरलेली
    # रक्कम परत थकित म्हणून दाखवली जाईल आणि बॅलन्स चुकेल.
    source_property_ids = set(source.property_ids or [])
    thakit_rows_updated = 0
    if source_property_ids:
        target_saved_rows = db.query(namuna9_model.Namuna9PropertyData).filter(
            namuna9_model.Namuna9PropertyData.namuna9_id == target.id,
            namuna9_model.Namuna9PropertyData.property_id.in_(source_property_ids)
        ).all()
        gp_id_for_fallback = getattr(target, 'gram_panchayat_id', None) or getattr(source, 'gram_panchayat_id', None)

        for row in target_saved_rows:
            source_amounts = _compute_thakit_source_amounts(db, source, row.property_id, gp_id_for_fallback)
            if source_amounts is None:
                continue

            already_collected = db.query(
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliGhar), 0.0),
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliDiva), 0.0),
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliAarogyaKar), 0.0),
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliSapanikar), 0.0),
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliVpanikar), 0.0),
                func.coalesce(func.sum(namuna9_model.Namuna9Receipt.vasuliCleaningTax), 0.0),
            ).filter(
                namuna9_model.Namuna9Receipt.namuna9_id == target.id,
                namuna9_model.Namuna9Receipt.property_id == row.property_id,
                namuna9_model.Namuna9Receipt.is_deleted == False
            ).first()
            coll_ghar, coll_diva, coll_aarogya, coll_sapani, coll_vpani, coll_clean = already_collected

            row.shaktiGhar = round(max(source_amounts['ghar'] - (coll_ghar or 0), 0), 2)
            row.shaktiDiva = round(max(source_amounts['diva'] - (coll_diva or 0), 0), 2)
            row.shaktiAarogyaKar = round(max(source_amounts['aarogyaKar'] - (coll_aarogya or 0), 0), 2)
            row.shaktiSapanikar = round(max(source_amounts['sapanikar'] - (coll_sapani or 0), 0), 2)
            row.shaktiVpanikar = round(max(source_amounts['vpanikar'] - (coll_vpani or 0), 0), 2)
            row.shaktiCleaningTax = round(max(source_amounts['cleaningTax'] - (coll_clean or 0), 0), 2)

            # शक्ती बदलल्यामुळे एकूण/total पुन्हा काढतो - चालू/दंड जसेच्या तसे ठेवतो.
            row.ekunGhar = round(max(row.shaktiGhar, 0) + max(row.chaluGhar or 0, 0) + max(row.dand or 0, 0), 2)
            row.ekunDiva = round(max(row.shaktiDiva + (row.chaluDiva or 0), 0), 2)
            row.ekunAarogyaKar = round(max(row.shaktiAarogyaKar + (row.chaluAarogyaKar or 0), 0), 2)
            row.ekunSapanikar = round(max(row.shaktiSapanikar + (row.chaluSapanikar or 0), 0), 2)
            row.ekunVpanikar = round(max(row.shaktiVpanikar + (row.chaluVpanikar or 0), 0), 2)
            row.ekunCleaningTax = round(max(row.shaktiCleaningTax + (row.chaluCleaningTax or 0), 0), 2)
            row.total = round(
                row.ekunGhar + row.ekunDiva + row.ekunAarogyaKar + row.ekunSapanikar +
                row.ekunVpanikar + row.ekunCleaningTax + (row.warrantFee or 0) + (row.noticeFee or 0),
                2
            )
            thakit_rows_updated += 1

        if thakit_rows_updated:
            db.commit()

    return {
        "message": "Copy and update successful",
        "villageId": target.villageId,
        "fromYearslap": from_year,
        "toYearslap": to_year,
        "propertyIdsCount": len(target.property_ids or []),
        "doesThakit": True,
        "thakitValues": getattr(target, "thakitValues", None),
        "thakitYear": getattr(target, "thakitYear", None),
        "thakitRowsRecalculated": thakit_rows_updated,
    }

@router.post("/", response_model=namuna9_schemas.Namuna9YearSetupRead, status_code=status.HTTP_201_CREATED)
def create_namuna9_year_setup(setup: namuna9_schemas.Namuna9YearSetupCreate, db: Session = Depends(database.get_db)):
    # Check if a record for this village and year already exists
    existing_setup = db.query(namuna9_model.Namuna9YearSetup).filter(
        namuna9_model.Namuna9YearSetup.village == setup.village,
        namuna9_model.Namuna9YearSetup.year == setup.year
    ).first()
    if existing_setup:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A record for village '{setup.village}' and year '{setup.year}' already exists."
        )
    
    db_setup = namuna9_model.Namuna9YearSetup(**setup.dict())
    db.add(db_setup)
    db.commit()
    db.refresh(db_setup)
    return db_setup

@router.get("/list", response_model=list[namuna9_schemas.Namuna9YearSetupRead])
def list_namuna9_year_setups(db: Session = Depends(database.get_db)):
    # Sorted by year then village for stable ordering
    return (
        db.query(namuna9_model.Namuna9YearSetup)
        .order_by(namuna9_model.Namuna9YearSetup.year, namuna9_model.Namuna9YearSetup.village)
        .all()
    )

@router.get("/exists")
def check_if_setup_exists(village: str, year: str, db: Session = Depends(database.get_db)):
    existing_setup = db.query(namuna9_model.Namuna9YearSetup).filter(
        namuna9_model.Namuna9YearSetup.village == village,
        namuna9_model.Namuna9YearSetup.year == year
    ).first()
    return {"exists": existing_setup is not None}

@router.post("/carry-forward")
def carry_forward_data(data: namuna9_schemas.Namuna9CarryForward, db: Session = Depends(database.get_db)):
    # This is a placeholder for the actual logic.
    # You would need to implement the business logic to:
    # 1. Find the source data from `data.from_year` for the given `data.village`.
    # 2. Select the correct values based on `data.carry_forward_option`.
    # 3. Apply these values to the `data.to_year` records for the `data.village`.
    return {"message": "Carry forward action received. Logic not yet implemented.", "data": data}

@router.delete("/")
def delete_namuna9_year_setup(village: str, year: str, db: Session = Depends(database.get_db)):
    db_record = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == village,
        namuna9_model.Namuna9.yearslap == year
    ).first()
    if not db_record:
        raise HTTPException(status_code=404, detail=f"Record for village '{village}' and year '{year}' not found")
    db.delete(db_record)
    db.commit()
    return {"message": f"Record for village '{village}' and year '{year}' deleted successfully."}

@router.post("/settings", response_model=Namuna9SettingsRead, status_code=status.HTTP_201_CREATED)
def create_namuna9_settings(settings: Namuna9SettingsCreate, db: Session = Depends(database.get_db)):
    db_settings = Namuna9Settings(**settings.dict())
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings

@router.get("/settings/{gram_panchayat_id}", response_model=Namuna9SettingsRead)
def get_namuna9_settings(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    db_settings = db.query(Namuna9Settings).filter(Namuna9Settings.gram_panchayat_id == gram_panchayat_id).first()
    if not db_settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return db_settings

@router.put("/settings/{gram_panchayat_id}", response_model=Namuna9SettingsRead)
def update_namuna9_settings(gram_panchayat_id: int, settings: Namuna9SettingsUpdate, db: Session = Depends(database.get_db)):
    db_settings = db.query(Namuna9Settings).filter(Namuna9Settings.gram_panchayat_id == gram_panchayat_id).first()
    if not db_settings:
        # Create new row if not found (upsert)
        settings_data = settings.dict(exclude_unset=True)
        settings_data['gram_panchayat_id'] = gram_panchayat_id
        new_settings = Namuna9Settings(**settings_data)
        db.add(new_settings)
        db.commit()
        db.refresh(new_settings)
        return new_settings
    for field, value in settings.dict(exclude_unset=True).items():
        setattr(db_settings, field, value)
    db.commit()
    db.refresh(db_settings)
    return db_settings 

@router.post("/create-or-carry-forward")
def create_or_carry_forward_namuna9(
    payload: dict, db: Session = Depends(database.get_db)
):
    village = payload.get("village")
    yearslap = payload.get("yearslap")
    data_source = payload.get("data_source")
    grampanchayatId = payload.get("grampanchayatId")
    if not (village and yearslap and data_source):
        raise HTTPException(status_code=400, detail="Missing required fields.")

    # Check for existing (villageId, yearslap) pair
    existing = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == village,
        namuna9_model.Namuna9.yearslap == yearslap
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A record for this village and year already exists. Please delete it first if you want to replace it.")

    if data_source == "जुना नमुना ९ मधून डाटा घेणे":
        # Find previous year
        try:
            prev_year = str(int(yearslap.split("-")[0]) - 1) + "-" + str(int(yearslap.split("-")[1]) - 1)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid yearslap format.")
        prev_records = []
        while int(prev_year.split("-")[0]) > 2000:
            prev_records = db.query(namuna9_model.Namuna9).filter(
                namuna9_model.Namuna9.villageId == village,
                namuna9_model.Namuna9.yearslap == prev_year
            ).all()
            if prev_records:
                break
            prev_year = str(int(prev_year.split("-")[0]) - 1) + "-" + str(int(prev_year.split("-")[1]) - 1)
        if not prev_records:
            raise HTTPException(status_code=404, detail="No previous Namuna9 records found for this village.")
        # Collect all property IDs from previous Namuna9 records
        prev_property_ids = set()
        for rec in prev_records:
            if getattr(rec, 'property_ids', None) and isinstance(rec.property_ids, list):
                prev_property_ids.update(rec.property_ids)
        # गावातल्या सर्व सध्याच्या मालमत्ता (Property.id ने, anuKramank ने नाही - ते वेगळं
        # असतं) मागील वर्षाच्या यादीत मिळवतो, जेणेकरून कधीही जोडलेली मालमत्ता नव्या
        # वर्षात आपोआप येईल (created_at च्या कॅलेंडर वर्षाशी काही संबंध नाही).
        current_village_property_ids = [
            p.id for p in db.query(namuna8_model.Property).filter(
                namuna8_model.Property.village_id == village
            ).all()
        ]
        # Combine all property IDs (avoid duplicates)
        all_property_ids = list(set(list(prev_property_ids) + current_village_property_ids))
        # Create new Namuna9 record for this yearslap. Also set the same
        # doesThakit/thakitValues/thakitYear fields that the separate manual
        # "Carry Forward" action (/copy-from-year) sets - without these, the
        # थकित (arrears) column never auto-populates from last year's data,
        # even though the property list itself carries forward correctly.
        # IMPORTANT: thakitValues must be one of the keys get_table_data's
        # थकित logic actually checks ("chaluGhar"/"yekun"/"thakit") - the
        # Marathi label "मागील एकूण चे" itself matches none of them, which
        # silently left थकित at 0 for every new year created this way.
        new_namuna9 = namuna9_model.Namuna9(
            yearslap=yearslap,
            villageId=village,
            grampanchayatId=grampanchayatId,
            property_ids=all_property_ids,
            doesThakit=True,
            thakitValues="yekun",
            thakitYear=prev_year
        )
        try:
            db.add(new_namuna9)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="A record for this year already exists. Please delete it first if you want to replace it.")
        return {"message": "Carry forward successful."}
    elif data_source == "नवीन बनवा":
        # Get all property IDs for the given village (ignore year)
        properties = db.query(namuna8_model.Property).filter(
            namuna8_model.Property.village_id == village
        ).all()
        property_ids = [p.id for p in properties]
        new_namuna9 = namuna9_model.Namuna9(
            yearslap=yearslap,
            villageId=village,
            grampanchayatId=grampanchayatId,
            property_ids=property_ids
        )
        try:
            db.add(new_namuna9)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="A record for this year already exists. Please delete it first if you want to replace it.")
        return {"message": "New Namuna9 record created."}
    else:
        raise HTTPException(status_code=400, detail="Invalid data_source value.") 

@router.get("/list-all")
def list_all_namuna9(db: Session = Depends(database.get_db)):
    # Sorted by yearslap then villageId for consistent output
    records = (
        db.query(namuna9_model.Namuna9)
        .order_by(namuna9_model.Namuna9.yearslap, namuna9_model.Namuna9.villageId)
        .all()
    )
    # Return as dicts for easier inspection
    return [
        {
            "id": r.id,
            "yearslap": r.yearslap,
            "villageId": r.villageId,
            "grampanchayatId": r.grampanchayatId,
            "property_ids": r.property_ids,
            "createdAt": r.createdAt,
            "updatedAt": r.updatedAt
        }
        for r in records
    ] 

@router.get("/delete-options")
def get_delete_options(db: Session = Depends(database.get_db)):
    # Get all unique villageIds and yearslaps from Namuna9
    records = db.query(namuna9_model.Namuna9).all()
    unique_village_ids = set()
    unique_years = set()
    pairs = []
    for r in records:
        unique_village_ids.add(r.villageId)
        unique_years.add(r.yearslap)
        pairs.append({"villageId": str(r.villageId), "yearslap": r.yearslap})
    # Get village names sorted by name for consistency
    villages = (
        db.query(namuna8_model.Village)
        .filter(namuna8_model.Village.id.in_(unique_village_ids))
        .order_by(namuna8_model.Village.name)
        .all()
    )
    village_list = [{"id": v.id, "name": v.name} for v in villages]
    # Sort pairs by numeric villageId then yearslap for stable ordering
    try:
        pairs = sorted(pairs, key=lambda p: (int(p["villageId"]), p["yearslap"]))
    except Exception:
        pairs = sorted(pairs, key=lambda p: (p["villageId"], p["yearslap"]))
    return {"villages": village_list, "years": sorted(list(unique_years)), "pairs": pairs} 

@router.get("/table-data")
def get_table_data(
    villageId: int,
    yearslap: str,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    applyWarrantFee: bool = Query(False),
    applyNoticeFee: bool = Query(False),
    applyPenalty: bool = Query(False),
    db: Session = Depends(database.get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
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
    settings = db.query(Namuna9Settings).filter(
        Namuna9Settings.district_id == district_id,
        Namuna9Settings.taluka_id == taluka_id,
        Namuna9Settings.gram_panchayat_id == gram_panchayat_id
    ).first()
    warrant_fee = settings.warrant_fee if settings and applyWarrantFee else 0
    notice_fee = settings.notice_fee if settings and applyNoticeFee else 0
    penalty = settings.penalty_percentage if settings and applyPenalty else 0
    # Find the Namuna9 record for this village and year
    rec = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId,
        namuna9_model.Namuna9.yearslap == yearslap
    ).first()
    if not rec:
        return []

    # गावातली सर्वात नवीन नमुना-9 साल असेल तरच (जुनी/बंद झालेली वर्षं गोठलेलीच
    # राहावीत) - त्या गावातल्या सर्व live मालमत्तांशी property_ids जुळवतो, जेणेकरून
    # वर्ष तयार झाल्यानंतर जोडलेली मालमत्ताही आपोआप दिसेल, "गाव डेटा जोडा" न दाबता.
    def _yearslap_start_year(ys):
        try:
            return int(str(ys).split('-')[0])
        except Exception:
            return -1
    village_year_records = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId
    ).all()
    if village_year_records:
        latest_yearslap = max((r.yearslap for r in village_year_records), key=_yearslap_start_year)
        if latest_yearslap == rec.yearslap:
            current_village_property_ids = {
                p.id for p in db.query(namuna8_model.Property).filter(
                    namuna8_model.Property.village_id == villageId
                ).all()
            }
            stored_property_ids = set(rec.property_ids or [])
            if not current_village_property_ids.issubset(stored_property_ids):
                rec.property_ids = list(stored_property_ids | current_village_property_ids)
                db.commit()
                db.refresh(rec)

    # Check if thakit is enabled and get thakit data
    does_thakit = getattr(rec, 'doesThakit', False)
    thakit_values = getattr(rec, 'thakitValues', None)
    thakit_year = getattr(rec, 'thakitYear', None)  # फक्त row मध्ये दाखवण्यासाठी - लुकअपसाठी वापरत नाही, बघा खालची टीप.

    # थकित carry-forward फक्त मागच्या (खऱ्याखुऱ्या, yearslap - 1) सालच्या नमुना-9
    # यादीतून, आणि फक्त त्या यादीत असलेल्या मालमत्तांनाच लागू व्हावा - rec.thakitYear
    # वर विसंबून राहत नाही, कारण ते चुकून सध्याच्याच सालाकडे (self-reference) सेट
    # झालेलं असू शकतं (झालं होतं), जे नवीन मालमत्तेला चुकीचा थकित देतं आणि जुन्या
    # मालमत्तेला स्वतःच्याच (अजून none) डेटावरून थकित शोधायला लावतं.
    true_prev_rec = None
    properties_in_true_prev_year = set()
    try:
        true_prev_year = (
            str(int(str(yearslap).split('-')[0]) - 1) + "-" + str(int(str(yearslap).split('-')[1]) - 1)
        )
        true_prev_rec = db.query(namuna9_model.Namuna9).filter(
            namuna9_model.Namuna9.villageId == villageId,
            namuna9_model.Namuna9.yearslap == true_prev_year
        ).first()
        if true_prev_rec and true_prev_rec.property_ids:
            properties_in_true_prev_year = set(true_prev_rec.property_ids)
    except Exception:
        pass

    # If thakit is enabled, get data from the true previous year
    thakit_data = {}
    if does_thakit and thakit_values and true_prev_rec:
        if true_prev_rec.property_ids:
            thakit_property_ids = [int(i) for i in true_prev_rec.property_ids]

            # थकित मागच्या सालच्या स्वतःच्या साठवलेल्या (user ने भरलेल्या/दुरुस्त केलेल्या
            # आकड्यांसकट) आकड्यांवरून काढतो - namuna8 वरून ताजी recalculation नाही, कारण
            # त्यात मागच्या वर्षातले receipt/मॅन्युअल बदल दिसत नाहीत. घरकरात दंड धरतो
            # (शिल्लक बाकी प्रमाणेच); बाकी कर-प्रकारांत फक्त शक्ती+चालू.
            thakit_saved_rows = db.query(namuna9_model.Namuna9PropertyData).filter(
                namuna9_model.Namuna9PropertyData.namuna9_id == true_prev_rec.id,
                namuna9_model.Namuna9PropertyData.property_id.in_(thakit_property_ids)
            ).all()
            thakit_saved_map = {r.property_id: r for r in thakit_saved_rows}
            for pid, saved in thakit_saved_map.items():
                thakit_data[pid] = {
                    'chaluGhar': round((saved.shaktiGhar or 0) + (saved.chaluGhar or 0) + (saved.dand or 0), 2),
                    'chaluDiva': round((saved.shaktiDiva or 0) + (saved.chaluDiva or 0), 2),
                    'chaluAarogyaKar': round((saved.shaktiAarogyaKar or 0) + (saved.chaluAarogyaKar or 0), 2),
                    'chaluSapanikar': round((saved.shaktiSapanikar or 0) + (saved.chaluSapanikar or 0), 2),
                    'chaluVpanikar': round((saved.shaktiVpanikar or 0) + (saved.chaluVpanikar or 0), 2),
                    'chaluCleaningTax': round((saved.shaktiCleaningTax or 0) + (saved.chaluCleaningTax or 0), 2),
                }

            # मागच्या सालात कधीच saved row नसलेल्या मालमत्तांसाठीच (उदा. त्या वर्षी कधीच
            # उघडल्या नव्हत्या) आधीची ताजी recalculation पद्धत बॅकअप म्हणून वापरतो.
            missing_ids = [pid for pid in thakit_property_ids if pid not in thakit_saved_map]
            thakit_properties = db.query(namuna8_model.Property).filter(
                namuna8_model.Property.id.in_(missing_ids)
            ).all() if missing_ids else []

            for thakit_prop in thakit_properties:
                thakit_prop_data = build_property_response(thakit_prop, db, gram_panchayat_id)
                thakit_constructions = db.query(namuna8_model.Construction).filter(
                    namuna8_model.Construction.property_id == thakit_prop.id
                ).all()

                # Check if karLaguNahi is True - if so, set all taxes to zero
                thakit_karLaguNahi = bool(getattr(thakit_prop, 'karLaguNahi', False))

                thakit_house_tax = 0 if thakit_karLaguNahi else sum([c.houseTax or 0 for c in thakit_constructions])
                thakit_lighting_tax = 0 if thakit_karLaguNahi else (thakit_prop_data.get('divaKar', 0) or 0)
                thakit_health_tax = 0 if thakit_karLaguNahi else (thakit_prop_data.get('aarogyaKar', 0) or thakit_prop_data.get('healthTax', 0) or 0)
                thakit_sapanikar = 0 if thakit_karLaguNahi else (thakit_prop_data.get('sapanikar', 0) or 0)
                thakit_vpanikar = 0 if thakit_karLaguNahi else (thakit_prop_data.get('vpanikar', 0) or 0)
                thakit_cleaning_tax = 0 if thakit_karLaguNahi else (thakit_prop_data.get('cleaningTax', 0) or 0)

                # Calculate total for thakit year
                thakit_total = thakit_house_tax + thakit_lighting_tax + thakit_health_tax + thakit_sapanikar + thakit_vpanikar + thakit_cleaning_tax
                thakit_total = round(thakit_total, 2)

                thakit_data[thakit_prop.id] = {
                    'chaluGhar': thakit_house_tax,
                    'chaluDiva': thakit_lighting_tax,
                    'chaluAarogyaKar': thakit_health_tax,
                    'chaluSapanikar': thakit_sapanikar,
                    'chaluVpanikar': thakit_vpanikar,
                    'chaluCleaningTax': thakit_cleaning_tax,
                    'total': thakit_total
                }

    property_ids = getattr(rec, 'property_ids', None)
    if not isinstance(property_ids, list) or len(property_ids) == 0:
        return []
    
    # Fetch saved property data from database
    saved_property_data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == rec.id
    ).all()
    
    # Create a map of property_id to saved data
    saved_data_map = {data.property_id: data for data in saved_property_data}
    
    # Fetch all property details
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids]),
                                                         namuna8_model.Property.village_id == villageId).all()
    # sort_order नुसार क्रम (32, 32/1, 32/2, 33 ...) - DB query ऑर्डरने (साधारण id प्रमाणे)
    # नाही, आणि मालमत्ता क्रमांकाच्या मजकुरावरून काढलेल्या नैसर्गिक क्रमवारीऐवजीही आता
    # sort_order वापरतो, कारण "Insert" ने घातलेल्या मालमत्तेचा मजकूर मोकळा ("1 भाग" सारखा)
    # असला तरी योग्य जागीच (निवडलेल्या मालमत्तेनंतर) दिसायला हवा.
    properties = sorted(properties, key=lambda p: (p.sort_order if p.sort_order is not None else float("inf")))
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        # Query constructions directly for this property
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        
        # Check if karLaguNahi is True - if so, set all taxes to zero
        karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
        
        from namuna9.tax_calculations import calculate_total_house_tax
        totalHouseTax = calculate_total_house_tax(prop, constructions, db)
        # Join all owner names (combined with भोगवटदार for owners like "सरकार" - see _owner_display_name)
        owner_names = ', '.join([_owner_display_name(o) for o in prop_data.get('owners', [])])
        # lightingTax, healthTax, sapanikar, vpanikar, cleaningTax
        lightingTax = round(prop_data.get('divaKar', 0) or 0, 2)
        healthTax = round((prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0), 2)
        sapanikar = round(prop_data.get('sapanikar', 0) or 0, 2)
        vpanikar = round(prop_data.get('vpanikar', 0) or 0, 2)
        cleaningTax = round(prop_data.get('cleaningTax', 0) or 0, 2)
        
        # Check if we have saved data for this property
        saved_data = saved_data_map.get(prop.id)
        
        # Initialize thakit values (use saved data if available, otherwise calculate)
        if saved_data:
            shaktiGhar = round(saved_data.shaktiGhar or 0, 2)
            shaktiDiva = round(saved_data.shaktiDiva or 0, 2)
            shaktiAarogyaKar = round(saved_data.shaktiAarogyaKar or 0, 2)
            shaktiSapanikar = round(saved_data.shaktiSapanikar or 0, 2)
            shaktiVpanikar = round(saved_data.shaktiVpanikar or 0, 2)
            shaktiCleaningTax = round(saved_data.shaktiCleaningTax or 0, 2)
            dand = round(saved_data.dand or 0, 2)
            # Use saved values directly, even if they are 0 or negative (don't fallback to calculated taxes)
            chaluGhar = round(saved_data.chaluGhar, 2) if saved_data.chaluGhar is not None else round(totalHouseTax, 2)
            chaluDiva = round(saved_data.chaluDiva, 2) if saved_data.chaluDiva is not None else round(lightingTax, 2)
            chaluAarogyaKar = round(saved_data.chaluAarogyaKar, 2) if saved_data.chaluAarogyaKar is not None else round(healthTax, 2)
            chaluSapanikar = round(saved_data.chaluSapanikar, 2) if saved_data.chaluSapanikar is not None else round(sapanikar, 2)
            chaluVpanikar = round(saved_data.chaluVpanikar, 2) if saved_data.chaluVpanikar is not None else round(vpanikar, 2)
            chaluCleaningTax = round(saved_data.chaluCleaningTax, 2) if saved_data.chaluCleaningTax is not None else round(cleaningTax, 2)
            warrantFee = saved_data.warrantFee if saved_data.warrantFee is not None else warrant_fee
            noticeFee = saved_data.noticeFee if saved_data.noticeFee is not None else notice_fee
        else:
            shaktiGhar = 0
            shaktiDiva = 0
            shaktiAarogyaKar = 0
            shaktiSapanikar = 0
            shaktiVpanikar = 0
            shaktiCleaningTax = 0
            dand = 0
            chaluGhar = totalHouseTax
            chaluDiva = lightingTax
            chaluAarogyaKar = healthTax
            chaluSapanikar = sapanikar
            chaluVpanikar = vpanikar
            chaluCleaningTax = cleaningTax
            warrantFee = warrant_fee
            noticeFee = notice_fee
        
        # Apply thakit logic if enabled and no saved data - आणि ही मालमत्ता मागच्या
        # सालात प्रत्यक्ष अस्तित्वात होती तरच (नवीन मालमत्तेला थकित नको).
        if (not saved_data and does_thakit and thakit_values and prop.id in thakit_data
                and prop.id in properties_in_true_prev_year):
            thakit_prop_data = thakit_data[prop.id]
            
            if thakit_values == "chaluGhar":
                # Use chalu values from thakit year as shakti
                shaktiGhar = round(thakit_prop_data['chaluGhar'], 2)
                shaktiDiva = round(thakit_prop_data['chaluDiva'], 2)
                shaktiAarogyaKar = round(thakit_prop_data['chaluAarogyaKar'], 2)
                shaktiSapanikar = round(thakit_prop_data['chaluSapanikar'], 2)
                shaktiVpanikar = round(thakit_prop_data['chaluVpanikar'], 2)
                shaktiCleaningTax = round(thakit_prop_data['chaluCleaningTax'], 2)
            elif thakit_values == "yekun":
                # Use total values from thakit year as shakti
                shaktiGhar = round(thakit_prop_data['chaluGhar'], 2)  # Total house tax
                shaktiDiva = round(thakit_prop_data['chaluDiva'], 2)  # Total lighting tax
                shaktiAarogyaKar = round(thakit_prop_data['chaluAarogyaKar'], 2)  # Total health tax
                shaktiSapanikar = round(thakit_prop_data['chaluSapanikar'], 2)  # Total sapanikar
                shaktiVpanikar = round(thakit_prop_data['chaluVpanikar'], 2)  # Total vpanikar
                shaktiCleaningTax = round(thakit_prop_data['chaluCleaningTax'], 2)  # Total cleaning tax
            elif thakit_values == "thakit":
                # Use thakit values (same as chaluGhar for now)
                shaktiGhar = round(thakit_prop_data['chaluGhar'], 2)
                shaktiDiva = round(thakit_prop_data['chaluDiva'], 2)
                shaktiAarogyaKar = round(thakit_prop_data['chaluAarogyaKar'], 2)
                shaktiSapanikar = round(thakit_prop_data['chaluSapanikar'], 2)
                shaktiVpanikar = round(thakit_prop_data['chaluVpanikar'], 2)
                shaktiCleaningTax = round(thakit_prop_data['chaluCleaningTax'], 2)
        
        # Calculate ekun (total) values - use saved data if available
        if saved_data:
            # Include dand in ekunGhar (house total) - ensure no negative values
            ekunGhar = round(max(shaktiGhar,0) + max(chaluGhar,0) + (max(dand,0) or 0), 2)
            ekunDiva = round(max(saved_data.ekunDiva or (shaktiDiva + chaluDiva), 0), 2)
            ekunAarogyaKar = round(max(saved_data.ekunAarogyaKar or (shaktiAarogyaKar + chaluAarogyaKar), 0), 2)
            ekunSapanikar = round(max(saved_data.ekunSapanikar or (shaktiSapanikar + chaluSapanikar), 0), 2)
            ekunVpanikar = round(max(saved_data.ekunVpanikar or (shaktiVpanikar + chaluVpanikar), 0), 2)
            ekunCleaningTax = round(max(saved_data.ekunCleaningTax or (shaktiCleaningTax + chaluCleaningTax), 0), 2)
        else:
            # Include dand in ekunGhar when no saved_data - ensure no negative values
            ekunGhar = round(max(totalHouseTax + (max(dand,0) or 0), (max(shaktiGhar,0) + max(chaluGhar,0) + (max(dand,0) or 0)), 0), 2)
            ekunDiva = round(max(shaktiDiva + chaluDiva, 0), 2)
            ekunAarogyaKar = round(max(shaktiAarogyaKar + chaluAarogyaKar, 0), 2)
            ekunSapanikar = round(max(shaktiSapanikar + chaluSapanikar, 0), 2)
            ekunVpanikar = round(max(shaktiVpanikar + chaluVpanikar, 0), 2)
            ekunCleaningTax = round(max(shaktiCleaningTax + chaluCleaningTax, 0), 2)
        
        # Total reflects ekun columns + fees + dand, avoiding double-count of shakti/chalu
        if saved_data and saved_data.total is not None:
            total = max(saved_data.total, 0)  # Ensure total is not negative
        else:
            total = (
                    (ekunGhar or 0) +
                    (ekunDiva or 0) +
                    (ekunAarogyaKar or 0) +
                    (ekunSapanikar or 0) +
                    (ekunVpanikar or 0) +
                    (ekunCleaningTax or 0) +
                    (warrantFee or 0) +
                    (noticeFee or 0) +
                    (dand or 0)
            )
            total = round(total, 2)
        
        # Final override: If karLaguNahi is True, set ALL taxes to 0 (this ensures automatic update from namuna8)
        if karLaguNahi:
            shaktiGhar = 0
            shaktiDiva = 0
            shaktiAarogyaKar = 0
            shaktiSapanikar = 0
            shaktiVpanikar = 0
            shaktiCleaningTax = 0
            chaluGhar = 0
            chaluDiva = 0
            chaluAarogyaKar = 0
            chaluSapanikar = 0
            chaluVpanikar = 0
            chaluCleaningTax = 0
            ekunGhar = 0
            ekunDiva = 0
            ekunAarogyaKar = 0
            ekunSapanikar = 0
            ekunVpanikar = 0
            ekunCleaningTax = 0
            totalHouseTax = 0
            total = warrantFee + noticeFee  # Only fees remain, no taxes
        
        row = {
            "anukramk": prop.anuKramank,
            # मालमत्ता क्रमांक नैसर्गिक क्रमवारी (वर properties = sorted(...) पहा) नंतरचा
            # चालू क्रमांक (1,2,3...) - फक्त डिस्प्लेसाठी; जतन केलेला anuKramank (वरचं
            # "anukramk") बदलत नाही, फक्त स्क्रीनवरचा अ.क्र. कॉलम आता हा वापरतो.
            "srNo": idx,
            "sort_order": prop.sort_order,
            "property_id": prop.id,  # Use actual property ID, not anuKramank
            "malmattaKramank": prop_data.get('malmattaKramank', ''),
            "ownerNames": owner_names,
            "shaktiGhar": round(max(shaktiGhar, 0), 2),
            "dand": round(max(dand, 0), 2),
            "chaluGhar": round(max(chaluGhar, 0), 2),
            "ekunGhar": round(max(ekunGhar, 0), 2),
            "totalHouseTax": round(max(totalHouseTax, 0), 2),
            "shaktiDiva": round(max(shaktiDiva, 0), 2),
            "chaluDiva": round(max(chaluDiva, 0), 2),
            "ekunDiva": round(max(ekunDiva, 0), 2),
            "shaktiAarogyaKar": round(max(shaktiAarogyaKar, 0), 2),
            "chaluAarogyaKar": round(max(chaluAarogyaKar, 0), 2),
            "ekunAarogyaKar": round(max(ekunAarogyaKar, 0), 2),
            "shaktiSapanikar": round(max(shaktiSapanikar, 0), 2),
            "chaluSapanikar": round(max(chaluSapanikar, 0), 2),
            "ekunSapanikar": round(max(ekunSapanikar, 0), 2),
            "shaktiVpanikar": round(max(shaktiVpanikar, 0), 2),
            "chaluVpanikar": round(max(chaluVpanikar, 0), 2),
            "ekunVpanikar": round(max(ekunVpanikar, 0), 2),
            "shaktiCleaningTax": round(max(shaktiCleaningTax, 0), 2),
            "chaluCleaningTax": round(max(chaluCleaningTax, 0), 2),
            "ekunCleaningTax": round(max(ekunCleaningTax, 0), 2),
            "warrantFee": max(warrantFee, 0),
            "noticeFee": max(noticeFee, 0),
            "total": round(max(total, 0), 2),
            "doesThakit": does_thakit,
            "thakitValues": thakit_values,
            "thakitYear": thakit_year
}
        if not saved_data:
            new_saved = namuna9_model.Namuna9PropertyData(
            namuna9_id = rec.id,
            property_id = prop.id,

            shaktiGhar = row["shaktiGhar"],
            shaktiDiva = row["shaktiDiva"],
            shaktiAarogyaKar = row["shaktiAarogyaKar"],
            shaktiSapanikar = row["shaktiSapanikar"],
            shaktiVpanikar = row["shaktiVpanikar"],
            shaktiCleaningTax = row["shaktiCleaningTax"],

            dand = row["dand"],

            chaluGhar = row["chaluGhar"],
            chaluDiva = row["chaluDiva"],
            chaluAarogyaKar = row["chaluAarogyaKar"],
            chaluSapanikar = row["chaluSapanikar"],
            chaluVpanikar = row["chaluVpanikar"],
            chaluCleaningTax = row["chaluCleaningTax"],

            ekunGhar = row["ekunGhar"],
            ekunDiva = row["ekunDiva"],
            ekunAarogyaKar = row["ekunAarogyaKar"],
            ekunSapanikar = row["ekunSapanikar"],
            ekunVpanikar = row["ekunVpanikar"],
            ekunCleaningTax = row["ekunCleaningTax"],

            warrantFee = row["warrantFee"],
            noticeFee = row["noticeFee"],
            total = row["total"]
            )

            db.add(new_saved)
            db.commit()
            db.refresh(new_saved)

            saved_data = new_saved
            saved_data_map[prop.id] = new_saved
        rows.append(row)
    # sort_order नुसार क्रम - anuKramank ने नाही (उप-मालमत्तांना नंतरचा anuKramank मिळतो),
    # आणि मालमत्ता क्रमांकाच्या मजकुरावरून काढलेल्या नैसर्गिक क्रमवारीऐवजीही आता हाच
    # वापरतो ("Insert" ने घातलेल्या मालमत्तेचा मजकूर काहीही असो, योग्य जागीच दिसण्यासाठी).
    rows = sorted(rows, key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else float("inf")))
    return rows

@router.get("/recordresponses/property_records_by_village")
def get_namuna9_table_data_custom(
    villageId: str, 
    yearslap: str, 
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    applyWarrantFee: bool = Query(False),
    applyNoticeFee: bool = Query(False),
    applyPenalty: bool = Query(False),
    db: Session = Depends(database.get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    district_name_ic = getattr(district, 'name', None)
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    taluka_name_ic = getattr(taluka, 'name', None)
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    rec = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId,
        namuna9_model.Namuna9.yearslap == yearslap
    ).first()
    if not rec:
        return []

    # गावातली सर्वात नवीन नमुना-9 साल असेल तरच (जुनी/बंद झालेली वर्षं गोठलेलीच
    # राहावीत) - त्या गावातल्या सर्व live मालमत्तांशी property_ids जुळवतो, get_table_data
    # प्रमाणेच - अन्यथा नंतर जोडलेली मालमत्ता (उदा. "80/1") या प्रिंटमध्ये कधीच दिसत नसे.
    def _yearslap_start_year(ys):
        try:
            return int(str(ys).split('-')[0])
        except Exception:
            return -1
    village_year_records = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId
    ).all()
    if village_year_records:
        latest_yearslap = max((r.yearslap for r in village_year_records), key=_yearslap_start_year)
        if latest_yearslap == rec.yearslap:
            current_village_property_ids = {
                p.id for p in db.query(namuna8_model.Property).filter(
                    namuna8_model.Property.village_id == villageId
                ).all()
            }
            stored_property_ids = set(rec.property_ids or [])
            if not current_village_property_ids.issubset(stored_property_ids):
                rec.property_ids = list(stored_property_ids | current_village_property_ids)
                db.commit()
                db.refresh(rec)

    # Settings for fees (match table-data)
    settings = db.query(Namuna9Settings).filter(
        Namuna9Settings.district_id == district_id,
        Namuna9Settings.taluka_id == taluka_id,
        Namuna9Settings.gram_panchayat_id == gram_panchayat_id
    ).first()
    warrant_fee = settings.warrant_fee if settings and applyWarrantFee else 0
    notice_fee = settings.notice_fee if settings and applyNoticeFee else 0
    penalty_percentage = settings.penalty_percentage if settings and applyPenalty else 0
    property_ids = getattr(rec, 'property_ids', None)
    if not isinstance(property_ids, list) or len(property_ids) == 0:
        return []
    # Fetch saved property data for this Namuna9 record (to mirror table-data behavior)
    saved_property_data = db.query(namuna9_model.Namuna9PropertyData).filter(
        namuna9_model.Namuna9PropertyData.namuna9_id == rec.id
    ).all()
    saved_data_map = {data.property_id: data for data in saved_property_data}

    # Thakit setup
    does_thakit = getattr(rec, 'doesThakit', False)
    thakit_values = getattr(rec, 'thakitValues', None)
    thakit_year = getattr(rec, 'thakitYear', None)  # फक्त row मध्ये दाखवण्यासाठी - लुकअपसाठी वापरत नाही.

    # थकित हस्तांतरण फक्त मागच्या (खऱ्याखुऱ्या, yearslap - 1) सालच्या यादीत असलेल्या
    # मालमत्तांनाच लागू व्हावं - rec.thakitYear वर विसंबून राहत नाही (get_table_data
    # प्रमाणेच, बघा तिथली सविस्तर टीप).
    true_prev_rec = None
    properties_in_true_prev_year = set()
    try:
        true_prev_year = (
            str(int(str(yearslap).split('-')[0]) - 1) + "-" + str(int(str(yearslap).split('-')[1]) - 1)
        )
        true_prev_rec = db.query(namuna9_model.Namuna9).filter(
            namuna9_model.Namuna9.villageId == villageId,
            namuna9_model.Namuna9.yearslap == true_prev_year
        ).first()
        if true_prev_rec and true_prev_rec.property_ids:
            properties_in_true_prev_year = set(true_prev_rec.property_ids)
    except Exception:
        pass

    thakit_data = {}
    if does_thakit and thakit_values and true_prev_rec and true_prev_rec.property_ids:
        thakit_property_ids = [int(i) for i in true_prev_rec.property_ids]

        # get_table_data प्रमाणेच - मागच्या सालच्या स्वतःच्या साठवलेल्या आकड्यांवरून
        # (दंडासकट घरकरात) थकित काढतो, ताजी recalculation नाही.
        thakit_saved_rows = db.query(namuna9_model.Namuna9PropertyData).filter(
            namuna9_model.Namuna9PropertyData.namuna9_id == true_prev_rec.id,
            namuna9_model.Namuna9PropertyData.property_id.in_(thakit_property_ids)
        ).all()
        thakit_saved_map = {r.property_id: r for r in thakit_saved_rows}
        for pid, saved in thakit_saved_map.items():
            thakit_data[pid] = {
                'chaluGhar': round((saved.shaktiGhar or 0) + (saved.chaluGhar or 0) + (saved.dand or 0), 2),
                'chaluDiva': round((saved.shaktiDiva or 0) + (saved.chaluDiva or 0), 2),
                'chaluAarogyaKar': round((saved.shaktiAarogyaKar or 0) + (saved.chaluAarogyaKar or 0), 2),
                'chaluSapanikar': round((saved.shaktiSapanikar or 0) + (saved.chaluSapanikar or 0), 2),
                'chaluVpanikar': round((saved.shaktiVpanikar or 0) + (saved.chaluVpanikar or 0), 2),
                'chaluCleaningTax': round((saved.shaktiCleaningTax or 0) + (saved.chaluCleaningTax or 0), 2),
            }

        missing_ids = [pid for pid in thakit_property_ids if pid not in thakit_saved_map]
        thakit_properties = db.query(namuna8_model.Property).filter(
            namuna8_model.Property.id.in_(missing_ids)
        ).all() if missing_ids else []
        for thakit_prop in thakit_properties:
            thakit_prop_data = build_property_response(thakit_prop, db, gram_panchayat_id)
            thakit_constructions = db.query(namuna8_model.Construction).filter(
                namuna8_model.Construction.property_id == thakit_prop.id
            ).all()

            # Check if karLaguNahi is True - if so, set all taxes to zero
            thakit_karLaguNahi = bool(getattr(thakit_prop, 'karLaguNahi', False))

            t_house_tax = 0 if thakit_karLaguNahi else sum([c.houseTax or 0 for c in thakit_constructions])
            t_lighting = 0 if thakit_karLaguNahi else (thakit_prop_data.get('divaKar', 0) or 0)
            t_health = 0 if thakit_karLaguNahi else (thakit_prop_data.get('aarogyaKar', 0) or thakit_prop_data.get('healthTax', 0) or 0)
            t_sa = 0 if thakit_karLaguNahi else (thakit_prop_data.get('sapanikar', 0) or 0)
            t_vi = 0 if thakit_karLaguNahi else (thakit_prop_data.get('vpanikar', 0) or 0)
            t_clean = 0 if thakit_karLaguNahi else (thakit_prop_data.get('cleaningTax', 0) or 0)
            thakit_data[thakit_prop.id] = {
                'chaluGhar': t_house_tax,
                'chaluDiva': t_lighting,
                'chaluAarogyaKar': t_health,
                'chaluSapanikar': t_sa,
                'chaluVpanikar': t_vi,
                'chaluCleaningTax': t_clean
            }

    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids]),
                                                         namuna8_model.Property.village_id == villageId).all()
    # sort_order नुसार क्रम (32, 32/1, 32/2, 33 ...) - मालमत्ता क्रमांकाच्या मजकुरावरून
    # काढलेल्या नैसर्गिक क्रमवारीऐवजी, "Insert" ने घातलेल्या मालमत्तेचा मजकूर काहीही असो
    # योग्य जागीच दिसण्यासाठी.
    properties = sorted(properties, key=lambda p: (p.sort_order if p.sort_order is not None else float("inf")))
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        
        # Check if karLaguNahi is True - if so, set all taxes to zero
        karLaguNahi = bool(getattr(prop, 'karLaguNahi', False))
        
        # Base total house tax from constructions
        if karLaguNahi:
            totalHouseTax = 0
        else:
            totalHouseTax = sum([(c.houseTax or 0) for c in constructions])
            # Khali jaga addition with unit handling similar to Namuna8. बांधकाम
            # लांबी/रुंदी constructionAreaUnit मध्ये असू शकतात, जे areaUnit पेक्षा वेगळं
            # असू शकतं - त्यामुळे used_area साठी वेगळं एकक वापरतो.
            vacant_land_type = getattr(prop, 'vacantLandType', None)
            if vacant_land_type not in [None, '', 'null']:
                # tax_calculations.calculate_total_house_tax प्रमाणेच - प्लॉटच्याच
                # एककात (unit) थेट वजाबाकी, गरज असेल तरच शेअर्ड 10.76 फॅक्टरने रूपांतर.
                unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
                construction_unit = getattr(prop, 'constructionAreaUnit', None) or unit
                total_area = (prop.totalArea or 0) if unit == 'sqm' else (prop.totalAreaSqFt or 0)
                construction_sum = round(sum((c.length or 0) * (c.width or 0) for c in constructions), 2)
                if construction_unit == unit:
                    used_area = construction_sum
                else:
                    used_area = round(construction_sum * 10.76, 2) if unit == 'sqft' else round(construction_sum / 10.76, 2)
                khali_area = round(max(total_area - used_area, 0), 2)
                khali_area_m = khali_area if unit == 'sqm' else round(khali_area / 10.76, 2)
                if khali_area > 0:
                    khali_construction_type = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == vacant_land_type).first()
                    if khali_construction_type:
                        AnnualLandValueRate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                        capital_value_kj = round_tax_amount(khali_area_m * AnnualLandValueRate, db, gram_panchayat_id)
                        totalHouseTax += round_tax_amount((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj, db, gram_panchayat_id)
        totalHouseTax = round(totalHouseTax, 2)
        # Taxes
        lightingTax = round((prop_data.get('divaKar', 0) or prop_data.get('lightingTax', 0) or 0), 2)
        healthTax = round((prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0), 2)
        saWaterTax = round(prop_data.get('sapanikar', 0) or 0, 2)
        viWaterTax = round(prop_data.get('vpanikar', 0) or 0, 2)
        cleaningTax = round(prop_data.get('cleaningTax', 0) or 0, 2)
        toiletTax = round(prop_data.get('toiletTax', 0) or 0, 2)

        # Saved data and thakit handling mapped to our response names
        saved_data = saved_data_map.get(prop.id)
        if saved_data:
            # Always honor saved values even if 0 or negative, to mirror the table
            shaktiGhar = round(saved_data.shaktiGhar or 0, 2)
            shaktiDiva = round(saved_data.shaktiDiva or 0, 2)
            shaktiAarogyaKar = round(saved_data.shaktiAarogyaKar or 0, 2)
            shaktiSapanikar = round(saved_data.shaktiSapanikar or 0, 2)
            shaktiVpanikar = round(saved_data.shaktiVpanikar or 0, 2)
            shaktiCleaningTax = round(saved_data.shaktiCleaningTax or 0, 2)
            dand = round(saved_data.dand or 0, 2)
            chaluGhar = round(saved_data.chaluGhar, 2) if saved_data.chaluGhar is not None else round(totalHouseTax, 2)
            chaluDiva = round(saved_data.chaluDiva, 2) if saved_data.chaluDiva is not None else round(lightingTax, 2)
            chaluAarogyaKar = round(saved_data.chaluAarogyaKar, 2) if saved_data.chaluAarogyaKar is not None else round(healthTax, 2)
            chaluSapanikar = round(saved_data.chaluSapanikar, 2) if saved_data.chaluSapanikar is not None else round(saWaterTax, 2)
            chaluVpanikar = round(saved_data.chaluVpanikar, 2) if saved_data.chaluVpanikar is not None else round(viWaterTax, 2)
            chaluCleaningTax = round(saved_data.chaluCleaningTax, 2) if saved_data.chaluCleaningTax is not None else round(cleaningTax, 2)
            warrantFee = saved_data.warrantFee if saved_data.warrantFee is not None else warrant_fee
            noticeFee = saved_data.noticeFee if saved_data.noticeFee is not None else notice_fee
        else:
            shaktiGhar = 0
            shaktiDiva = 0
            shaktiAarogyaKar = 0
            shaktiSapanikar = 0
            shaktiVpanikar = 0
            shaktiCleaningTax = 0
            dand = 0
            chaluGhar = totalHouseTax
            chaluDiva = lightingTax
            chaluAarogyaKar = healthTax
            chaluSapanikar = saWaterTax
            chaluVpanikar = viWaterTax
            chaluCleaningTax = cleaningTax
            warrantFee = warrant_fee
            noticeFee = notice_fee

        if (not saved_data and does_thakit and thakit_values and prop.id in thakit_data
                and prop.id in properties_in_true_prev_year):
            tdata = thakit_data[prop.id]
            if thakit_values == "chaluGhar":
                shaktiGhar = round(tdata['chaluGhar'], 2)
                shaktiDiva = round(tdata['chaluDiva'], 2)
                shaktiAarogyaKar = round(tdata['chaluAarogyaKar'], 2)
                shaktiSapanikar = round(tdata['chaluSapanikar'], 2)
                shaktiVpanikar = round(tdata['chaluVpanikar'], 2)
                shaktiCleaningTax = round(tdata['chaluCleaningTax'], 2)
            elif thakit_values in ("yekun", "thakit"):
                shaktiGhar = round(tdata['chaluGhar'], 2)
                shaktiDiva = round(tdata['chaluDiva'], 2)
                shaktiAarogyaKar = round(tdata['chaluAarogyaKar'], 2)
                shaktiSapanikar = round(tdata['chaluSapanikar'], 2)
                shaktiVpanikar = round(tdata['chaluVpanikar'], 2)
                shaktiCleaningTax = round(tdata['chaluCleaningTax'], 2)

        # Map to your response field names and compute totals like table-data total
        ekunGhar = round(shaktiGhar + chaluGhar + (dand or 0), 2)
        ekunDiva = round(shaktiDiva + chaluDiva, 2)
        ekunAarogyaKar = round(shaktiAarogyaKar + chaluAarogyaKar, 2)
        ekunSapanikar = round(shaktiSapanikar + chaluSapanikar, 2)
        ekunVpanikar = round(shaktiVpanikar + chaluVpanikar, 2)
        ekunCleaningTax = round(shaktiCleaningTax + chaluCleaningTax, 2)

        total = (
            (max(0,ekunGhar) or 0) + (max(0,ekunDiva) or 0) + (max(0,ekunAarogyaKar) or 0) +
            (max(0,ekunSapanikar) or 0) + (max(0,ekunVpanikar) or 0) + (max(0,ekunCleaningTax) or 0) +
            (max(0,warrantFee) or 0) + (max(0,noticeFee) or 0)
        )
        total = round(total, 2)
        
        # Final override: If karLaguNahi is True, set ALL taxes to 0 (this ensures automatic update from namuna8)
        if karLaguNahi:
            shaktiGhar = 0
            shaktiDiva = 0
            shaktiAarogyaKar = 0
            shaktiSapanikar = 0
            shaktiVpanikar = 0
            shaktiCleaningTax = 0
            chaluGhar = 0
            chaluDiva = 0
            chaluAarogyaKar = 0
            chaluSapanikar = 0
            chaluVpanikar = 0
            chaluCleaningTax = 0
            ekunGhar = 0
            ekunDiva = 0
            ekunAarogyaKar = 0
            ekunSapanikar = 0
            ekunVpanikar = 0
            ekunCleaningTax = 0
            totalHouseTax = 0
            total = warrantFee + noticeFee  # Only fees remain, no taxes
        
        row = {
            "id": str(prop.anuKramank),
            "srNo": idx,
            "sort_order": prop.sort_order,
            "gramPanchayat": gram_panchayat.name if gram_panchayat else None,
            "taluka": taluka_name_ic if taluka_name_ic else None,
            "jilha": district_name_ic if district_name_ic else None,
            "village": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "ownerName": ', '.join([_owner_display_name(o) for o in prop_data.get('owners', [])]),
            "occupant" : ', '.join([o.get('occupantName', '') for o in prop_data.get('owners', [])]),
            "propertyNumber": prop_data.get('malmattaKramank', ''),
            # Map table columns into your field names
            "dhakitHouseTax": round(shaktiGhar, 2),
            "dandHouseTax": round(dand, 2),
            "houseTax": round(chaluGhar, 2),
            "totalHouseTax": round(ekunGhar, 2),
            "dhakitLightingTax": round(shaktiDiva, 2),
            "lightingTax": round(chaluDiva, 2),
            "totalLightingTax": round(ekunDiva, 2),
            "dhakitHealthTax": round(shaktiAarogyaKar, 2),
            "healthTax": round(chaluAarogyaKar, 2),
            "totalHealthTax": round(ekunAarogyaKar, 2),
            "dhakitSaWaterTax": round(shaktiSapanikar, 2),
            "saWaterTax": round(chaluSapanikar, 2), 
            "totalSaWaterTax": round(ekunSapanikar, 2), 
            "dhakitViWaterTax": round(shaktiVpanikar, 2),
            "viWaterTax": round(chaluVpanikar, 2), 
            "totalViWaterTax": round(ekunVpanikar, 2), 
            "dhakitCleaningTax": round(shaktiCleaningTax, 2),
            "cleaningTax": round(chaluCleaningTax, 2),
            "totalCleaningTax": round(ekunCleaningTax, 2),
            "dhakitToiletTax": 0,
            "toiletTax": round(toiletTax, 2),
            "totlaToiletTax": 0,
            "totaltax": round(total, 2),
            "totaltaxwithoutnoticwarrant": round(total - (warrantFee or 0) - (noticeFee or 0), 2),
            "totaltaxwithoutspanivpaninoticewaraant": round(
                (max(0,ekunGhar) or 0) + (max(0,ekunDiva) or 0) + (max(0,ekunAarogyaKar) or 0)
                - 0  # clarity
                + 0  # clarity
                - 0  # clarity
                + 0  # clarity
                , 2
            ) if False else round(
                (total or 0)
                - (max(0,ekunSapanikar) or 0)
                - (max(0,ekunVpanikar) or 0)
                - (max(0,warrantFee) or 0)
                - (max(0,noticeFee) or 0)
            , 2),
            "pavatiSRKivyaTarik": 0
        }
        rows.append(row)
    # sort_order नुसार क्रम - anuKramank ("id" इथे) ने नाही, आणि मालमत्ता क्रमांकाच्या
    # मजकुरावरून काढलेल्या नैसर्गिक क्रमवारीऐवजीही आता हाच वापरतो.
    rows = sorted(rows, key=lambda r: (r.get("sort_order") if r.get("sort_order") is not None else float("inf")))
    return rows


@router.get("/recordresponses/property_records_by_village/regular/")
def get_property_records_by_village_regular(
    villageId: str,
    yearslap: str,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    applyWarrantFee: bool = Query(False),
    applyNoticeFee: bool = Query(False),
    applyPenalty: bool = Query(False),
    db: Session = Depends(database.get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    district_name_ic = getattr(district, 'name', None)
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    taluka_name_ic = getattr(taluka, 'name', None)
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    from datetime import datetime
    rec = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId,
        namuna9_model.Namuna9.yearslap == yearslap
    ).first()
    if not rec:
        return []
    property_ids = getattr(rec, 'property_ids', None)
    if not isinstance(property_ids, list) or len(property_ids) == 0:
        return []
    # Get canonical calculations from the table-data endpoint
    table_rows = get_table_data(
        villageId=int(villageId),
        yearslap=yearslap,
        district_id=district_id,
        taluka_id=taluka_id,
        gram_panchayat_id=gram_panchayat_id,
        applyWarrantFee=applyWarrantFee,
        applyNoticeFee=applyNoticeFee,
        applyPenalty=applyPenalty,
        db=db
    )
    bank_qr = None;
    from location_management import helpers
    image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
    if image_path and os.path.exists(image_path):
          bank_qr = f"{backend_url}/location/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image"
    signature_image = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/signature"
        if gram_panchayat and gram_panchayat.signature_url else None
    )
    # घर कर / पाणी कर Bank Scanner QR - only shown if the GP has turned this on
    # in Master settings (same toggle used by the namuna8Print prakar routes).
    show_bank_scanner = bool(gram_panchayat and gram_panchayat.show_bank_scanner_in_reports)
    houseTaxQrUrl = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/house"
        if show_bank_scanner and gram_panchayat and gram_panchayat.house_tax_qr_url else None
    )
    waterTaxQrUrl = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/water"
        if show_bank_scanner and gram_panchayat and gram_panchayat.water_tax_qr_url else None
    )

    mapped = []
    from datetime import datetime
    for r in table_rows:
        # शिल्लक बाकी नमुना-10 पावती प्रमाणेच पूर्ण दिसावी म्हणून विशेष पाणी कर
        # (Thakit5/current5) इथेही समाविष्ट केला - सफाई/नोटीस/वारंट एका जागेने पुढे सरकले.
        thakit = {f"Thakit{i}": 0 for i in range(1, 9)}
        thakit["Thakit1"] = r.get('shaktiGhar', 0)
        thakit["Thakit2"] = r.get('shaktiDiva', 0)
        thakit["Thakit3"] = r.get('shaktiAarogyaKar', 0)
        thakit["Thakit4"] = r.get('shaktiSapanikar', 0)
        thakit["Thakit5"] = r.get('shaktiVpanikar', 0)
        thakit["Thakit6"] = r.get('shaktiCleaningTax', 0)
        thakit["Thakit7"] = r.get('noticeFee', 0)
        thakit["Thakit8"] = r.get('warrantFee', 0)

        current = {
            "current1": r.get('chaluGhar', 0),
            "current2": r.get('chaluDiva', 0),
            "current3": r.get('chaluAarogyaKar', 0),
            "current4": r.get('chaluSapanikar', 0),
            "current5": r.get('chaluVpanikar', 0),
            "current6": r.get('chaluCleaningTax', 0),
            "current7": r.get('noticeFee', 0),
            "current8": r.get('warrantFee', 0)
        }
        total = {
            "total1": round(r.get('ekunGhar', 0)),
            "total2": round(r.get('ekunDiva', 0)),
            "total3": round(r.get('ekunAarogyaKar', 0)),
            "total4": round(r.get('ekunSapanikar', 0)),
            "total5": round(r.get('ekunVpanikar', 0)),
            "total6": round(r.get('ekunCleaningTax', 0)),
            # For fees, show only the fee amount once in the last column
            "total7": round(r.get('noticeFee', 0)),
            "total8": round(r.get('warrantFee', 0))
        }
        # Build Dand map sourced from table row (use dand in house column)
        dand_map = {f"Dand{i}": 0 for i in range(1, 9)}
        dand_map["Dand1"] = r.get('dand', 0)

        # भरलेली रक्कम - या मालमत्तेच्या सर्व पावत्यांमधून (थकित+चालू दोन्ही मिळून)
        # आजवर प्रत्यक्ष जमा झालेली एकूण रक्कम, कर-प्रकारानुसार. चालू कॉलमसाठी
        # वापरतो (नमुना-10 पावतीत जसं "भरलेली" रक्कम दिसते तशीच इथेही दिसावी).
        paid_map = {f"paid{i}": 0 for i in range(1, 9)}
        try:
            all_receipts = db.query(namuna9_model.Namuna9Receipt).filter(
                namuna9_model.Namuna9Receipt.namuna9_id == rec.id,
                namuna9_model.Namuna9Receipt.property_id == r.get('property_id'),
                namuna9_model.Namuna9Receipt.is_deleted == False
            ).all()
            paid_map["paid1"] = round(sum((rcpt.vasuliGhar or 0) + (rcpt.vasuliChaluGhar or 0) for rcpt in all_receipts), 2)
            paid_map["paid2"] = round(sum((rcpt.vasuliDiva or 0) + (rcpt.vasuliChaluDiva or 0) for rcpt in all_receipts), 2)
            paid_map["paid3"] = round(sum((rcpt.vasuliAarogyaKar or 0) + (rcpt.vasuliChaluAarogyaKar or 0) for rcpt in all_receipts), 2)
            paid_map["paid4"] = round(sum((rcpt.vasuliSapanikar or 0) + (rcpt.vasuliChaluSapanikar or 0) for rcpt in all_receipts), 2)
            paid_map["paid5"] = round(sum((rcpt.vasuliVpanikar or 0) + (rcpt.vasuliChaluVpanikar or 0) for rcpt in all_receipts), 2)
            paid_map["paid6"] = round(sum((rcpt.vasuliCleaningTax or 0) + (rcpt.vasuliChaluCleaningTax or 0) for rcpt in all_receipts), 2)
            paid_map["paid7"] = round(sum((rcpt.vasuliNoticeFee or 0) for rcpt in all_receipts), 2)
            paid_map["paid8"] = round(sum((rcpt.vasuliWarrantFee or 0) for rcpt in all_receipts), 2)
        except Exception:
            pass

        # Resolve gram panchayat name and occupant name using the property record
        gp_name = None
        village_name = None
        anu_kramank = None
        occupant_name = ""
        owner_names_plain = ""
        parent_gp_name = None
        try:
            prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == r.get('property_id')).first()
            if prop:
                anu_kramank = compute_display_sr_no(db, prop.village_id, prop.anuKramank)
                # GP name from village linkage
                v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
                if v:
                    village_name = getattr(v, 'name', None)
                    gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
                    gp_name = getattr(gp, 'name', None)
                    parent_gp_name = getattr(gp, 'parent_gram_panchayat_name', None)
                    taluka_name = getattr(gp, 'taluka_id', None)
                    if taluka_name:
                        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_name).first()
                        if taluka:
                            taluka_name = getattr(taluka, 'name', None)
                    district_name = getattr(gp, 'district_id', None)
                    if district_name:
                        district = db.query(location_models.District).filter(location_models.District.id == district_name).first()
                        if district:
                            district_name = getattr(district, 'name', None)
                # Occupant name from owners via build_property_response
                prop_data_full = build_property_response(prop, db, gram_panchayat_id)
                owners = prop_data_full.get('owners', [])
                # नमुना ९ क/क2 "श्री" ओळीत फक्त मालकाचे नाव हवे - भोगवटदार कंसात जोडायचा
                # नाही (तो खाली स्वतंत्र भोगवटदार ओळीत आधीच दाखवला जातो, नाहीतर same
                # नाव दोनदा छापलं जातं. see client point: owner name in brackets + duplicate भोगवटदार).
                owner_names_plain = ', '.join([o.get('name', '') or '' for o in owners]) if isinstance(owners, list) else ''
                if isinstance(owners, list) and len(owners) > 0:
                    occ = owners[0].get('occupantName') or ""
                    occupant_name = occ or "स्वतः"
        except Exception:
            gp_name = gp_name or None
            occupant_name = occupant_name or ""

        mapped.append({
            "gramPanchayat": gp_name or "",
            "parentGramPanchayat": parent_gp_name or "",
            "village": village_name or "",
            "anuKramank": anu_kramank,
            "taluka": taluka_name_ic or "",
            "district": district_name_ic or "",
            "yearSlap": yearslap,
            "propertyNumber": r.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": owner_names_plain,
            "occupantName": occupant_name,
            "bank_qr_code":bank_qr,
            "signature_image": signature_image,
            "houseTaxQrUrl": houseTaxQrUrl,
            "waterTaxQrUrl": waterTaxQrUrl,
            "houseNumber": r.get('malmattaKramank', ''),
            "exServicemanTip": bool(getattr(prop, 'exServiceman', False)) if prop else False,
            "कराचे नाव": {
                "घरकर": r.get('chaluGhar', 0),
                "दिवाबत्ती कर": r.get('chaluDiva', 0),
                "आरोग्य कर": r.get('chaluAarogyaKar', 0),
                "पाणीकर": r.get('chaluSapanikar', 0),
                "सफाई कर": r.get('chaluCleaningTax', 0),
                "नोटीस फी": r.get('noticeFee', 0),
                "वारंट फी": r.get('warrantFee', 0)
            },
            "recoverableAmounts": {
                "arrears": {"Thakit": thakit, "Dand": dand_map},
                "current": current,
                "total": total,
                "paid": paid_map
            },
            # Compute totalTax explicitly to avoid double-counting dand (already included in ekunGhar)
            "totalTax": round(
                (r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
            ),
            "totalTaxwithoutvipanitoilet": round(
                (r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
                # - (r.get('totlaToiletTax', 0) or 0)
            )
        })
    return mapped

@router.get("/recordresponses/property_records_by_village/visheshpani/")
def get_property_records_by_village_visheshpani(
    villageId: str,
    yearslap: str,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(database.get_db)
):
    # Validate location hierarchy - check if the three fields match the actual data
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    district_name_ic = getattr(district, 'name', None)
    taluka = db.query(location_models.Taluka).filter(
        location_models.Taluka.id == taluka_id,
        location_models.Taluka.district_id == district_id
    ).first()
    taluka_name_ic = getattr(taluka, 'name', None)
    if not taluka:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    gram_panchayat = db.query(location_models.GramPanchayat).filter(
        location_models.GramPanchayat.id == gram_panchayat_id,
        location_models.GramPanchayat.taluka_id == taluka_id
    ).first()
    if not gram_panchayat:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")

    # Source data exactly like the regular API
    table_rows = get_table_data(
        villageId=int(villageId),
        yearslap=yearslap,
        district_id=district_id,
        taluka_id=taluka_id,
        gram_panchayat_id=gram_panchayat_id,
        applyWarrantFee=False,
        applyNoticeFee=False,
        applyPenalty=False,
        db=db
    )
    bank_qr = None;
    from location_management import helpers
    image_path = helpers.get_gram_panchayat_image_path(db, gram_panchayat_id)
    if image_path and os.path.exists(image_path):
          bank_qr = f"{backend_url}/location/districts/{district_id}/talukas/{taluka_id}/gram-panchayats/{gram_panchayat_id}/image"
    signature_image = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/signature"
        if gram_panchayat and gram_panchayat.signature_url else None
    )
    # घर कर / पाणी कर Bank Scanner QR - only shown if the GP has turned this on
    # in Master settings (same toggle used by the namuna8Print prakar routes).
    show_bank_scanner = bool(gram_panchayat and gram_panchayat.show_bank_scanner_in_reports)
    houseTaxQrUrl = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/house"
        if show_bank_scanner and gram_panchayat and gram_panchayat.house_tax_qr_url else None
    )
    waterTaxQrUrl = (
        f"{backend_url}/location/gram-panchayats/{gram_panchayat_id}/qr/water"
        if show_bank_scanner and gram_panchayat and gram_panchayat.water_tax_qr_url else None
    )
    mapped = []
    from datetime import datetime
    for r in table_rows:
        # Build arrears/current/total same as regular
        thakit = {f"Thakit{i}": 0 for i in range(1, 8)}
        thakit["Thakit1"] = r.get('shaktiGhar', 0)
        thakit["Thakit2"] = r.get('shaktiDiva', 0)
        thakit["Thakit3"] = r.get('shaktiAarogyaKar', 0)
        thakit["Thakit4"] = r.get('shaktiSapanikar', 0)
        thakit["Thakit5"] = r.get('shaktiVpanikar', 0)
        thakit["Thakit6"] = r.get('noticeFee', 0)
        thakit["Thakit7"] = r.get('warrantFee', 0)

        current = {
            "current1": r.get('chaluGhar', 0),
            "current2": r.get('chaluDiva', 0),
            "current3": r.get('chaluAarogyaKar', 0),
            "current4": r.get('chaluSapanikar', 0),
            "current5": r.get('chaluVpanikar', 0),
            "current6": r.get('noticeFee', 0),
            "current7": r.get('warrantFee', 0)
        }
        total = {
            "total1": round(r.get('ekunGhar', 0)),
            "total2": round(r.get('ekunDiva', 0)),
            "total3": round(r.get('ekunAarogyaKar', 0)),
            "total4": round(r.get('ekunSapanikar', 0)),
            "total5": round(r.get('ekunVpanikar', 0)),
            "total6": round(r.get('noticeFee', 0)),
            "total7": round(r.get('warrantFee', 0))
        }

        # Resolve gram panchayat and occupant like regular
        gp_name = None
        village_name = None
        occupant_name = ""
        owner_names_plain = ""
        try:
            prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == r.get('property_id')).first()
            if prop:
                v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
                if v:
                    village_name = getattr(v, 'name', None)
                    gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
                    gp_name = getattr(gp, 'name', None)
                prop_data_full = build_property_response(prop, db, gram_panchayat_id)
                owners = prop_data_full.get('owners', [])
                # नमुना ९ क/क2 "श्री" ओळीत फक्त मालकाचे नाव हवे - भोगवटदार कंसात जोडायचा
                # नाही (तो खाली स्वतंत्र भोगवटदार ओळीत आधीच दाखवला जातो).
                owner_names_plain = ', '.join([o.get('name', '') or '' for o in owners]) if isinstance(owners, list) else ''
                if isinstance(owners, list) and len(owners) > 0:
                    occupant_name = owners[0].get('occupantName') or "स्वतः"
        except Exception:
            pass

        mapped.append({
            "gramPanchayat": gp_name or "",
            "village": village_name or "",
            "taluka": taluka_name_ic or "",
            "district": district_name_ic or "",
            "yearSlap": yearslap,
            "propertyNumber": r.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": owner_names_plain,
            "occupantName": occupant_name,
            "bank_qr_code":bank_qr,
            "signature_image": signature_image,
            "houseTaxQrUrl": houseTaxQrUrl,
            "waterTaxQrUrl": waterTaxQrUrl,
            "houseNumber": r.get('malmattaKramank', ''),
            "recoverableAmounts": {
                "arrears": {"Thakit": thakit, "Dand": {"Dand1": r.get('dand', 0), "Dand2": 0, "Dand3": 0, "Dand4": 0, "Dand5": 0, "Dand6": 0, "Dand7": 0}},
                "current": current,
                "total": total
            },
            # Compute total tax in line with regular API
            "totalTax": round(
                (r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunVpanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
            ),
            # Also expose without vi pani and toilet to match downstream templates
            "totalTaxwithoutvipanitoilet": round(
                ((r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
                + (r.get('ekunVpanikar', 0) or 0)
                - 0
            ))
            ,
            "totalTaxwithoutsafaitoilet": round(
                ((r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunVpanikar', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0))
            )
        })

    return mapped