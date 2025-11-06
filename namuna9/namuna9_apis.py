from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
from namuna9 import namuna9_model, namuna9_schemas
from namuna9.namuna9settings import Namuna9Settings
from namuna9.namuna9_schemas import Namuna9SettingsCreate, Namuna9SettingsRead, Namuna9SettingsUpdate, Namuna9PropertyDataCreate, Namuna9PropertyDataUpdate, Namuna9PropertyDataRead, Namuna9BulkPropertyDataUpdate
from namuna8 import namuna8_model
from namuna8.mastertab import mastertabmodels as settingModels
from sqlalchemy.exc import IntegrityError
from namuna8.namuna8_apis import build_property_response
from location_management import models as location_models
from typing import List
router = APIRouter(
    prefix="/namuna9",
    tags=["namuna9"]
)

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

    return {
        "message": "Copy and update successful",
        "villageId": target.villageId,
        "fromYearslap": from_year,
        "toYearslap": to_year,
        "propertyIdsCount": len(target.property_ids or []),
        "doesThakit": True,
        "thakitValues": getattr(target, "thakitValues", None),
        "thakitYear": getattr(target, "thakitYear", None),
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

@router.get("/list", response_model=List[namuna9_schemas.Namuna9YearSetupRead])
def list_namuna9_year_setups(db: Session = Depends(database.get_db)):
    return db.query(namuna9_model.Namuna9YearSetup).all()

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
        # Get all property IDs for the given village for the current year (yearslap)
        start_year = int(yearslap.split('-')[0])
        current_year_properties = db.query(namuna8_model.Property).filter(
            namuna8_model.Property.village_id == village,
            namuna8_model.Property.created_at != None
        ).all()
        current_year_property_ids = [p.anuKramank for p in current_year_properties if p.created_at.year == start_year]
        # Combine all property IDs (avoid duplicates)
        all_property_ids = list(set(list(prev_property_ids) + current_year_property_ids))
        # Create new Namuna9 record for this yearslap
        new_namuna9 = namuna9_model.Namuna9(
            yearslap=yearslap,
            villageId=village,
            grampanchayatId=grampanchayatId,
            property_ids=all_property_ids
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
    records = db.query(namuna9_model.Namuna9).all()
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
    # Get village names for these IDs
    villages = db.query(namuna8_model.Village).filter(namuna8_model.Village.id.in_(unique_village_ids)).all()
    village_list = [{"id": v.id, "name": v.name} for v in villages]
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
    
    # Check if thakit is enabled and get thakit data
    does_thakit = getattr(rec, 'doesThakit', False)
    thakit_values = getattr(rec, 'thakitValues', None)
    thakit_year = getattr(rec, 'thakitYear', None)
    
    # If thakit is enabled, get data from thakit year
    thakit_data = {}
    if does_thakit and thakit_values and thakit_year:
        # Find the thakit year record
        thakit_rec = db.query(namuna9_model.Namuna9).filter(
            namuna9_model.Namuna9.villageId == villageId,
            namuna9_model.Namuna9.yearslap == thakit_year
        ).first()
        
        if thakit_rec and thakit_rec.property_ids:
            # Get property data from thakit year
            thakit_properties = db.query(namuna8_model.Property).filter(
                namuna8_model.Property.id.in_([int(i) for i in thakit_rec.property_ids])
            ).all()
            
            # Create a map of property number to thakit data
            for thakit_prop in thakit_properties:
                thakit_prop_data = build_property_response(thakit_prop, db, gram_panchayat_id)
                thakit_constructions = db.query(namuna8_model.Construction).filter(
                    namuna8_model.Construction.property_id == thakit_prop.id
                ).all()
                
                thakit_house_tax = sum([c.houseTax or 0 for c in thakit_constructions])
                thakit_lighting_tax = thakit_prop_data.get('divaKar', 0) or 0
                thakit_health_tax = thakit_prop_data.get('aarogyaKar', 0) or thakit_prop_data.get('healthTax', 0) or 0
                thakit_sapanikar = thakit_prop_data.get('sapanikar', 0) or 0
                thakit_vpanikar = thakit_prop_data.get('vpanikar', 0) or 0
                thakit_cleaning_tax = thakit_prop_data.get('cleaningTax', 0) or 0
                
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
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids])).all()
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        # Query constructions directly for this property
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        # Calculate totalHouseTax from constructions (includes 'खाली जागा' constructions) and add synthetic khali jaga if any leftover area exists
        totalHouseTax = sum([(c.houseTax or 0) for c in constructions])
        # Khali jaga addition similar to Namuna8 property_record_response
        vacant_land_type = getattr(prop, 'vacantLandType', None)
        if vacant_land_type not in [None, '', 'null']:
            total_area = prop.totalAreaSqFt or 0
            used_area = sum((c.length or 0) * (c.width or 0) for c in constructions)
            khali_area = max(total_area - used_area, 0)
            if khali_area > 0:
                khali_construction_type = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == "खाली जागा").first()
                if khali_construction_type:
                    userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
                    formula1 = userFormulaPreference.capitalFormula1 if userFormulaPreference else None
                    area_in_meter = khali_area * 0.092903
                    annual_land_value_rate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                    if formula1:
                        capital_value_kj = (khali_area * annual_land_value_rate)
                    else:
                        capital_value_kj = (area_in_meter * annual_land_value_rate)
                    totalHouseTax += round((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj)
        totalHouseTax = round(totalHouseTax, 2)
        # Join all owner names
        owner_names = ', '.join([o.get('name', '') for o in prop_data.get('owners', [])])
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
        
        # Apply thakit logic if enabled and no saved data
        if not saved_data and does_thakit and thakit_values and prop.id in thakit_data:
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
            ekunGhar = round(max(saved_data.ekunGhar or (max(shaktiGhar,0) + max(chaluGhar,0) + (max(dand,0) or 0)), 0), 2)
            ekunDiva = round(max(saved_data.ekunDiva or (shaktiDiva + chaluDiva), 0), 2)
            ekunAarogyaKar = round(max(saved_data.ekunAarogyaKar or (shaktiAarogyaKar + chaluAarogyaKar), 0), 2)
            ekunSapanikar = round(max(saved_data.ekunSapanikar or (shaktiSapanikar + chaluSapanikar), 0), 2)
            ekunVpanikar = round(max(saved_data.ekunVpanikar or (shaktiVpanikar + chaluVpanikar), 0), 2)
            ekunCleaningTax = round(max(saved_data.ekunCleaningTax or (shaktiCleaningTax + chaluCleaningTax), 0), 2)
        else:
            # Include dand in ekunGhar when no saved_data - ensure no negative values
            ekunGhar = round(max(max(shaktiGhar,0) + max(chaluGhar,0) + (max(dand,0)), 0), 2)
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
        
        row = {
            "anukramk": idx,
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
        rows.append(row)
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
    rec = db.query(namuna9_model.Namuna9).filter(
        namuna9_model.Namuna9.villageId == villageId,
        namuna9_model.Namuna9.yearslap == yearslap
    ).first()
    if not rec:
        return []
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
    thakit_year = getattr(rec, 'thakitYear', None)
    thakit_data = {}
    if does_thakit and thakit_values and thakit_year:
        thakit_rec = db.query(namuna9_model.Namuna9).filter(
            namuna9_model.Namuna9.villageId == villageId,
            namuna9_model.Namuna9.yearslap == thakit_year
        ).first()
        if thakit_rec and thakit_rec.property_ids:
            thakit_properties = db.query(namuna8_model.Property).filter(
                namuna8_model.Property.id.in_([int(i) for i in thakit_rec.property_ids])
            ).all()
            for thakit_prop in thakit_properties:
                thakit_prop_data = build_property_response(thakit_prop, db, gram_panchayat_id)
                thakit_constructions = db.query(namuna8_model.Construction).filter(
                    namuna8_model.Construction.property_id == thakit_prop.id
                ).all()
                t_house_tax = sum([c.houseTax or 0 for c in thakit_constructions])
                t_lighting = thakit_prop_data.get('divaKar', 0) or 0
                t_health = thakit_prop_data.get('aarogyaKar', 0) or thakit_prop_data.get('healthTax', 0) or 0
                t_sa = thakit_prop_data.get('sapanikar', 0) or 0
                t_vi = thakit_prop_data.get('vpanikar', 0) or 0
                t_clean = thakit_prop_data.get('cleaningTax', 0) or 0
                thakit_data[thakit_prop.id] = {
                    'chaluGhar': t_house_tax,
                    'chaluDiva': t_lighting,
                    'chaluAarogyaKar': t_health,
                    'chaluSapanikar': t_sa,
                    'chaluVpanikar': t_vi,
                    'chaluCleaningTax': t_clean
                }

    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids])).all()
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        # Base total house tax from constructions
        totalHouseTax = sum([(c.houseTax or 0) for c in constructions])
        # Khali jaga addition with unit handling similar to Namuna8
        vacant_land_type = getattr(prop, 'vacantLandType', None)
        if vacant_land_type not in [None, '', 'null']:
            unit = getattr(prop, 'areaUnit', 'sqft') or 'sqft'
            if unit == 'sqm':
                total_area_m = round(prop.totalArea or 0, 2)
                used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in constructions), 2)
            else:
                total_area_m = round((prop.totalAreaSqFt or 0) * 0.092903, 2)
                used_area_m = round(sum((c.length or 0) * (c.width or 0) for c in constructions) * 0.092903, 2)
            khali_area_m = round(max(total_area_m - used_area_m, 0), 2)
            khali_area = round(khali_area_m / 0.092903, 2)
            if khali_area > 0:
                khali_construction_type = db.query(namuna8_model.ConstructionType).filter(namuna8_model.ConstructionType.name == "खाली जागा").first()
                if khali_construction_type:
                    userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
                    formula1 = userFormulaPreference.capitalFormula1 if userFormulaPreference else None
                    AnnualLandValueRate = getattr(khali_construction_type, 'annualLandValueRate', 1)
                    if formula1:
                        capital_value_kj = (khali_area_m * AnnualLandValueRate)
                    else:
                        capital_value_kj = (khali_area_m * AnnualLandValueRate)
                    totalHouseTax += round((getattr(khali_construction_type, 'rate', 0) / 1000) * capital_value_kj)
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

        if not saved_data and does_thakit and thakit_values and prop.id in thakit_data:
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
            (ekunGhar or 0) + (ekunDiva or 0) + (ekunAarogyaKar or 0) +
            (ekunSapanikar or 0) + (ekunVpanikar or 0) + (ekunCleaningTax or 0) +
            (warrantFee or 0) + (noticeFee or 0)
        )
        total = round(total, 2)
        row = {
            "id": str(prop.anuKramank),
            "srNo": idx,
            "gramPanchayat": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "taluka": None,
            "jilha": None,
            "village": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "ownerName": ', '.join([o.get('name', '') for o in prop_data.get('owners', [])]),
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
            "totlaToiletTax": round(toiletTax, 2),
            "totaltax": round(total, 2),
            "totaltaxwithoutnoticwarrant": round(total - (warrantFee or 0) - (noticeFee or 0), 2),
            "totaltaxwithoutspanivpaninoticewaraant": round(
                (ekunGhar or 0) + (ekunDiva or 0) + (ekunAarogyaKar or 0)
                - 0  # clarity
                + 0  # clarity
                - 0  # clarity
                + 0  # clarity
                , 2
            ) if False else round(
                (total or 0)
                - (ekunSapanikar or 0)
                - (ekunVpanikar or 0)
                - (warrantFee or 0)
                - (noticeFee or 0)
            , 2),
            "pavatiSRKivyaTarik": 0
        }
        rows.append(row)
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
    mapped = []
    from datetime import datetime
    for r in table_rows:
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
            "total1": r.get('ekunGhar', 0),
            "total2": r.get('ekunDiva', 0),
            "total3": r.get('ekunAarogyaKar', 0),
            "total4": r.get('ekunSapanikar', 0),
            "total5": r.get('ekunVpanikar', 0),
            # For fees, show only the fee amount once in the last column
            "total6": r.get('noticeFee', 0),
            "total7": r.get('warrantFee', 0)
        }
        # Build Dand map sourced from table row (use dand in house column)
        dand_map = {f"Dand{i}": 0 for i in range(1, 8)}
        dand_map["Dand1"] = r.get('dand', 0)

        # Resolve gram panchayat name and occupant name using the property record
        gp_name = None
        occupant_name = ""
        try:
            prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == r.get('property_id')).first()
            if prop:
                # GP name from village linkage
                v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
                if v:
                    gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
                    gp_name = getattr(gp, 'name', None)
                # Occupant name from owners via build_property_response
                prop_data_full = build_property_response(prop, db, gram_panchayat_id)
                owners = prop_data_full.get('owners', [])
                if isinstance(owners, list) and len(owners) > 0:
                    occ = owners[0].get('occupantName') or ""
                    occupant_name = occ
        except Exception:
            gp_name = gp_name or None
            occupant_name = occupant_name or ""

        mapped.append({
            "gramPanchayat": gp_name or "",
            "yearSlap": yearslap,
            "propertyNumber": r.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": r.get('ownerNames', ''),
            "occupantName": occupant_name,
            "houseNumber": r.get('malmattaKramank', ''),
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
                "total": total
            },
            # Compute totalTax explicitly to avoid double-counting dand (already included in ekunGhar)
            "totalTax": (
                (r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunVpanikar', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
            ),
            "totalTaxwithoutvipanitoilet": (
                (r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0)
                - (r.get('totlaToiletTax', 0) or 0)
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
            "total1": r.get('ekunGhar', 0),
            "total2": r.get('ekunDiva', 0),
            "total3": r.get('ekunAarogyaKar', 0),
            "total4": r.get('ekunSapanikar', 0),
            "total5": r.get('ekunVpanikar', 0),
            "total6": r.get('noticeFee', 0),
            "total7": r.get('warrantFee', 0)
        }

        # Resolve gram panchayat and occupant like regular
        gp_name = None
        occupant_name = ""
        try:
            prop = db.query(namuna8_model.Property).filter(namuna8_model.Property.id == r.get('property_id')).first()
            if prop:
                v = db.query(namuna8_model.Village).filter(namuna8_model.Village.id == prop.village_id).first()
                if v:
                    gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == v.gram_panchayat_id).first()
                    gp_name = getattr(gp, 'name', None)
                prop_data_full = build_property_response(prop, db, gram_panchayat_id)
                owners = prop_data_full.get('owners', [])
                if isinstance(owners, list) and len(owners) > 0:
                    occupant_name = owners[0].get('occupantName') or ""
        except Exception:
            pass

        mapped.append({
            "gramPanchayat": gp_name or "",
            "yearSlap": yearslap,
            "propertyNumber": r.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": r.get('ownerNames', ''),
            "occupantName": occupant_name,
            "houseNumber": r.get('malmattaKramank', ''),
            "recoverableAmounts": {
                "arrears": {"Thakit": thakit, "Dand": {"Dand1": r.get('dand', 0), "Dand2": 0, "Dand3": 0, "Dand4": 0, "Dand5": 0, "Dand6": 0, "Dand7": 0}},
                "current": current,
                "total": total
            },
            # Compute total tax in line with regular API
            "totalTax": (
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
            "totalTaxwithoutvipanitoilet": (
                ((r.get('ekunGhar', 0) or 0)
                + (r.get('ekunDiva', 0) or 0)
                + (r.get('ekunAarogyaKar', 0) or 0)
                + (r.get('ekunSapanikar', 0) or 0)
                + (r.get('ekunCleaningTax', 0) or 0)
                + (r.get('warrantFee', 0) or 0)
                + (r.get('noticeFee', 0) or 0))
                - (r.get('ekunVpanikar', 0) or 0)
                - (r.get('totlaToiletTax', 0) or 0)
            )
            ,
            "totalTaxwithoutsafaitoilet": (
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