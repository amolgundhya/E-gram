from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import database
from namuna9 import namuna9_model, namuna9_schemas
from namuna9.namuna9settings import Namuna9Settings
from namuna9.namuna9_schemas import Namuna9SettingsCreate, Namuna9SettingsRead, Namuna9SettingsUpdate
from namuna8 import namuna8_model
from sqlalchemy.exc import IntegrityError
from namuna8.namuna8_apis import build_property_response
from location_management import models as location_models

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

@router.get("/list", response_model=list[namuna9_schemas.Namuna9YearSetupRead])
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
    print(f"Received carry forward request: {data}")
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
        property_ids = [p.anuKramank for p in properties]
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
                namuna8_model.Property.anuKramank.in_([int(i) for i in thakit_rec.property_ids])
            ).all()
            
            # Create a map of property number to thakit data
            for thakit_prop in thakit_properties:
                thakit_prop_data = build_property_response(thakit_prop, db, gram_panchayat_id)
                thakit_constructions = db.query(namuna8_model.Construction).filter(
                    namuna8_model.Construction.property_anuKramank == thakit_prop.anuKramank
                ).all()
                
                thakit_house_tax = sum([c.houseTax or 0 for c in thakit_constructions])
                thakit_lighting_tax = thakit_prop_data.get('divaKar', 0) or 0
                thakit_health_tax = thakit_prop_data.get('aarogyaKar', 0) or thakit_prop_data.get('healthTax', 0) or 0
                thakit_sapanikar = thakit_prop_data.get('sapanikar', 0) or 0
                thakit_vpanikar = thakit_prop_data.get('vpanikar', 0) or 0
                thakit_cleaning_tax = thakit_prop_data.get('cleaningTax', 0) or 0
                
                # Calculate total for thakit year
                thakit_total = thakit_house_tax + thakit_lighting_tax + thakit_health_tax + thakit_sapanikar + thakit_vpanikar + thakit_cleaning_tax
                
                thakit_data[thakit_prop.anuKramank] = {
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
    # Fetch all property details
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids])).all()
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        # Query constructions directly for this property
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        # Calculate totalHouseTax as the sum of all houseTax in constructions (excluding 'खाली जागा')
        totalHouseTax = sum([
            c.houseTax or 0
            for c in constructions
        ])
        # Join all owner names
        owner_names = ', '.join([o.get('name', '') for o in prop_data.get('owners', [])])
        # lightingTax, healthTax, sapanikar, vpanikar, cleaningTax
        lightingTax = prop_data.get('divaKar', 0) or 0
        healthTax = prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0
        sapanikar = prop_data.get('sapanikar', 0) or 0
        vpanikar = prop_data.get('vpanikar', 0) or 0
        cleaningTax = prop_data.get('cleaningTax', 0) or 0
        
        # Initialize thakit values
        shaktiGhar = 0
        shaktiDiva = 0
        shaktiAarogyaKar = 0
        shaktiSapanikar = 0
        shaktiVpanikar = 0
        shaktiCleaningTax = 0
        
        # Apply thakit logic if enabled
        if does_thakit and thakit_values and prop.anuKramank in thakit_data:
            thakit_prop_data = thakit_data[prop.anuKramank]
            
            if thakit_values == "chaluGhar":
                # Use chalu values from thakit year as shakti
                shaktiGhar = thakit_prop_data['chaluGhar']
                shaktiDiva = thakit_prop_data['chaluDiva']
                shaktiAarogyaKar = thakit_prop_data['chaluAarogyaKar']
                shaktiSapanikar = thakit_prop_data['chaluSapanikar']
                shaktiVpanikar = thakit_prop_data['chaluVpanikar']
                shaktiCleaningTax = thakit_prop_data['chaluCleaningTax']
            elif thakit_values == "yekun":
                # Use total values from thakit year as shakti
                shaktiGhar = thakit_prop_data['chaluGhar']  # Total house tax
                shaktiDiva = thakit_prop_data['chaluDiva']  # Total lighting tax
                shaktiAarogyaKar = thakit_prop_data['chaluAarogyaKar']  # Total health tax
                shaktiSapanikar = thakit_prop_data['chaluSapanikar']  # Total sapanikar
                shaktiVpanikar = thakit_prop_data['chaluVpanikar']  # Total vpanikar
                shaktiCleaningTax = thakit_prop_data['chaluCleaningTax']  # Total cleaning tax
            elif thakit_values == "thakit":
                # Use thakit values (same as chaluGhar for now)
                shaktiGhar = thakit_prop_data['chaluGhar']
                shaktiDiva = thakit_prop_data['chaluDiva']
                shaktiAarogyaKar = thakit_prop_data['chaluAarogyaKar']
                shaktiSapanikar = thakit_prop_data['chaluSapanikar']
                shaktiVpanikar = thakit_prop_data['chaluVpanikar']
                shaktiCleaningTax = thakit_prop_data['chaluCleaningTax']
        
        # Calculate ekun (total) values
        ekunGhar = shaktiGhar + totalHouseTax
        ekunDiva = shaktiDiva + lightingTax
        ekunAarogyaKar = shaktiAarogyaKar + healthTax
        ekunSapanikar = shaktiSapanikar + sapanikar
        ekunVpanikar = shaktiVpanikar + vpanikar
        ekunCleaningTax = shaktiCleaningTax + cleaningTax
        
        # Total = sum of all numeric columns except serial, property no, owner name
        total = (
            shaktiGhar + 0 + totalHouseTax + ekunGhar + 
            shaktiDiva + lightingTax + ekunDiva + 
            shaktiAarogyaKar + healthTax + ekunAarogyaKar + 
            shaktiSapanikar + sapanikar + ekunSapanikar + 
            shaktiVpanikar + vpanikar + ekunVpanikar + 
            shaktiCleaningTax + cleaningTax + ekunCleaningTax + 
            warrant_fee + notice_fee
        )
        
        row = {
            "anukramk": idx,
            "malmattaKramank": prop_data.get('malmattaKramank', ''),
            "ownerNames": owner_names,
            "shaktiGhar": shaktiGhar,
            "dand": 0,
            "chaluGhar": totalHouseTax,
            "ekunGhar": ekunGhar,
            "totalHouseTax": totalHouseTax,
            "shaktiDiva": shaktiDiva,
            "chaluDiva": lightingTax,
            "ekunDiva": ekunDiva,
            "shaktiAarogyaKar": shaktiAarogyaKar,
            "chaluAarogyaKar": healthTax,
            "ekunAarogyaKar": ekunAarogyaKar,
            "shaktiSapanikar": shaktiSapanikar,
            "chaluSapanikar": sapanikar,
            "ekunSapanikar": ekunSapanikar,
            "shaktiVpanikar": shaktiVpanikar,
            "chaluVpanikar": vpanikar,
            "ekunVpanikar": ekunVpanikar,
            "shaktiCleaningTax": shaktiCleaningTax,
            "chaluCleaningTax": cleaningTax,
            "ekunCleaningTax": ekunCleaningTax,
            "warrantFee": warrant_fee,
            "noticeFee": notice_fee,
            "total": total,
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
    property_ids = getattr(rec, 'property_ids', None)
    if not isinstance(property_ids, list) or len(property_ids) == 0:
        return []
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.id.in_([int(i) for i in property_ids])).all()
    rows = []
    for idx, prop in enumerate(properties, 1):
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        constructions = db.query(namuna8_model.Construction).filter(
            namuna8_model.Construction.property_id == prop.id
        ).all()
        totalHouseTax = sum([
            c.houseTax or 0
            for c in constructions
        ])
        lightingTax = prop_data.get('divaKar', 0) or prop_data.get('lightingTax', 0) or 0
        healthTax = prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0
        saWaterTax = prop_data.get('sapanikar', 0) or 0
        viWaterTax = prop_data.get('vpanikar', 0) or 0
        cleaningTax = prop_data.get('cleaningTax', 0) or 0
        toiletTax = prop_data.get('toiletTax', 0) or 0
        totaltax = totalHouseTax + lightingTax + healthTax + saWaterTax + viWaterTax + cleaningTax + toiletTax
        row = {
            "id": str(prop.anuKramank),
            "srNo": idx,
            "gramPanchayat": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "taluka": None,
            "jilha": None,
            "village": prop.village.name if hasattr(prop, 'village') and prop.village else None,
            "ownerName": ', '.join([o.get('name', '') for o in prop_data.get('owners', [])]),
            "propertyNumber": prop_data.get('malmattaKramank', ''),
            "dhakitHouseTax": 0,
            "dandHouseTax": 0,
            "houseTax": totalHouseTax,
            "totalHouseTax": totalHouseTax,
            "dhakitLightingTax": 0,
            "lightingTax": lightingTax,
            "totalLightingTax": lightingTax,
            "dhakitHealthTax": 0,
            "healthTax": healthTax,
            "totalHealthTax": healthTax,
            "dhakitSaWaterTax": 0,
            "saWaterTax": saWaterTax, 
            "totalSaWaterTax": saWaterTax, 
            "dhakitViWaterTax": 0,
            "viWaterTax": viWaterTax, 
            "totalViWaterTax": viWaterTax, 
            "dhakitCleaningTax": 0,
            "cleaningTax": cleaningTax,
            "totalCleaningTax": cleaningTax,
            "dhakitToiletTax": 0,
            "toiletTax": toiletTax,
            "totlaToiletTax": toiletTax,
            "totaltax": totaltax,
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
    # Fetch Namuna9Settings for notice and warrant fee
    settings = db.query(Namuna9Settings).filter(
        Namuna9Settings.district_id == district_id,
        Namuna9Settings.taluka_id == taluka_id,
        Namuna9Settings.gram_panchayat_id == gram_panchayat_id
    ).first()
    notice_fee = settings.notice_fee if settings and settings.notice_fee is not None else 0
    warrant_fee = settings.warrant_fee if settings and settings.warrant_fee is not None else 0
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.anuKramank.in_([int(i) for i in property_ids])).all()
    rows = []
    for prop in properties:
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        owner_names = ', '.join([o.get('name', '') for o in prop_data.get('owners', [])])
        occupant_names = ', '.join([o.get('occupantName', '') for o in prop_data.get('owners', []) if o.get('occupantName', '')])
        house_number = prop_data.get('malmattaKramank', '')
        # Taxes
        house_tax = sum([(c.get('houseTax', 0) if isinstance(c, dict) else getattr(c, 'houseTax', 0) or 0) for c in getattr(prop, 'constructions', [])])
        lighting_tax = prop_data.get('divaKar', 0) or 0
        health_tax = prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0
        sapanikar = prop_data.get('sapanikar', 0) or 0
        cleaning_tax = prop_data.get('cleaningTax', 0) or 0
        # Arrears as Thakit and Dand
        thakit = {f"Thakit{i}": 0 for i in range(1, 8)}
        dand = {f"Dand{i}": 0 for i in range(1, 8)}
        arrears = {
            "Thakit": thakit,
            "Dand": dand
        }
        # Current and Total as numbered keys
        current = {
            "current1": house_tax,
            "current2": lighting_tax,
            "current3": health_tax,
            "current4": sapanikar,
            "current5": cleaning_tax,
            "current6": notice_fee,
            "current7": warrant_fee
        }
        total = {
            "total1": house_tax,
            "total2": lighting_tax,
            "total3": health_tax,
            "total4": sapanikar,
            "total5": cleaning_tax,
            "total6": notice_fee,
            "total7": warrant_fee
        }
        total_tax = sum([
            house_tax, lighting_tax, health_tax, sapanikar, cleaning_tax, notice_fee, warrant_fee
        ])
        row = {
            "gramPanchayat": prop_data.get('gramPanchayat', ''),
            "yearSlap": yearslap,
            "propertyNumber": prop_data.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": owner_names,
            "occupantName": occupant_names,
            "houseNumber": house_number,
            "कराचे नाव": {
                "घरकर": house_tax,
                "दिवाबत्ती कर": lighting_tax,
                "आरोग्य कर": health_tax,
                "पाणीकर": sapanikar,
                "सफाई कर": cleaning_tax,
                "नोटीस फी": notice_fee,
                "वारंट फी": warrant_fee
            },
            "recoverableAmounts": {
                "arrears": arrears,
                "current": current,
                "total": total
            },
            "totalTax": total_tax
        }
        rows.append(row)
    return rows 

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
    # Fetch Namuna9Settings for notice and warrant fee
    settings = db.query(Namuna9Settings).filter(
        Namuna9Settings.district_id == district_id,
        Namuna9Settings.taluka_id == taluka_id,
        Namuna9Settings.gram_panchayat_id == gram_panchayat_id
    ).first()
    notice_fee = settings.notice_fee if settings and settings.notice_fee is not None else 0
    warrant_fee = settings.warrant_fee if settings and settings.warrant_fee is not None else 0
    properties = db.query(namuna8_model.Property).filter(namuna8_model.Property.anuKramank.in_([int(i) for i in property_ids])).all()
    rows = []
    for prop in properties:
        prop_data = build_property_response(prop, db, gram_panchayat_id)
        owner_names = ', '.join([o.get('name', '') for o in prop_data.get('owners', [])])
        occupant_names = ', '.join([o.get('occupantName', '') for o in prop_data.get('owners', []) if o.get('occupantName', '')])
        house_number = prop_data.get('malmattaKramank', '')
        # Taxes
        house_tax = sum([(c.get('houseTax', 0) if isinstance(c, dict) else getattr(c, 'houseTax', 0) or 0) for c in getattr(prop, 'constructions', [])])
        lighting_tax = prop_data.get('divaKar', 0) or 0
        health_tax = prop_data.get('aarogyaKar', 0) or prop_data.get('healthTax', 0) or 0
        sapanikar = prop_data.get('sapanikar', 0) or 0
        vpanikar = prop_data.get('vpanikar', 0) or 0
        # Arrears as Thakit and Dand
        thakit = {f"Thakit{i}": 0 for i in range(1, 8)}
        dand = {f"Dand{i}": 0 for i in range(1, 8)}
        arrears = {
            "Thakit": thakit,
            "Dand": dand
        }
        # Current and Total as numbered keys (order: house, lighting, health, sapanikar, vpanikar, notice, warrant)
        current = {
            "current1": house_tax,
            "current2": lighting_tax,
            "current3": health_tax,
            "current4": sapanikar,
            "current5": vpanikar,
            "current6": notice_fee,
            "current7": warrant_fee
        }
        total = {
            "total1": house_tax,
            "total2": lighting_tax,
            "total3": health_tax,
            "total4": sapanikar,
            "total5": vpanikar,
            "total6": notice_fee,
            "total7": warrant_fee
        }
        total_tax = sum([
            house_tax, lighting_tax, health_tax, sapanikar, vpanikar, notice_fee, warrant_fee
        ])
        row = {
            "gramPanchayat": prop_data.get('gramPanchayat', ''),
            "yearSlap": yearslap,
            "propertyNumber": prop_data.get('malmattaKramank', ''),
            "currentDate": datetime.now().strftime('%Y-%m-%d'),
            "ownerName": owner_names,
            "occupantName": occupant_names,
            "houseNumber": house_number,
            "कराचे नाव": {
                "घरकर": house_tax,
                "दिवाबत्ती कर": lighting_tax,
                "आरोग्य कर": health_tax,
                "सा.पाणीकर": sapanikar,
                "वि.पाणीकर": vpanikar,
                "नोटीस फी": notice_fee,
                "वारंट फी": warrant_fee
            },
            "recoverableAmounts": {
                "arrears": arrears,
                "current": current,
                "total": total
            },
            "totalTax": total_tax
        }
        rows.append(row)
    return rows 