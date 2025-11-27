from fastapi import APIRouter, Depends, HTTPException, status, Body, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
import database
from namuna8 import namuna8_model as models
from namuna8.mastertab import mastertabmodels as settingModels
from namuna8 import namuna8_schemas as schemas
from fastapi.responses import JSONResponse, FileResponse
from namuna8.namuna8_schemas import PropertyReportDTO
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from namuna8.namuna8_model import Namuna8SettingTax
from sqlalchemy.exc import SQLAlchemyError
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader
import os
import shutil
import time
import re
from Utility.QRcodeGeneration import QRCodeGeneration
from namuna8.recordresponses.property_record_response import get_property_record
from namuna8.mastertab.mastertabmodels import GeneralSetting, BuildingUsageWeightage
from location_management import models as location_models
from namuna8.PropertyDocuments.property_document_model import PropertyDocument
import logging

logging.basicConfig(
    filename="namuna8_logs.txt",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter(
    prefix="/namuna8",
    tags=["namuna8"]
)



@router.post("/", response_model=schemas.PropertyRead, status_code=status.HTTP_201_CREATED)
def create_namuna8_entry(property_data: schemas.PropertyCreate, db: Session = Depends(database.get_db)):

    try:
    
        with db.begin():
            if db.query(models.Property).filter(
                models.Property.village_id == property_data.village_id,
                models.Property.anuKramank == property_data.anuKramank
            ).first():
                raise HTTPException(
                    status_code=400,
                    detail="या गावात हा अनुक्रमांक आधीच अस्तित्वात आहे / This anuKramank already exists for this village"
                )
            owners = []
            for owner_data in property_data.owners:
                # Convert dict to Pydantic model if needed
                if isinstance(owner_data, dict):
                    owner_data = schemas.OwnerCreate(**owner_data)
                db_owner = None
                owner_id = getattr(owner_data, 'id', None)
                if owner_id:
                    db_owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
                elif owner_data.aadhaarNumber:
                    db_owner = db.query(models.Owner).filter(models.Owner.aadhaarNumber == owner_data.aadhaarNumber).first()
                if db_owner:
                    # Optionally update fields if needed
                    db_owner.name = owner_data.name
                    if owner_data.mobileNumber is not None:
                        db_owner.mobileNumber = owner_data.mobileNumber
                    if owner_data.wifeName is not None:
                        db_owner.wifeName = owner_data.wifeName
                    if owner_data.occupantName is not None:
                        db_owner.occupantName = owner_data.occupantName
                    db.flush()
                    owners.append(db_owner)
                else:
                    # Debug logging for owner creation
                    owner_district_id = getattr(property_data, 'district_id', None)
                    owner_taluka_id = getattr(property_data, 'taluka_id', None)
                    owner_gram_panchayat_id = getattr(property_data, 'gram_panchayat_id', None)
                    
                    new_owner = models.Owner(
                        name=owner_data.name,
                        aadhaarNumber=owner_data.aadhaarNumber,
                        mobileNumber=owner_data.mobileNumber,
                        wifeName=owner_data.wifeName,
                        occupantName=owner_data.occupantName,
                        ownerPhoto=getattr(owner_data, 'ownerPhoto', None) if getattr(owner_data, 'ownerPhoto', None) is not None and isinstance(getattr(owner_data, 'ownerPhoto', None), str) and getattr(owner_data, 'ownerPhoto', None) != '' else None,
                        village_id=owner_data.village_id,
                        district_id=owner_district_id,
                        taluka_id=owner_taluka_id,
                        gram_panchayat_id=owner_gram_panchayat_id
                    )
                    new_owner.created_at = datetime.now()
                    db.add(new_owner)
                    db.flush()
                    owners.append(new_owner)
            if not property_data.malmattaKramank or str(property_data.malmattaKramank).strip() == "":
                raise HTTPException(
                    status_code=400,
                    detail="मालमत्ता क्रमांक रिक्त असू शकत नाही / Malmatta Kramank should not be null or empty"
                )
            if db.query(models.Property).filter(
                models.Property.village_id == property_data.village_id,
                models.Property.malmattaKramank == property_data.malmattaKramank).first():
                raise HTTPException(
                    status_code=400,
                    detail="मालमत्ता क्रमांक आधीच या आयडीसह अस्तित्वात आहे / Malmatta Kramank already exists with this ID"
                )
            # --- FIX: Convert constructions dicts to model instances ---
            constructions = []
            for construction_data in property_data.constructions:
                if isinstance(construction_data, dict):
                    construction_data = schemas.ConstructionCreate(**construction_data)
                construction_type = db.query(models.ConstructionType).filter_by(name=construction_data.constructionType).first()
                if not construction_type:
                    raise HTTPException(status_code=400, detail=f"Invalid construction type: {construction_data.constructionType}")
                # Calculate capitalValue and houseTax as per user instruction
                
                
                userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
                
                if userFormulaPreference:
                    formula1 = userFormulaPreference.capitalFormula1
                    formula2 = userFormulaPreference.capitalFormula2
                else:
                    # print("No user formula preference found")
                    pass
                   
                # capital_value = 0
                AnnualLandValueRate = getattr(construction_type, 'annualLandValueRate', 1)
                # for capital_value calculation: respect frontend area unit
                unit = getattr(property_data, 'areaUnit', 'sqft')
                if unit == 'sqm':
                    AreaInMeter = (construction_data.length or 0) * (construction_data.width or 0)
                else:
                    AreaInMeter = (construction_data.length or 0) * (construction_data.width or 0) * 0.092903
                ConstructionRateAsPerConstruction = construction_type.bandhmastache_dar
                depreciationRate = calculate_depreciation_rate(construction_data.constructionYear, construction_type.name)
                # Before using usageBasedBuildingWeightageFactor, build the mapping
                weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
                usageBasedBuildingWeightageFactor = weightage_map.get(getattr(construction_data, 'bharank', None), 1)
                if formula1:
                    # capital_value = (( ((construction_data.length * 0.092903) * (construction_data.width * 0.092903)) * AnnualLandValueRate ) + ( ((construction_data.length * 0.092903) * (construction_data.width * 0.092903)) * ConstructionRateAsPerConstruction * (depreciationRate/100))) * usageBasedBuildingWeightageFactor
                    capital_value = (( ((AreaInMeter)) * AnnualLandValueRate ) + ( ((AreaInMeter)) * ConstructionRateAsPerConstruction * (depreciationRate/100))) * usageBasedBuildingWeightageFactor
                    # capital_value = (( AreaInMeter * AnnualLandValueRate ) + ( AreaInMeter * ConstructionRateAsPerConstruction * depreciationRate)) * usageBasedBuildingWeightageFactor
                    capital_value = round(capital_value, 2)
                    # print("capital_value_from_formula1" , capital_value)
                else:
                    capital_value = (AreaInMeter) * AnnualLandValueRate * depreciationRate/100 * usageBasedBuildingWeightageFactor
                    capital_value = round(capital_value, 2)
                    # print("capital_value_from_formula2" , capital_value)
                    
                    
                house_tax = round((getattr(construction_type, 'rate', 0) / 1000) * capital_value, 2)
                
                # Debug logging for construction creation
                construction_district_id = getattr(property_data, 'district_id', None)
                construction_taluka_id = getattr(property_data, 'taluka_id', None)
                construction_gram_panchayat_id = getattr(property_data, 'gram_panchayat_id', None)
              
                
                new_construction = models.Construction(
                    construction_type_id=construction_type.id,
                    length=construction_data.length,
                    width=construction_data.width,
                    constructionYear=construction_data.constructionYear,
                    floor=construction_data.floor,
                    bharank=construction_data.bharank,
                    capitalValue=capital_value,
                    houseTax=house_tax,
                    district_id=construction_district_id,
                    taluka_id=construction_taluka_id,
                    gram_panchayat_id=construction_gram_panchayat_id
                )
                constructions.append(new_construction)
            # --- END FIX ---

            # --- ADDITION: Handle vacant land construction if needed ---
            vacant_land_type = property_data.vacantLandType
            # print("vacant " + str(vacant_land_type))
            has_khali_jaga = False
            for c in constructions:
                ctype = db.query(models.ConstructionType).filter_by(id=c.construction_type_id).first()
                if ctype and ctype.name.strip().startswith("खाली जागा"):
                    has_khali_jaga = True
                    break
            if not has_khali_jaga:
                # Use totalAreaSqFt if present, otherwise fallback to totalArea, otherwise calculate from lengths
                total_area = getattr(property_data, 'totalAreaSqFt', None)
                if total_area is None or total_area == 0:
                    total_area = getattr(property_data, 'totalArea', None)
                if total_area is None or total_area == 0:
                    east = getattr(property_data, 'eastLength', 0) or 0
                    west = getattr(property_data, 'westLength', 0) or 0
                    north = getattr(property_data, 'northLength', 0) or 0
                    south = getattr(property_data, 'southLength', 0) or 0
                    try:
                        avg_length = (float(east) + float(west)) / 2 if east or west else 0
                        avg_width = (float(north) + float(south)) / 2 if north or south else 0
                        total_area = avg_length * avg_width if avg_length and avg_width else 0
                    except (TypeError, ValueError):
                        logging.info("Khalijaga issue")
                        total_area = 0
                try:
                    total_area = float(total_area)
                except (TypeError, ValueError):
                    total_area = 0

                # Sum all construction areas, converting to float
                used_area = sum(
                    float(getattr(c, 'length', 0) or 0) * float(getattr(c, 'width', 0) or 0)
                    for c in constructions
                )
                remaining_area = total_area - used_area
              
            property_dict = property_data.dict(exclude={"owners", "constructions"})
            # Normalize totalAreaSqFt based on areaUnit to avoid double-conversion later
            if "totalArea" in property_dict and property_dict["totalArea"] is not None:
                try:
                    area_val = float(property_dict["totalArea"]) or 0.0
                except (TypeError, ValueError):
                    area_val = 0.0
                area_unit = property_dict.get("areaUnit", "sqft") or "sqft"
                if area_unit == "sqm":
                    property_dict["totalAreaSqFt"] = round(area_val * 10.7639, 2)
                else:
                    property_dict["totalAreaSqFt"] = round(area_val, 2)
            
            # Handle vacantLandType field - convert empty string to None
            if "vacantLandType" in property_dict and property_dict["vacantLandType"] == "":
                property_dict["vacantLandType"] = None
            
            # Handle case sensitivity issue - check for vacantLandtype (lowercase t)
            if "vacantLandtype" in property_dict:
                property_dict["vacantLandType"] = property_dict.pop("vacantLandtype")
                if property_dict["vacantLandType"] == "":
                    property_dict["vacantLandType"] = None
            
            # Additional validation for vacantLandType
            if "vacantLandType" in property_dict:
                if property_dict["vacantLandType"] is not None and not isinstance(property_dict["vacantLandType"], str):
                    property_dict["vacantLandType"] = str(property_dict["vacantLandType"])
                if property_dict["vacantLandType"] == "" or property_dict["vacantLandType"] is None:
                    property_dict["vacantLandType"] = None
            
            # Ensure vacantLandType is properly set even if not in dict
            if "vacantLandType" not in property_dict:
                property_dict["vacantLandType"] = None
            
          
            try:
                db_property = models.Property(**property_dict, owners=owners, constructions=constructions)
                db_property.created_at = datetime.now()
                
                db.add(db_property)
            except Exception as e:
                raise e
            # Ensure totalAreaSqFt is set on the db_property object before saving (rounded to 2 decimals)
            if not db_property.totalAreaSqFt or db_property.totalAreaSqFt == 0:
                east = db_property.eastLength or 0
                west = db_property.westLength or 0
                north = db_property.northLength or 0
                south = db_property.southLength or 0
                area_unit = getattr(property_data, 'areaUnit', 'sqft') or 'sqft'
                if east == 0 and west == 0 and north == 0 and south == 0:
                    # All lengths empty, use totalArea from payload with unit awareness
                    base_area = float(property_data.totalArea or 0)
                    if area_unit == 'sqm':
                        db_property.totalAreaSqFt = round(base_area * 10.7639, 2)
                    else:
                        db_property.totalAreaSqFt = round(base_area, 2)
                else:
                    avg_length = (east + west) / 2
                    avg_width = (north + south) / 2
                    computed_area = (avg_length * avg_width) if (avg_length and avg_width) else 0
                    if area_unit == 'sqm':
                        db_property.totalAreaSqFt = round(computed_area * 10.7639, 2)
                    else:
                        db_property.totalAreaSqFt = round(computed_area, 2)
            # Only set boolean fields and toilet (not calculated tax fields)
            db_property.divaArogyaKar = bool(property_data.divaArogyaKar)
            db_property.safaiKar = bool(property_data.safaiKar)
            db_property.shauchalayKar = bool(property_data.shauchalayKar)
            db_property.toilet = property_data.toilet if property_data.toilet is not None else ''
            try:
                db.flush()
                # print(f"DEBUG: Database flush successful")
                db.refresh(db_property)
                # print(f"DEBUG: Property refreshed successfully")
                # print(f"DEBUG: Final vacantLandType value: {getattr(db_property, 'vacantLandType', 'NOT_FOUND')}")
            except Exception as e:
                # print(f"DEBUG: Error during database flush: {e}")
                raise e
            # Build response with constructionType name
            response = build_property_response(db_property, db, property_data.gram_panchayat_id)
          
            try:
                # Use get_property_record to get accurate total tax
                # Match update method signature: (anuKramank, village_id, district_id, taluka_id, gram_panchayat_id, db)
                record_response = get_property_record(
                    db_property.anuKramank,
                    db_property.village_id,
                    db_property.district_id,
                    db_property.taluka_id,
                    db_property.gram_panchayat_id,
                    db
                )
              
                vpanikar_qr = record_response.get('vpanikar',0)
                totalTax_qr = record_response.get('totaltax',0)
                # electricityTax = record_response.get('electricityTax', 0)
                totalTax = totalTax_qr - vpanikar_qr
                srNo = response.get('anuKramank') or response.get('srNo') or ''
                # totalArea = avg_length * avg_width if avg_length and avg_width else 0
                totalArea = round(record_response.get('totalArea', 0) or 0, 2)
                owner_name = owners[0].name if owners else None
                wife_name = owners[0].wifeName if owners and getattr(owners[0], "wifeName", None) else None
                occupant_name = owners[0].occupantName if owners and getattr(owners[0], "occupantName", None) else record_response.get('occupantName')
                mobile_number = owners[0].mobileNumber if owners and getattr(owners[0], "mobileNumber", None) else record_response.get('mobileNumber')
                # Construction area (exclude 'खाली जागा')
                constructionArea = sum(
                    (c['length'] or 0) * (c['width'] or 0)
                    for c in response.get('constructions', [])
                    if not (c.get('constructionType', '').strip().startswith('खाली जागा'))
                )
                constructionArea = round(constructionArea, 2)
                # Open area: totalArea - constructionArea
                openArea = round(totalArea - constructionArea, 2)
                # Boundaries (prefer record response, fallback to property)
                boundary_east = record_response.get('boundaryEast') or getattr(db_property, 'eastBoundary', None)
                boundary_west = record_response.get('boundaryWest') or getattr(db_property, 'westBoundary', None)
                boundary_north = record_response.get('boundaryNorth') or getattr(db_property, 'northBoundary', None)
                boundary_south = record_response.get('boundarySouth') or getattr(db_property, 'southBoundary', None)


                def safe_name(value: str) -> str:
                        try:
                            import re
                            value = value.strip()
                            # replace spaces with underscores and remove disallowed chars
                            value = re.sub(r"\s+", "_", value)
                            value = re.sub(r"[^\w\-\.\u0900-\u097F]", "", value)  # allow Devanagari
                            return value[:80] if len(value) > 80 else value
                        except Exception:
                            return str(value)


                district = db.query(location_models.District).filter(location_models.District.id == db_property.district_id).first()
                taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == db_property.taluka_id).first()
                gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == db_property.gram_panchayat_id).first()
                village = db.query(models.Village).filter(models.Village.id == db_property.village_id).first()

                district_name = safe_name(district.name if district else str(db_property.district_id))
                taluka_name = safe_name(taluka.name if taluka else str(db_property.taluka_id))
                gp_name = safe_name(gram_panchayat.name if gram_panchayat else str(db_property.gram_panchayat_id))

                qr_data = {
                    # Marathi labels for QR display
                    "अनुक्रमांक": getattr(db_property, 'anuKramank', None),
                    "मालकाचे नाव": owner_name,
                    # "mobileNumber": mobile_number,
                    "एकूण क्षेत्रफळ": totalArea,
                    "बांधकाम क्षेत्रफळ": constructionArea,
                    "खुली जागा": openArea,
                    "एकूण कर": totalTax,
                }
                if wife_name:
                    qr_data["पत्नीचे नाव"] = wife_name
                # Create location-based QR directory structure
                qr_dir = os.path.join("uploaded_images", "qrcode", str(db_property.district_id), str(db_property.taluka_id), str(db_property.gram_panchayat_id),str(db_property.village_id),str(db_property.anuKramank))
                # print(f"DEBUG: Creating QR directory: {qr_dir}")
                os.makedirs(qr_dir, exist_ok=True)
                qr_path = os.path.join(qr_dir, "qrcode.png") 
                QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)  
                db_property.qrcode = qr_path.replace(os.sep, "/")
                db.flush()
                logging.info("QR code generated successfully")
                
                ### For generating QR Template ###
                try:
                    ###Creating new QRcode for template
                    # Ensure area values are strictly in square feet for the QR template
                    area_unit_for_template = getattr(db_property, 'areaUnit', 'sqft') or 'sqft'
                    total_area_sqft = round(float(getattr(db_property, 'totalAreaSqFt', 0) or totalArea or 0), 2)
                    construction_area_sqft = round((constructionArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((constructionArea or 0), 2)
                    open_area_sqft = round((openArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((openArea or 0), 2)
                    year_from = datetime.now().year
                    year_to = year_from + 3
                    # Display like 2025-26 (two-digit end year)
                    fer_akarnani_year = f"{str(year_from)}-{str(year_to)}"

                    qr_data_template = {
                        # Marathi labels for QR display
                        "ग्रा. पं.": gp_name,
                        "ता.": taluka_name,
                        "जि.": district_name,
                        "मा क्र": getattr(db_property, 'malmattaKramank', None),
                        "मा. धा. नाव": owner_name,
                        "भो. नाव": occupant_name,
                        "पू.": boundary_east,
                        "प.": boundary_west,
                        "उ.": boundary_north,
                        "द.": boundary_south,
                        "मो नं": mobile_number,
                        "ए क्षे. चौ. फू": total_area_sqft,
                        "ए बां. चौ. फू": construction_area_sqft,
                        "ए खा .जागा चौ.फू": open_area_sqft,
                        "ए कर": totalTax,
                    }
                    if wife_name:
                        qr_data_template["पत्नीचे नाव"] = wife_name
                    qr_path_template = os.path.join(qr_dir, "qrcode_template.png")
                    QRCodeGeneration.createQRcodeTemp(qr_data_template, qr_path_template)
                    #get template
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))    
                    template_dir = os.path.join(base_dir, 'templates')  
                    namuna8_template_dir = os.path.join(template_dir ,'Namuna8' )
                    env = Environment(loader=FileSystemLoader(namuna8_template_dir))
                    template = env.get_template('qrTemplate.html')

                    # save location using NAMES rather than IDs
                    def safe_name(value: str) -> str:
                        try:
                            import re
                            value = value.strip()
                            # replace spaces with underscores and remove disallowed chars
                            value = re.sub(r"\s+", "_", value)
                            value = re.sub(r"[^\w\-\.\u0900-\u097F]", "", value)  # allow Devanagari
                            return value[:80] if len(value) > 80 else value
                        except Exception:
                            return str(value)

                    district = db.query(location_models.District).filter(location_models.District.id == db_property.district_id).first()
                    taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == db_property.taluka_id).first()
                    gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == db_property.gram_panchayat_id).first()
                    village = db.query(models.Village).filter(models.Village.id == db_property.village_id).first()

                    district_name = safe_name(district.name if district else str(db_property.district_id))
                    taluka_name = safe_name(taluka.name if taluka else str(db_property.taluka_id))
                    gp_name = safe_name(gram_panchayat.name if gram_panchayat else str(db_property.gram_panchayat_id))
                    village_name = safe_name(village.name if village else str(db_property.village_id))

                    qr_template_dir = os.path.join(
                        "uploaded_images",
                        "qrTemplate",
                        district_name,
                        taluka_name,
                        gp_name,
                        village_name,
                    )
                    os.makedirs(qr_template_dir, exist_ok=True)

                    #create qr template with data
                    report_images_dir = os.path.join(base_dir, 'ReportImages')
                    reports_dir = os.path.join(base_dir, 'reports')
                    rel_report_images = os.path.relpath(report_images_dir, start=qr_template_dir)
                    rel_reports = os.path.relpath(reports_dir, start=qr_template_dir)
                    
                    # Convert NEW template QR code path to relative path (use qrcode_template.png)
                    qr_code_abs_path = os.path.abspath(qr_path_template)
                    rel_qrcode = os.path.relpath(qr_code_abs_path, start=qr_template_dir)

                    context = {
                        # IDs
                        "district_id": str(db_property.district_id),
                        "taluka_id": str(db_property.taluka_id),
                        "gram_panchayat_id": str(db_property.gram_panchayat_id),
                        "village_id": str(db_property.village_id),
                        # Names
                        "district_name": district.name if district else "",
                        "taluka_name": taluka.name if taluka else "",
                        "gram_panchayat_name": gram_panchayat.name if gram_panchayat else "",
                        "village_name": village.name if village else "",
                        "owner_name": owner_name,
                        # Others
                        "malmatta_kramank": getattr(db_property, 'malmattaKramank', None),
                        "report_images": rel_report_images,
                        "reports": rel_reports,
                        "qrcode": rel_qrcode,
                    }
                    rendered_html = template.render(**context)
                    qr_template_path = os.path.join(qr_template_dir , f'qr_template_{str(db_property.anuKramank)}.html')
                    with open(qr_template_path , 'w' , encoding='utf-8') as f:
                        f.write(rendered_html)


                   


                except Exception as e:
                    logging.error(f"Error in generating the qr template : " , e)
        ### For generating QR Template ###
            except Exception as e:
                logging.error(f"QR code generation failed: {e}")
               
            return response
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error during property creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save property and owners: " + str(e))
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error during property creation: {e}")
        raise HTTPException(status_code=500, detail="Failed to save property and owners: " + str(e))

@router.get("/property_list/", response_model=list[schemas.PropertyList])
def get_property_list(village: str, db: Session = Depends(database.get_db)):
    # Find the village by name
    village_obj = db.query(models.Village).filter(models.Village.name == village).first()
    if not village_obj:
        return []
    properties = db.query(models.Property).filter(models.Property.village_id == village_obj.id).all()
    result = []
    for p in properties:
        if p.owners:
            owner_name = ','.join([f"{i+1}.{o.name}" for i, o in enumerate(p.owners)])
            holderno = p.owners[0].holderno if hasattr(p.owners[0], 'holderno') else None
        else:
            owner_name = "N/A"
            holderno = None
        result.append({
            "malmattaKramank": p.malmattaKramank,
            "ownerName": owner_name,
            "anuKramank": p.anuKramank,
            "holderno": holderno
        })
    return result

@router.get("/get-all-constructiontypes", response_model=List[schemas.ConstructionType])
def get_all_construction_types(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    taluka_id: Optional[int] = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: Optional[int] = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.ConstructionType)
    
    # Apply location filters if provided
    if district_id is not None:
        query = query.filter(models.ConstructionType.district_id == district_id)
    if taluka_id is not None:
        query = query.filter(models.ConstructionType.taluka_id == taluka_id)
    if gram_panchayat_id is not None:
        query = query.filter(models.ConstructionType.gram_panchayat_id == gram_panchayat_id)
    
    return query.all()

@router.get("/{anu_kramank}", response_model=schemas.PropertyRead)
def get_property_details(
    anu_kramank: int,
    village_id:int,
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
    
    db_property = db.query(models.Property).filter(
        models.Property.village_id == village_id,
        models.Property.anuKramank == anu_kramank,
        models.Property.district_id == district_id,
        models.Property.taluka_id == taluka_id,
        models.Property.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")
    return build_property_response(db_property, db, gram_panchayat_id)

@router.put("/{anu_kramank}", response_model=schemas.PropertyRead)
def update_namuna8_entry(
    anu_kramank: int, 
    property_data: schemas.PropertyUpdate,
    village_id: int, 
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(database.get_db)
):
    # Map totalArea to totalAreaSqFt based on areaUnit if provided
    property_update_data = property_data.dict(exclude={'owners', 'constructions'})
    if "totalArea" in property_update_data and property_update_data["totalArea"] is not None:
        try:
            area_val = float(property_update_data["totalArea"]) or 0.0
        except (TypeError, ValueError):
            area_val = 0.0
        area_unit = property_update_data.get("areaUnit", "sqft") or "sqft"
        if area_unit == "sqm":
            property_update_data["totalAreaSqFt"] = round(area_val * 10.7639, 2)
        else:
            property_update_data["totalAreaSqFt"] = round(area_val, 2)
    # Validate location hierarchy
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
    if db.query(models.Property).filter(
                models.Property.village_id == property_data.village_id,
                models.Property.anuKramank == property_data.anuKramank,
                models.Property.id != property_data.id
            ).first():
                raise HTTPException(
                    status_code=400,
                    detail="या गावात हा अनुक्रमांक आधीच अस्तित्वात आहे / This anuKramank already exists for this village"
                )
    db_property = db.query(models.Property).filter(
        models.Property.village_id == village_id,
        models.Property.anuKramank == anu_kramank,
        models.Property.district_id == district_id,
        models.Property.taluka_id == taluka_id,
        models.Property.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found in the specified location")
    
    # Store old anuKramank before updating
    old_anu_kramank = db_property.anuKramank
    
    # Validate malmattaKramank duplication in the same village if it's being changed
    new_malmatta_kramank = property_update_data.get('malmattaKramank')
    current_malmatta_kramank = getattr(db_property, 'malmattaKramank', None)
    if new_malmatta_kramank is not None:
        new_malmatta_kramank = str(new_malmatta_kramank).strip()
    if new_malmatta_kramank:
        # Only validate if the value is actually changing
        if str(current_malmatta_kramank).strip() != new_malmatta_kramank:
            existing_property = db.query(models.Property).filter(
                models.Property.village_id == village_id,
                models.Property.malmattaKramank == new_malmatta_kramank,
                models.Property.id != db_property.id
            ).first()
            if existing_property:
                raise HTTPException(
                    status_code=400,
                    detail="मालमत्ता क्रमांक आधीच या गावात अस्तित्वात आहे / Malmatta Kramank already exists in this village"
                )
    
    for key, value in property_update_data.items():
        setattr(db_property, key, value)
    db_property.updated_at = datetime.now()
    # After setting all fields, recalculate totalAreaSqFt from lengths with unit awareness (rounded to 2 decimals)
    try:
        east = float(db_property.eastLength) if db_property.eastLength is not None else 0
        west = float(db_property.westLength) if db_property.westLength is not None else 0
        north = float(db_property.northLength) if db_property.northLength is not None else 0
        south = float(db_property.southLength) if db_property.southLength is not None else 0

        area_unit = getattr(property_data, 'areaUnit', getattr(db_property, 'areaUnit', 'sqft')) or 'sqft'
        if east == 0 and west == 0 and north == 0 and south == 0:
            # Fallback to totalArea when no side lengths are available
            base_area = float(db_property.totalArea or 0)
            if area_unit == 'sqm':
                db_property.totalAreaSqFt = round(base_area * 10.7639, 2)
            else:
                db_property.totalAreaSqFt = round(base_area, 2)
        else:
            avg_length = (east + west) / 2 if (east or west) else 0
            avg_width = (north + south) / 2 if (north or south) else 0
            computed_area = (avg_length * avg_width) if (avg_length and avg_width) else 0
            if area_unit == 'sqm':
                db_property.totalAreaSqFt = round(computed_area * 10.7639, 2)
            else:
                db_property.totalAreaSqFt = round(computed_area, 2)

    except Exception:
        db_property.totalAreaSqFt = round(db_property.totalArea or 0, 2)

    # Update property document paths if anuKramank is changed
    new_anu_kramank = property_update_data.get('anuKramank', old_anu_kramank)
    if new_anu_kramank is not None and old_anu_kramank != new_anu_kramank:
        try:
            # Find all property documents for this property
            property_docs = db.query(PropertyDocument).filter(
                PropertyDocument.property_anuKramank.in_([old_anu_kramank, str(old_anu_kramank)]),
                PropertyDocument.village_id == village_id
            ).all()
            
            if property_docs:
                UPLOAD_DIR = "uploaded_images/property_documents"
                old_dir = os.path.join(UPLOAD_DIR, str(village_id), str(old_anu_kramank))
                new_dir = os.path.join(UPLOAD_DIR, str(village_id), str(new_anu_kramank))
                
                # Create new directory if it doesn't exist
                if not os.path.exists(new_dir):
                    os.makedirs(new_dir, exist_ok=True)
                
                # Update each document
                for doc in property_docs:
                    # Update document_image path if exists
                    if doc.document_image:
                        old_image_path = doc.document_image
                        # Convert to absolute path if relative
                        if not os.path.isabs(old_image_path):
                            old_image_path = os.path.join(os.getcwd(), old_image_path)
                        
                        if os.path.exists(old_image_path):
                            # Extract filename from old path
                            filename = os.path.basename(old_image_path)
                            new_image_path = os.path.join(new_dir, filename)
                            
                            # Move file
                            try:
                                shutil.move(old_image_path, new_image_path)
                                # Update database path (relative path with forward slashes)
                                rel_new_path = os.path.relpath(new_image_path, start=os.getcwd()).replace(os.sep, "/")
                                doc.document_image = rel_new_path
                            except Exception as e:
                                logging.error(f"Error moving document_image: {e}")
                    
                    # Update document_path if exists
                    if doc.document_path:
                        old_doc_path = doc.document_path
                        # Convert to absolute path if relative
                        if not os.path.isabs(old_doc_path):
                            old_doc_path = os.path.join(os.getcwd(), old_doc_path)
                        
                        if os.path.exists(old_doc_path):
                            # Extract filename from old path
                            filename = os.path.basename(old_doc_path)
                            new_doc_path = os.path.join(new_dir, filename)
                            
                            # Move file
                            try:
                                shutil.move(old_doc_path, new_doc_path)
                                # Update database path (relative path with forward slashes)
                                rel_new_path = os.path.relpath(new_doc_path, start=os.getcwd()).replace(os.sep, "/")
                                doc.document_path = rel_new_path
                            except Exception as e:
                                logging.error(f"Error moving document_path: {e}")
                    
                    # Update property_anuKramank in database
                    doc.property_anuKramank = new_anu_kramank
                
                # Try to remove old directory if empty
                try:
                    if os.path.exists(old_dir) and not os.listdir(old_dir):
                        os.rmdir(old_dir)
                except Exception:
                    pass
        except Exception as e:
            logging.error(f"Error updating property document paths: {e}")
            # Don't raise exception, just log the error to not block the property update

    if property_data.owners:
        new_owners = []
        for owner_data in property_data.owners:
            # Accept dict or Pydantic model
            if isinstance(owner_data, dict):
                owner_data = schemas.OwnerUpdate(**owner_data)
            owner_id = getattr(owner_data, 'id', None)
            owner = None
            if owner_id is not None:
                # Ensure owner_id is an integer for matching
                if isinstance(owner_id, str) and owner_id.isdigit():
                    owner_id = int(owner_id)
                elif isinstance(owner_id, float):
                    owner_id = int(owner_id)
                owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
            if owner:
                # Update existing owner fields
                owner.name = owner_data.name
                if owner_data.aadhaarNumber is not None:
                    owner.aadhaarNumber = owner_data.aadhaarNumber
                if owner_data.mobileNumber is not None:
                    owner.mobileNumber = owner_data.mobileNumber
                if owner_data.wifeName is not None:
                    owner.wifeName = owner_data.wifeName
                if owner_data.occupantName is not None:
                    owner.occupantName = owner_data.occupantName
                owner_photo_val = getattr(owner_data, 'ownerPhoto', None)
                if owner_photo_val is not None and isinstance(owner_photo_val, str) and owner_photo_val != '':
                    owner.ownerPhoto = owner_photo_val
                if owner_data.village_id is not None:
                    owner.village_id = owner_data.village_id
                owner.updated_at = datetime.now()
                db.commit()
                new_owners.append(owner)
            else:
                # Always create new owner if id is null or does not match
                owner = models.Owner(
                    name=owner_data.name,
                    aadhaarNumber=owner_data.aadhaarNumber,
                    mobileNumber=owner_data.mobileNumber,
                    wifeName=owner_data.wifeName,
                    occupantName=owner_data.occupantName,
                    ownerPhoto=getattr(owner_data, 'ownerPhoto', None) if getattr(owner_data, 'ownerPhoto', None) is not None and isinstance(getattr(owner_data, 'ownerPhoto', None), str) and getattr(owner_data, 'ownerPhoto', None) != '' else None,
                    village_id=owner_data.village_id,
                    district_id=getattr(property_data, 'district_id', None),
                    taluka_id=getattr(property_data, 'taluka_id', None),
                    gram_panchayat_id=getattr(property_data, 'gram_panchayat_id', None)
                )
                db.add(owner)
                db.commit()
                db.refresh(owner)
                new_owners.append(owner)
        db_property.owners = new_owners

    # --- FIX: Convert constructions dicts to model instances ---
    if property_data.constructions:
        new_constructions = []
        for construction_data in property_data.constructions:
            if isinstance(construction_data, dict):
                construction_data = schemas.ConstructionCreate(**construction_data)
            construction_type = db.query(models.ConstructionType).filter_by(name=construction_data.constructionType).first()
            if not construction_type:
                raise HTTPException(status_code=400, detail=f"Invalid construction type: {construction_data.constructionType}")
            
            userFormulaPreference = db.query(settingModels.GeneralSetting).filter_by().first()
            if userFormulaPreference:
                    formula1 = userFormulaPreference.capitalFormula1
                    formula2 = userFormulaPreference.capitalFormula2
            else:
                # print("No user formula preference found")
                pass
                
            # capital_value = 0
            AnnualLandValueRate = getattr(construction_type, 'annualLandValueRate', 1)
            # for capital_value calculation: respect frontend area unit
            unit = getattr(property_data, 'areaUnit', 'sqft')
            if unit == 'sqm':
                AreaInMeter = (construction_data.length or 0) * (construction_data.width or 0)
            else:
                AreaInMeter = (construction_data.length or 0) * (construction_data.width or 0) * 0.092903
            ConstructionRateAsPerConstruction = construction_type.bandhmastache_dar
            depreciationRate = calculate_depreciation_rate(construction_data.constructionYear, construction_type.name)
            # Before using usageBasedBuildingWeightageFactor, build the mapping
            weightage_map = {row.building_usage: row.weightage for row in db.query(BuildingUsageWeightage).all()}
            usageBasedBuildingWeightageFactor = weightage_map.get(getattr(construction_data, 'bharank', None), 1)
            if formula1:
                capital_value =(( ((AreaInMeter)) * AnnualLandValueRate ) + ( ((AreaInMeter)) * ConstructionRateAsPerConstruction * (depreciationRate/100))) * usageBasedBuildingWeightageFactor
                # capital_value = (( AreaInMeter * AnnualLandValueRate ) + ( AreaInMeter * ConstructionRateAsPerConstruction * depreciationRate)) * usageBasedBuildingWeightageFactor
                capital_value = round(capital_value, 2)
                # print("capital_value_from_formula1" , capital_value)
            else:
                capital_value = (AreaInMeter) * AnnualLandValueRate * depreciationRate/100 * usageBasedBuildingWeightageFactor
                capital_value = round(capital_value, 2)
                    
            house_tax = round((getattr(construction_type, 'rate', 0) / 1000) * capital_value  ,2)
            new_construction = models.Construction(
                construction_type_id=construction_type.id,
                length=construction_data.length,
                width=construction_data.width,
                constructionYear=construction_data.constructionYear,
                floor=construction_data.floor,
                bharank=construction_data.bharank,
                capitalValue=capital_value,
                houseTax=house_tax,
                district_id=getattr(property_data, 'district_id', None),
                taluka_id=getattr(property_data, 'taluka_id', None),
                gram_panchayat_id=getattr(property_data, 'gram_panchayat_id', None)
            )
            new_constructions.append(new_construction)
        # --- ADDITION: Handle vacant land construction if needed (like POST) ---
        vacant_land_type = getattr(property_data, 'vacantLandType', None)
        has_khali_jaga = False
        for c in new_constructions:
            ctype = db.query(models.ConstructionType).filter_by(id=c.construction_type_id).first()
            if ctype and ctype.name.strip().startswith("खाली जागा"):
                has_khali_jaga = True
                break
        if not has_khali_jaga and vacant_land_type:
            total_area = getattr(property_data, 'totalAreaSqFt', None)
            if total_area is None or total_area == 0:
                total_area = getattr(property_data, 'totalArea', None)
            if total_area is None or total_area == 0:
                east = getattr(property_data, 'eastLength', 0) or 0
                west = getattr(property_data, 'westLength', 0) or 0
                north = getattr(property_data, 'northLength', 0) or 0
                south = getattr(property_data, 'southLength', 0) or 0
                try:
                    avg_length = (float(east) + float(west)) / 2 if east or west else 0
                    avg_width = (float(north) + float(south)) / 2 if north or south else 0
                    total_area = avg_length * avg_width if avg_length and avg_width else 0
                except (TypeError, ValueError):
                    total_area = 0
            try:
                total_area = float(total_area)
            except (TypeError, ValueError):
                total_area = 0
            used_area = sum(
                float(getattr(c, 'length', 0) or 0) * float(getattr(c, 'width', 0) or 0)
                for c in new_constructions
            )
            remaining_area = total_area - used_area
            # if remaining_area > 0:
            #     vacant_type_obj = db.query(models.ConstructionType).filter(models.ConstructionType.name == vacant_land_type).first()
            #     if vacant_type_obj:
            #         length = remaining_area
            #         width = 1
            #         constructionYear = str(datetime.now().year)
            #         floor = "तळमजला"
            #         # bharank = "औद्योगिक"
            #         if new_constructions:
            #             bharank = new_constructions[-1].bharank
            #         else:
            #             bharank = None
            #         AreaInMeter = length * width * 0.092903
            #         AnnualLandValueRate = 1000
            #         ConstructionRateAsPerConstruction = vacant_type_obj.bandhmastache_dar
            #         depreciationRate = calculate_depreciation_rate(constructionYear, vacant_type_obj.name)
            #         usageBasedBuildingWeightageFactor = 1
            #         capital_value = (( AreaInMeter * AnnualLandValueRate ) + ( AreaInMeter * ConstructionRateAsPerConstruction * depreciationRate)) * usageBasedBuildingWeightageFactor
            #         house_tax = round((getattr(vacant_type_obj, 'rate', 0) / 1000) * capital_value)
            #         new_vacant_land = models.Construction(
            #             construction_type_id=vacant_type_obj.id,
            #             length=length,
            #             width=width,
            #             constructionYear=constructionYear,
            #             floor=floor,
            #             bharank=bharank,
            #             capitalValue=capital_value,
            #             houseTax=house_tax,
            #             district_id=getattr(property_data, 'district_id', None),
            #             taluka_id=getattr(property_data, 'taluka_id', None),
            #             gram_panchayat_id=getattr(property_data, 'gram_panchayat_id', None)
            #         )
            #         new_constructions.append(new_vacant_land)
        # --- END ADDITION ---
        db_property.constructions = new_constructions
    # --- END FIX ---

    db_property.divaArogyaKar = bool(property_data.divaArogyaKar)
    db_property.safaiKar = bool(property_data.safaiKar)
    db_property.shauchalayKar = bool(property_data.shauchalayKar)
    db_property.toilet = property_data.toilet if property_data.toilet is not None else ''

    db.commit()
    db.refresh(db_property)
    # Build response with constructionType name
    response = build_property_response(db_property, db, db_property.gram_panchayat_id)
    # --- QR CODE GENERATION (after update, using calculated values) ---
    try:
        # Use get_property_record to get accurate total tax
        record_response = get_property_record(db_property.anuKramank,village_id, district_id, taluka_id, gram_panchayat_id, db)
       
        vpanikar_qr = record_response.get('vpanikar',0)
        totalTax_qr = record_response.get('totaltax',0)
        # electricityTax = record_response.get('electricityTax', 0)
        totalTax = totalTax_qr - vpanikar_qr
        srNo = response.get('anuKramank') or response.get('srNo') or ''
      
        east = db_property.eastLength or 0
        west = db_property.westLength or 0
        north = db_property.northLength or 0
        south = db_property.southLength or 0
        avg_length = (east + west) / 2 if (east or west) else 0
        avg_width = (north + south) / 2 if (north or south) else 0
        area_unit = getattr(db_property, 'areaUnit', 'sqft') or 'sqft'
        totalArea_calc = avg_length * avg_width if avg_length and avg_width else 0
        # totalArea in response should follow record_response's convention; we use record_response below
        if area_unit == 'sqm':
            totalArea = round(totalArea_calc, 2)
        else:
            totalArea = round(totalArea_calc, 2)
        constructionArea = sum(
            (c['length'] or 0) * (c['width'] or 0)
            for c in response.get('constructions', [])
            if not (c.get('constructionType', '').strip().startswith('खाली जागा'))
        )
        constructionArea = round(constructionArea, 2)
        openArea = round(totalArea - constructionArea, 2)
        owner_name = record_response.get('ownerName', 0)
        wife_name = record_response.get('ownerWifeName', 0)
        occupant_name = record_response.get('occupantName', 0)
        totalArea = round(record_response.get('totalArea', 0) or 0, 2)
        mobile_number = record_response.get('mobileNumber')

        # Boundaries (prefer record response, fallback to property)
        boundary_east = record_response.get('boundaryEast') or getattr(db_property, 'eastBoundary', None)
        boundary_west = record_response.get('boundaryWest') or getattr(db_property, 'westBoundary', None)
        boundary_north = record_response.get('boundaryNorth') or getattr(db_property, 'northBoundary', None)
        boundary_south = record_response.get('boundarySouth') or getattr(db_property, 'southBoundary', None)

        qr_data = {
                    # Marathi labels for QR display
            "अनुक्रमांक": getattr(db_property, 'anuKramank', None),
            "मालकाचे नाव": owner_name,
            # "mobileNumber": mobile_number,
            "एकूण क्षेत्रफळ": totalArea,
            "बांधकाम क्षेत्रफळ": constructionArea,
            "खुली जागा": openArea,
            "एकूण कर": totalTax,
        }
        if wife_name:
            qr_data["पत्नीचे नाव"] = wife_name
        
        # Create location-based QR directory structure
        qr_dir = os.path.join("uploaded_images", "qrcode", str(db_property.district_id), str(db_property.taluka_id), str(db_property.gram_panchayat_id),str(db_property.village_id), str(db_property.anuKramank))
        # print(f"DEBUG UPDATE: Creating QR directory: {qr_dir}")
        os.makedirs(qr_dir, exist_ok=True)
        qr_path = os.path.join(qr_dir, "qrcode.png")
        # print(f"DEBUG UPDATE: QR path: {qr_path}")
        # print(f"DEBUG UPDATE: QR data: {qr_data}")
        QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
        # print(f"DEBUG UPDATE: QR code generated successfully")
        db_property.qrcode = qr_path.replace(os.sep, "/")
        db.commit()
        
        ### For generating QR Template ###
        try:
            ###Creating new QRcode for template
            # Ensure area values are strictly in square feet for the QR template
            area_unit_for_template = getattr(db_property, 'areaUnit', 'sqft') or 'sqft'
            total_area_sqft = round(float(getattr(db_property, 'totalAreaSqFt', 0) or totalArea or 0), 2)
            construction_area_sqft = round((constructionArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((constructionArea or 0), 2)
            open_area_sqft = round((openArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((openArea or 0), 2)
            year_from = datetime.now().year
            year_to = year_from + 3
            # Display like 2025-26 (two-digit end year)
            fer_akarnani_year = f"{str(year_from)}-{str(year_to)}"

            # Resolve location names early (used below in qr_data_template)
            def safe_name(value: str) -> str:
                try:
                    import re
                    value = value.strip()
                    # replace spaces with underscores and remove disallowed chars
                    value = re.sub(r"\s+", "_", value)
                    value = re.sub(r"[^\w\-\.\u0900-\u097F]", "", value)  # allow Devanagari
                    return value[:80] if len(value) > 80 else value
                except Exception:
                    return str(value)

            district = db.query(location_models.District).filter(location_models.District.id == db_property.district_id).first()
            taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == db_property.taluka_id).first()
            gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == db_property.gram_panchayat_id).first()
            village = db.query(models.Village).filter(models.Village.id == db_property.village_id).first()

            district_name = safe_name(district.name if district else str(db_property.district_id))
            taluka_name = safe_name(taluka.name if taluka else str(db_property.taluka_id))
            gp_name = safe_name(gram_panchayat.name if gram_panchayat else str(db_property.gram_panchayat_id))
            village_name = safe_name(village.name if village else str(db_property.village_id))

            qr_data_template = {
                # Marathi labels for QR display
                "ग्रा. पं.": gp_name,
                "ता.": taluka_name,
                "जि.": district_name,
                "मा क्र": getattr(db_property, 'malmattaKramank', None),
                "मा. धा. नाव": owner_name,
                "भो. नाव": occupant_name,
                "पू.": boundary_east,
                "प.": boundary_west,
                "उ.": boundary_north,
                "द.": boundary_south,
                "मो नं": mobile_number,
                "ए क्षे. चौ. फू": total_area_sqft,
                "ए बां. चौ. फू": construction_area_sqft,
                "ए खा .जागा चौ.फू": open_area_sqft,
                "ए कर": totalTax,
            }
            if wife_name:
                qr_data_template["पत्नीचे नाव"] = wife_name
            qr_path_template = os.path.join(qr_dir, "qrcode_template.png")
            QRCodeGeneration.createQRcodeTemp(qr_data_template, qr_path_template)
            #get template
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            template_dir = os.path.join(base_dir, 'templates')
            namuna8_template_dir = os.path.join(template_dir ,'Namuna8' )
            env = Environment(loader=FileSystemLoader(namuna8_template_dir))
            template = env.get_template('qrTemplate.html')

            # names already computed above
            qr_template_dir = os.path.join(
                "uploaded_images",
                "qrTemplate",
                district_name,
                taluka_name,
                gp_name,
                village_name,
            )
            os.makedirs(qr_template_dir, exist_ok=True)

            #create qr template with data
            report_images_dir = os.path.join(base_dir, 'ReportImages')
            reports_dir = os.path.join(base_dir, 'reports')
            rel_report_images = os.path.relpath(report_images_dir, start=qr_template_dir)
            rel_reports = os.path.relpath(reports_dir, start=qr_template_dir)
            
            # Convert NEW template QR code path to relative path (use qrcode_template.png)
            qr_code_abs_path = os.path.abspath(qr_path_template)
            rel_qrcode = os.path.relpath(qr_code_abs_path, start=qr_template_dir)

            context = {
                # IDs
                "district_id": str(db_property.district_id),
                "taluka_id": str(db_property.taluka_id),
                "gram_panchayat_id": str(db_property.gram_panchayat_id),
                "village_id": str(db_property.village_id),
                # Names
                "district_name": district.name if district else "",
                "taluka_name": taluka.name if taluka else "",
                "gram_panchayat_name": gram_panchayat.name if gram_panchayat else "",
                "village_name": village.name if village else "",
                "owner_name": owner_name,
                # Others
                "malmatta_kramank": getattr(db_property, 'malmattaKramank', None),
                "report_images": rel_report_images,
                "reports": rel_reports,
                "qrcode": rel_qrcode,
            }
            rendered_html = template.render(**context)
            qr_template_path = os.path.join(qr_template_dir , f'qr_template_{str(db_property.anuKramank)}.html')
            with open(qr_template_path , 'w' , encoding='utf-8') as f:
                f.write(rendered_html)


            
        except Exception as e:
            logging.error("Error in generating the qr template : %s", e)
       
    except Exception as e:
        logging.error(f"QR code update failed: {e}")
    return response

@router.get("/bulk_edit_list/", response_model=list[schemas.BulkEditPropertyRow])
def get_bulk_edit_property_list(
    village: str, 
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
    village_obj = db.query(models.Village).filter(models.Village.name == village).first()
    if not village_obj:
        return []
    properties = db.query(models.Property).filter(models.Property.village_id == village_obj.id).order_by(models.Property.malmattaKramank).all()
    # Prepare settings for tax and water calculations - filter by gram_panchayat_id
    settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    water_settings = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    water_slab_settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    def get_tax_by_area(area, field):
        if not settings:
            return 0
        if area is None:
            area = 0
        if area <= 300:
            return getattr(settings, field + 'Upto300', 0) or 0
        elif 301 <= area <= 700:
            return getattr(settings, field + '301_700', 0) or 0
        else:
            return getattr(settings, field + 'Above700', 0) or 0
    def get_water_facility_price(facility):
        if not facility:
            return 0
        if not water_settings or not water_slab_settings:
            return 0
        # Accept both spellings for 'सामान्य पाणीकर' and 'सामान्य पाणीकर'
        if facility in ['सामान्य पाणीकर', 'सामान्य पाणीकर']:
            return getattr(water_settings, 'generalWater', 0)
        elif facility == 'घरगुती नळ':
            return getattr(water_settings, 'houseTax', 0)
        elif facility == 'व्यावसायिक नळ':
            return getattr(water_settings, 'commercialTax', 0)
        elif facility == 'करास पात्र नसलेली इमारत':
            return getattr(water_settings, 'exemptRate', 0)
        elif facility == 'सामान्य पाणीकर १ ते ३०० चौ. फु.':
            return getattr(water_slab_settings, 'generalWaterUpto300', 0)
        elif facility == 'सामान्य पाणीकर ३०१ ते ७०० चौ. फु.':
            return getattr(water_slab_settings, 'generalWater301_700', 0)
        elif facility == 'सामान्य पाणीकर ७०० चौ. फु. वरील':
            return getattr(water_slab_settings, 'generalWaterAbove700', 0)
        return 0
    result = []
    for idx, p in enumerate(properties, start=1):
        owner_name = p.owners[0].name if p.owners else ""
        total_area = p.totalAreaSqFt or 0
        divaArogyaKar = bool(getattr(p, 'divaArogyaKar', False))
        result.append(schemas.BulkEditPropertyRow(
            serial_no=idx,
            id = p.id ,
            anukramank=getattr(p, 'anuKramank', None),
            malmattaKramank=p.malmattaKramank,
            ownerName=owner_name,
            occupant="स्वतः",  # Always 'self' for now
            gharKar=sum([c.houseTax or 0 for c in p.constructions]),
            divaKar=get_tax_by_area(total_area, 'light') if not divaArogyaKar else 0,
            aarogyaKar=get_tax_by_area(total_area, 'health') if not divaArogyaKar else 0,
            sapanikar=get_water_facility_price(getattr(p, 'waterFacility1', None)),
            vpanikar=get_water_facility_price(getattr(p, 'waterFacility2', None)),
        ))
    return result

@router.post("/bulk_update/")
def bulk_update_properties(update: schemas.BulkEditUpdateRequest, db: Session = Depends(database.get_db)):
    valid_water_facilities = [
        "सामान्य पाणीकर",
        "घरगुती नळ",
        "व्यावसायिक नळ",
        "करास पात्र नसलेली इमारत",
        "सामान्य पाणीकर १ ते ३०० चौ. फु.",
        "सामान्य पाणीकर ३०१ ते ७०० चौ. फु.",
        "सामान्य पाणीकर ७०० चौ. फु. वरील",
        None
    ]
    updated_count = 0
    for prop_id in update.property_ids:
        prop = db.query(models.Property).filter(models.Property.id == prop_id).first()
        if not prop:
            continue
        # Only update fields that are not None
        if update.waterFacility1 is not None:
            if update.waterFacility1 in valid_water_facilities:
                prop.waterFacility1 = update.waterFacility1
            else:
                continue  # skip invalid value
        if update.waterFacility2 is not None:
            if update.waterFacility2 in valid_water_facilities:
                prop.waterFacility2 = update.waterFacility2
            else:
                continue  # skip invalid value
        if update.toilet is not None:
            prop.toilet = update.toilet
        if update.roofType is not None:
            prop.roofType = update.roofType
        if update.house is not None:
            prop.house = update.house
        if update.divaArogyaKar is not None:
            prop.divaArogyaKar = update.divaArogyaKar
        if update.safaiKar is not None:
            prop.safaiKar = update.safaiKar
        if update.shauchalayKar is not None:
            prop.shauchalayKar = update.shauchalayKar
        if update.karLaguNahi is not None:
            prop.karLaguNahi = update.karLaguNahi
        updated_count += 1
    db.commit()
    return {"message": f"Updated {updated_count} properties successfully."}

# @router.get("/property_report_list/")
# def get_property_report_list(village: str, db: Session = Depends(database.get_db)):
#     properties = db.query(models.Property).filter(models.Property.villageOrMoholla == village).all()
#     rows = []
#     for prop in properties:
#         # Compose owner names
#         owner_names = []
#         for idx, owner in enumerate(prop.owners, start=1):
#             owner_names.append(f"{idx}.{owner.name}")
#         owner_name_str = ", ".join(owner_names) if owner_names else None
#         # Compose dimension string
#         dimension = None
#         if prop.eastLength or prop.westLength or prop.northLength or prop.southLength:
#             dimension = f"{prop.eastLength or ''} x {prop.westLength or ''} x {prop.northLength or ''} x {prop.southLength or ''}"
#         # Area calculation (example: product of lengths, adjust as needed)
#         area_sqft_sqm = None
#         if prop.eastLength and prop.northLength:
#             try:
#                 area_sqft = float(prop.eastLength) * float(prop.northLength)
#                 area_sqft_sqm = str(area_sqft)
#             except Exception:
#                 area_sqft_sqm = None
#         dto = PropertyReportDTO(
#             sr_no=prop.anuKramank,
#             village_info=prop.villageOrMoholla,
#             owner_name=owner_name_str,
#             occupant_name=prop.owners[0].occupantName if prop.owners and hasattr(prop.owners[0], 'occupantName') else None,
#             property_description=None,
#             property_numbers=str(prop.malmattaKramank) if prop.malmattaKramank else None,
#             dimension=dimension,
#             area_sqft_sqm=area_sqft_sqm,
#             rate_per_sqm=None,
#             depreciation_info=None,
#             tax_rate_paise=None,
#             capital_value=None,
#             tax_percentage=None,
#             tax_amount_rupees=None,
#             land_tax=None,
#             building_tax=None,
#             construction_tax=None,
#             house_tax=str(prop.gharKar) if prop.gharKar is not None else None,
#             light_tax=str(prop.divaKar) if prop.divaKar is not None else None,
#             total_tax=None
#         )
#         rows.append(dto.dict())
#     return JSONResponse(status_code=200, content={"success": True, "message": "Property report list fetched successfully", "data": rows})

@router.post("/construction_type/", response_model=schemas.ConstructionType, status_code=status.HTTP_201_CREATED)
def create_construction_type(construction_type_data: schemas.ConstructionTypeCreate, db: Session = Depends(database.get_db)):
    new_construction_type = models.ConstructionType(**construction_type_data.dict())
    db.add(new_construction_type)
    db.commit()
    db.refresh(new_construction_type)
    return new_construction_type

@router.post("/owner", status_code=status.HTTP_201_CREATED)
def create_owner(
    name: str = Body(...),
    aadhaarNumber: str = Body(None),
    mobileNumber: str = Body(...),
    village_id: int = Body(...),
    wifeName: str = Body(None),
    district_id: int = Body(...),
    taluka_id: int = Body(...),
    gram_panchayat_id: int = Body(...),
    db: Session = Depends(database.get_db)
):
    # Check if owner with same aadhaarNumber exists, only if aadhaarNumber is provided
    if aadhaarNumber not in (None, ""):
        existing_owner = db.query(models.Owner).filter(models.Owner.aadhaarNumber == aadhaarNumber).first()
        if existing_owner:
            return {"detail": "Owner with this Aadhaar number already exists."}
    new_owner = models.Owner(
        name=name,
        aadhaarNumber=aadhaarNumber,
        mobileNumber=mobileNumber,
        wifeName=wifeName,
        village_id=village_id,
        district_id=district_id,
        taluka_id=taluka_id,
        gram_panchayat_id=gram_panchayat_id
    )
    db.add(new_owner)
    db.commit()
    db.refresh(new_owner)
    return {
        "id": new_owner.id,
        "name": new_owner.name,
        "aadhaarNumber": new_owner.aadhaarNumber,
        "mobileNumber": new_owner.mobileNumber,
        "wifeName": new_owner.wifeName,
        "village_id": new_owner.village_id
    }

# @router.post("/owners/upload_photo/", response_model=str)
# def upload_owner_photo(owner_id: int = Form(...), file: UploadFile = File(...)):
#     from sqlalchemy.orm import Session
#     from database import get_db
#     import re
    
#     db: Session = next(get_db())
    
#     try:
#         # print(f"DEBUG: Starting photo upload for owner_id: {owner_id}")
        
#         # Get owner to find location information
#         owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
#         if not owner:
#             # print(f"DEBUG: Owner not found with id: {owner_id}")
#             raise HTTPException(status_code=400, detail="Owner not found")
        
#         # print(f"DEBUG: Found owner: {owner.name}, district_id: {owner.district_id}, taluka_id: {owner.taluka_id}, gram_panchayat_id: {owner.gram_panchayat_id}")
        
#         # Validate that owner has location information
#         if not owner.district_id or not owner.taluka_id or not owner.gram_panchayat_id:
#             # print(f"DEBUG: Owner missing location information")
#             raise HTTPException(status_code=400, detail="Owner must have complete location information (district_id, taluka_id, gram_panchayat_id)")
        
#         # Create directory structure: uploaded_images/owners/{district_id}/{taluka_id}/{gram_panchayat_id}/{owner_id}/
#         image_dir = os.path.join("uploaded_images", "owners", str(owner.district_id), str(owner.taluka_id), str(owner.gram_panchayat_id), str(owner_id))
#         # print(f"DEBUG: Creating directory: {image_dir}")
        
#         # Ensure the directory exists
#         os.makedirs(image_dir, exist_ok=True)
#         # print(f"DEBUG: Directory created successfully")
        
#         # Sanitize owner name for filename
#         ownername = re.sub(r'[^\w\-_]', '_', owner.name) if owner.name else f"owner_{owner_id}"
#         # print(f"DEBUG: Sanitized owner name: {ownername}")
        
#         # Get file extension
#         ext = os.path.splitext(file.filename)[1] if file.filename else ''
#         filename = f"{ownername}{ext}"
#         # print(f"DEBUG: Filename: {filename}")
        
#         file_path = os.path.join(image_dir, filename)
#         # print(f"DEBUG: Full file path: {file_path}")
        
#         # Save the file
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#         # print(f"DEBUG: File saved successfully")
        
#         # Convert to forward slashes for database storage
#         file_location = file_path.replace(os.sep, '/')
#         # print(f"DEBUG: Database file location: {file_location}")
        
#         # Update the owner's photo path in the database
#         owner.ownerPhoto = file_location
#         print(owner.ownerPhoto)
#         db.commit()
#         # print(f"DEBUG: Database updated successfully")
        
#         return file_location
#     except Exception as e:
#         # print(f"DEBUG: Error occurred: {str(e)}")
#         # print(f"DEBUG: Error type: {type(e)}")
#         import traceback
#         # print(f"DEBUG: Traceback: {traceback.format_exc()}")
#         raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")

@router.post("/owners/upload_photo/", response_model=str)
def upload_owner_photo(owner_id: int = Form(...), file: UploadFile = File(...)):
    from sqlalchemy.orm import Session
    from database import get_db
    import re
    import time
    
    db: Session = next(get_db())
    
    try:
        # Get owner to find location information
        owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
        if not owner:
            raise HTTPException(status_code=400, detail="Owner not found")
        
        # Validate that owner has location information
        if not owner.district_id or not owner.taluka_id or not owner.gram_panchayat_id:
            raise HTTPException(
                status_code=400,
                detail="Owner must have complete location information (district_id, taluka_id, gram_panchayat_id)"
            )
        
        # Create directory structure
        image_dir = os.path.join(
            "uploaded_images", "owners",
            str(owner.district_id),
            str(owner.taluka_id),
            str(owner.gram_panchayat_id),
            str(owner_id)
        )
        os.makedirs(image_dir, exist_ok=True)
        
        # Sanitize owner name
        ownername = re.sub(r'[^\w\-_]', '_', owner.name) if owner.name else f"owner_{owner_id}"
        
        # Get file extension
        ext = os.path.splitext(file.filename)[1] if file.filename else ''
        
        # Add timestamp to make filename unique
        timestamp = int(time.time())
        filename = f"{ownername}_{timestamp}{ext}"
        
        file_path = os.path.join(image_dir, filename)
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Convert to forward slashes for DB
        file_location = file_path.replace(os.sep, '/')
        
        # Update DB with latest photo path
        owner.ownerPhoto = file_location
        db.commit()
        
        return file_location
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"Error uploading photo: {str(e)}")


def build_property_response(db_property, db, gram_panchayat_id: int):
    # Build constructions with constructionType name
    constructions = []
    for c in db_property.constructions:
        constructions.append({
            "id": c.id,
            "constructionType": c.construction_type.name if c.construction_type else "",
            "length": c.length,
            "width": c.width,
            "constructionYear": c.constructionYear,
            "floor": c.floor,
            "bharank": c.bharank,
            "district_id": c.district_id,
            "taluka_id": c.taluka_id,
            "gram_panchayat_id": c.gram_panchayat_id,
        })
    # Build owners as needed
    owners = []
    for o in db_property.owners:
        owners.append({
            "id": o.id,
            "name": o.name,
            "aadhaarNumber": o.aadhaarNumber,
            "mobileNumber": o.mobileNumber,
            "wifeName": o.wifeName,
            "occupantName": o.occupantName,
            "ownerPhoto": o.ownerPhoto,
            "village_id": o.village_id,
            "district_id": o.district_id,
            "taluka_id": o.taluka_id,
            "gram_panchayat_id": o.gram_panchayat_id,
        })
    # Calculate taxes and water charges on the fly - filter by gram_panchayat_id
    settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    water_settings = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    water_slab_settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    def get_tax_by_area(area, field):
        if not settings:
            return 0
        if area is None:
            area = 0
        if area <= 300:
            return getattr(settings, field + 'Upto300', 0) or 0
        elif 301 <= area <= 700:
            return getattr(settings, field + '301_700', 0) or 0
        else:
            return getattr(settings, field + 'Above700', 0) or 0
    def get_water_facility_price(facility):
        if not facility:
            return 0
        if not water_settings or not water_slab_settings:
            return 0
        # Accept both spellings for 'सामान्य पाणीकर' and 'सामान्य पाणीकर'
        if facility in ['सामान्य पाणीकर', 'सामान्य पाणीकर']:
            return getattr(water_settings, 'generalWater', 0)
        elif facility == 'घरगुती नळ':
            return getattr(water_settings, 'houseTax', 0)
        elif facility == 'व्यावसायिक नळ':
            return getattr(water_settings, 'commercialTax', 0)
        elif facility == 'करास पात्र नसलेली इमारत':
            return getattr(water_settings, 'exemptRate', 0)
        elif facility == 'सामान्य पाणीकर १ ते ३०० चौ. फु.':
            return getattr(water_slab_settings, 'generalWaterUpto300', 0)
        elif facility == ['सामान्य पाणीकर ३०१ ते ७०० चौ. फु.','सामान्य पाणीकर ३०१ ते ७०० चौ. फु.']:
            return getattr(water_slab_settings, 'generalWater301_700', 0)
        elif facility == ['सामान्य पाणीकर ७०० चौ. फु. वरील','सामान्य पाणीकर ७०० चौ. फु. वरील']:
            return getattr(water_slab_settings, 'generalWaterAbove700', 0)
        return 0
    total_area = db_property.totalAreaSqFt or 0
    divaArogyaKar = bool(getattr(db_property, 'divaArogyaKar', False))
    safaiKar = bool(getattr(db_property, 'safaiKar', False))
    shauchalayKar = bool(getattr(db_property, 'shauchalayKar', False))
    karLaguNahi = bool(getattr(db_property, 'karLaguNahi', False))
    property_dict = {
        **{k: getattr(db_property, k) for k in schemas.PropertyBase.__fields__.keys()},
        "owners": owners,
        "constructions": constructions,
        "divaKar": 0 if karLaguNahi else (get_tax_by_area(total_area, 'light') if not divaArogyaKar else 0),
        "aarogyaKar": 0 if karLaguNahi else (get_tax_by_area(total_area, 'health') if not divaArogyaKar else 0),
        "cleaningTax": 0 if karLaguNahi else (get_tax_by_area(total_area, 'cleaning') if safaiKar else 0),
        "toiletTax": 0.0 if karLaguNahi else (get_tax_by_area(total_area, 'bathroom') if shauchalayKar else 0.0),
        "sapanikar": 0 if karLaguNahi else get_water_facility_price(getattr(db_property, 'waterFacility1', None)),
        "vpanikar": 0 if karLaguNahi else get_water_facility_price(getattr(db_property, 'waterFacility2', None)),
    }
    return property_dict


# --- Namuna8SettingChecklist CRUD ---
@router.post("/settings/checklist/save", response_model=schemas.Namuna8SettingChecklistRead)
def create_checklist(data: schemas.Namuna8SettingChecklistCreate, db: Session = Depends(database.get_db)):
    if not data.gram_panchayat_id:
        raise HTTPException(status_code=400, detail="gram_panchayat_id is required")
    
    obj = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == data.gram_panchayat_id).first()
    if obj:
        for k, v in data.dict().items():
            setattr(obj, k, v)
    else:
        obj = models.Namuna8SettingChecklist(**data.dict())
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/settings/checklist/getall", response_model=list[schemas.Namuna8SettingChecklistRead])
def get_all_checklists(db: Session = Depends(database.get_db)):
    return db.query(models.Namuna8SettingChecklist).all()

@router.get("/settings/checklist/get/{gram_panchayat_id}", response_model=schemas.Namuna8SettingChecklistRead)
def get_checklist(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Checklist not found")
    return obj

@router.put("/settings/checklist/update/{gram_panchayat_id}", response_model=schemas.Namuna8SettingChecklistRead)
def update_checklist(gram_panchayat_id: int, data: schemas.Namuna8SettingChecklistCreate, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Checklist not found")
    for k, v in data.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/settings/checklist/delete/{gram_panchayat_id}")
def delete_checklist(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Checklist not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Deleted"}

# --- Namuna8DropdownAddSettings CRUD ---
@router.post("/settings/dropdown/save", response_model=schemas.Namuna8DropdownAddSettingsRead)
def create_dropdown(data: schemas.Namuna8DropdownAddSettingsCreate, db: Session = Depends(database.get_db)):
    if not data.gram_panchayat_id:
        raise HTTPException(status_code=400, detail="gram_panchayat_id is required")
    
    obj = db.query(models.Namuna8DropdownAddSettings).filter(models.Namuna8DropdownAddSettings.gram_panchayat_id == data.gram_panchayat_id).first()
    if obj:
        for k, v in data.dict().items():
            setattr(obj, k, v)
    else:
        obj = models.Namuna8DropdownAddSettings(**data.dict())
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/settings/dropdown/getall", response_model=list[schemas.Namuna8DropdownAddSettingsRead])
def get_all_dropdowns(db: Session = Depends(database.get_db)):
    return db.query(models.Namuna8DropdownAddSettings).all()

@router.get("/settings/dropdown/get/{gram_panchayat_id}", response_model=schemas.Namuna8DropdownAddSettingsRead)
def get_dropdown(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8DropdownAddSettings).filter(models.Namuna8DropdownAddSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Dropdown setting not found")
    return obj

@router.put("/settings/dropdown/update/{gram_panchayat_id}", response_model=schemas.Namuna8DropdownAddSettingsRead)
def update_dropdown(gram_panchayat_id: int, data: schemas.Namuna8DropdownAddSettingsCreate, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8DropdownAddSettings).filter(models.Namuna8DropdownAddSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Dropdown setting not found")
    for k, v in data.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/settings/dropdown/delete/{gram_panchayat_id}")
def delete_dropdown(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8DropdownAddSettings).filter(models.Namuna8DropdownAddSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Dropdown setting not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Deleted"}

# --- Namuna8SettingTax CRUD ---
@router.post("/settings/tax/save", response_model=schemas.Namuna8SettingTaxRead)
def create_tax(data: schemas.Namuna8SettingTaxCreate, db: Session = Depends(database.get_db)):
    if not data.gram_panchayat_id:
        raise HTTPException(status_code=400, detail="gram_panchayat_id is required")
    
    obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == data.gram_panchayat_id).first()
    if obj:
        for k, v in data.dict().items():
            setattr(obj, k, v)
    else:
        obj = models.Namuna8SettingTax(**data.dict())
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/settings/tax/getall", response_model=list[schemas.Namuna8SettingTaxRead])
def get_all_taxes(db: Session = Depends(database.get_db)):
    return db.query(models.Namuna8SettingTax).all()

@router.get("/settings/tax/get/{gram_panchayat_id}", response_model=schemas.Namuna8SettingTaxRead)
def get_tax(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    return obj

@router.put("/settings/tax/update/{gram_panchayat_id}", response_model=schemas.Namuna8SettingTaxRead)
def update_tax(gram_panchayat_id: int, data: schemas.Namuna8SettingTaxCreate, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    for k, v in data.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/settings/tax/delete/{gram_panchayat_id}")
def delete_tax(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Tax setting not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Deleted"}

@router.get("/settings/tax/waterslab/fields", response_model=dict)
def get_water_slab_fields(
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(database.get_db)
):
    obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        return {"generalWaterUpto300": 0, "generalWater301_700": 0, "generalWaterAbove700": 0}
    return {
        "generalWaterUpto300": obj.generalWaterUpto300,
        "generalWater301_700": obj.generalWater301_700,
        "generalWaterAbove700": obj.generalWaterAbove700
    }

# --- Namuna8WaterTaxSettings CRUD ---
@router.post("/settings/watertax/save", response_model=schemas.Namuna8WaterTaxSettingsRead)
def create_watertax(data: schemas.Namuna8WaterTaxSettingsCreate, db: Session = Depends(database.get_db)):
    if not data.gram_panchayat_id:
        raise HTTPException(status_code=400, detail="gram_panchayat_id is required")
    
    obj = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == data.gram_panchayat_id).first()
    if obj:
        for k, v in data.dict().items():
            setattr(obj, k, v)
    else:
        obj = models.Namuna8WaterTaxSettings(**data.dict())
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/settings/watertax/getall", response_model=list[schemas.Namuna8WaterTaxSettingsRead])
def get_all_watertax(db: Session = Depends(database.get_db)):
    return db.query(models.Namuna8WaterTaxSettings).all()

@router.get("/settings/watertax/get/{gram_panchayat_id}", response_model=schemas.Namuna8WaterTaxSettingsRead)
def get_watertax(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax setting not found")
    return obj

@router.put("/settings/watertax/update/{gram_panchayat_id}", response_model=schemas.Namuna8WaterTaxSettingsRead)
def update_watertax(gram_panchayat_id: int, data: schemas.Namuna8WaterTaxSettingsCreate, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax setting not found")
    for k, v in data.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/settings/watertax/delete/{gram_panchayat_id}")
def delete_watertax(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax setting not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Deleted"}

# --- Namuna8GeneralWaterTaxSlabSettings CRUD ---
@router.post("/settings/watertaxslab/save", response_model=schemas.Namuna8GeneralWaterTaxSlabSettingsRead)
def create_watertaxslab(data: schemas.Namuna8GeneralWaterTaxSlabSettingsCreate, db: Session = Depends(database.get_db)):
    if not data.gram_panchayat_id:
        raise HTTPException(status_code=400, detail="gram_panchayat_id is required")
    
    obj = db.query(models.Namuna8GeneralWaterTaxSlabSettings).filter(models.Namuna8GeneralWaterTaxSlabSettings.gram_panchayat_id == data.gram_panchayat_id).first()
    if obj:
        for k, v in data.dict().items():
            setattr(obj, k, v)
    else:
        obj = models.Namuna8GeneralWaterTaxSlabSettings(**data.dict())
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

@router.get("/settings/watertaxslab/getall", response_model=list[schemas.Namuna8GeneralWaterTaxSlabSettingsRead])
def get_all_watertaxslab(db: Session = Depends(database.get_db)):
    return db.query(models.Namuna8GeneralWaterTaxSlabSettings).all()

@router.get("/settings/watertaxslab/get/{gram_panchayat_id}", response_model=schemas.Namuna8GeneralWaterTaxSlabSettingsRead)
def get_watertaxslab(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8GeneralWaterTaxSlabSettings).filter(models.Namuna8GeneralWaterTaxSlabSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax slab setting not found")
    return obj

@router.put("/settings/watertaxslab/update/{gram_panchayat_id}", response_model=schemas.Namuna8GeneralWaterTaxSlabSettingsRead)
def update_watertaxslab(gram_panchayat_id: int, data: schemas.Namuna8GeneralWaterTaxSlabSettingsCreate, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8GeneralWaterTaxSlabSettings).filter(models.Namuna8GeneralWaterTaxSlabSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax slab setting not found")
    for k, v in data.dict().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj

@router.delete("/settings/watertaxslab/delete/{gram_panchayat_id}")
def delete_watertaxslab(gram_panchayat_id: int, db: Session = Depends(database.get_db)):
    obj = db.query(models.Namuna8GeneralWaterTaxSlabSettings).filter(models.Namuna8GeneralWaterTaxSlabSettings.gram_panchayat_id == gram_panchayat_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Water tax slab setting not found")
    db.delete(obj)
    db.commit()
    return {"detail": "Deleted"}

@router.post("/construction_type/bulk_upsert", response_model=List[schemas.ConstructionType])
def bulk_upsert_construction_types(
    request: schemas.BulkConstructionTypeUpsertRequest, 
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(database.get_db)
):
    # Validate location hierarchy
    from location_management import models as location_models
    
    # Check if district exists
    district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
    if not district:
        raise HTTPException(status_code=404, detail="District not found")
    
    # Check if taluka exists and belongs to the district
    taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
    if not taluka:
        raise HTTPException(status_code=404, detail="Taluka not found")
    if taluka.district_id != district_id:
        raise HTTPException(status_code=400, detail="Taluka does not belong to the specified district")
    
    # Check if gram panchayat exists and belongs to the taluka
    gram_panchayat = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == gram_panchayat_id).first()
    if not gram_panchayat:
        raise HTTPException(status_code=404, detail="Gram Panchayat not found")
    if gram_panchayat.taluka_id != taluka_id:
        raise HTTPException(status_code=400, detail="Gram Panchayat does not belong to the specified taluka")
    result = []
    for item in request.construction_types:
        if item.id is not None:
            obj = db.query(models.ConstructionType).filter(models.ConstructionType.id == item.id).first()
            if obj:
                obj.name = item.name
                obj.rate = item.rate
                obj.bandhmastache_dar = item.bandhmastache_dar
                obj.bandhmastache_prakar = item.bandhmastache_prakar
                obj.gharache_prakar = item.gharache_prakar
                obj.annualLandValueRate = item.annualLandValueRate
                # Only update location fields if they are currently null (global items)
                if obj.district_id is None and obj.taluka_id is None and obj.gram_panchayat_id is None:
                    obj.district_id = district_id
                    obj.taluka_id = taluka_id
                    obj.gram_panchayat_id = gram_panchayat_id
                db.flush()
                result.append(obj)
            else:
                # If id is given but not found, create new
                new_obj = models.ConstructionType(
                    name=item.name,
                    rate=item.rate,
                    bandhmastache_dar=item.bandhmastache_dar,
                    bandhmastache_prakar=item.bandhmastache_prakar,
                    gharache_prakar=item.gharache_prakar,
                    annualLandValueRate=item.annualLandValueRate,
                    district_id=district_id,
                    taluka_id=taluka_id,
                    gram_panchayat_id=gram_panchayat_id
                )
                db.add(new_obj)
                db.flush()
                result.append(new_obj)
        else:
            new_obj = models.ConstructionType(
                name=item.name,
                rate=item.rate,
                bandhmastache_dar=item.bandhmastache_dar,
                bandhmastache_prakar=item.bandhmastache_prakar,
                gharache_prakar=item.gharache_prakar,
                annualLandValueRate=item.annualLandValueRate,
                district_id=district_id,
                taluka_id=taluka_id,
                gram_panchayat_id=gram_panchayat_id
            )
            db.add(new_obj)
            db.flush()
            result.append(new_obj)
    
    # Commit all changes at once
    db.commit()
    
    # Refresh all objects to get updated data
    for obj in result:
        db.refresh(obj)
    
    return result

@router.post("/settings/bulk_save")
def bulk_save_namuna8_settings(request: schemas.BulkNamuna8SettingsRequest, db: Session = Depends(database.get_db)):
    result = {}
    # Checklist
    if request.checklist:
        checklist_data = request.checklist.dict(exclude_unset=True)
        checklist_data.pop('id', None)
        if not checklist_data.get('gram_panchayat_id'):
            raise HTTPException(status_code=400, detail="gram_panchayat_id is required for checklist settings")
        
        checklist_obj = db.query(models.Namuna8SettingChecklist).filter(models.Namuna8SettingChecklist.gram_panchayat_id == checklist_data['gram_panchayat_id']).first()
        if checklist_obj:
            for k, v in checklist_data.items():
                setattr(checklist_obj, k, v)
        else:
            checklist_obj = models.Namuna8SettingChecklist(**checklist_data)
            db.add(checklist_obj)
        db.commit()
        db.refresh(checklist_obj)
        result['checklist'] = checklist_obj
    # Dropdown
    if request.dropdown:
        dropdown_data = request.dropdown.dict(exclude_unset=True)
        dropdown_data.pop('id', None)
        if not dropdown_data.get('gram_panchayat_id'):
            raise HTTPException(status_code=400, detail="gram_panchayat_id is required for dropdown settings")
        
        obj = db.query(models.Namuna8DropdownAddSettings).filter(models.Namuna8DropdownAddSettings.gram_panchayat_id == dropdown_data['gram_panchayat_id']).first()
        if obj:
            for k, v in dropdown_data.items():
                setattr(obj, k, v)
        else:
            obj = models.Namuna8DropdownAddSettings(**dropdown_data)
            db.add(obj)
        db.commit()
        db.refresh(obj)
        result['dropdown'] = obj
    # Tax
    if request.tax:
        tax_data = request.tax.dict(exclude_unset=True)
        tax_data.pop('id', None)
        if not tax_data.get('gram_panchayat_id'):
            raise HTTPException(status_code=400, detail="gram_panchayat_id is required for tax settings")
        
        tax_obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == tax_data['gram_panchayat_id']).first()
        if tax_obj:
            for k, v in tax_data.items():
                setattr(tax_obj, k, v)
        else:
            tax_obj = models.Namuna8SettingTax(**tax_data)
            db.add(tax_obj)
        db.commit()
        db.refresh(tax_obj)
        result['tax'] = tax_obj
    # Water Tax
    if request.watertax:
        watertax_data = request.watertax.dict(exclude_unset=True)
        watertax_data.pop('id', None)
        if not watertax_data.get('gram_panchayat_id'):
            raise HTTPException(status_code=400, detail="gram_panchayat_id is required for water tax settings")
        
        watertax_obj = db.query(models.Namuna8WaterTaxSettings).filter(models.Namuna8WaterTaxSettings.gram_panchayat_id == watertax_data['gram_panchayat_id']).first()
        if watertax_obj:
            for k, v in watertax_data.items():
                setattr(watertax_obj, k, v)
        else:
            watertax_obj = models.Namuna8WaterTaxSettings(**watertax_data)
            db.add(watertax_obj)
        db.commit()
        db.refresh(watertax_obj)
        result['watertax'] = watertax_obj
    # Water Tax Slab
    if request.watertaxslab:
        watertaxslab_data = request.watertaxslab.dict(exclude_unset=True)
        watertaxslab_data.pop('id', None)
        # Update Namuna8SettingTax fields instead of Namuna8GeneralWaterTaxSlabSettings
        if not watertaxslab_data.get('gram_panchayat_id'):
            raise HTTPException(status_code=400, detail="gram_panchayat_id is required for water tax slab settings")
        
        settingtax_obj = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == watertaxslab_data['gram_panchayat_id']).first()
        if settingtax_obj:
            if 'rateUpto300' in watertaxslab_data:
                settingtax_obj.generalWaterUpto300 = watertaxslab_data['rateUpto300']
            if 'rate301To700' in watertaxslab_data:
                settingtax_obj.generalWater301_700 = watertaxslab_data['rate301To700']
            if 'rateAbove700' in watertaxslab_data:
                settingtax_obj.generalWaterAbove700 = watertaxslab_data['rateAbove700']
            # Add location fields if provided
            if 'district_id' in watertaxslab_data and watertaxslab_data['district_id'] is not None:
                settingtax_obj.district_id = watertaxslab_data['district_id']
            if 'taluka_id' in watertaxslab_data and watertaxslab_data['taluka_id'] is not None:
                settingtax_obj.taluka_id = watertaxslab_data['taluka_id']
            if 'gram_panchayat_id' in watertaxslab_data and watertaxslab_data['gram_panchayat_id'] is not None:
                settingtax_obj.gram_panchayat_id = watertaxslab_data['gram_panchayat_id']
            db.commit()
            db.refresh(settingtax_obj)
            result['watertaxslab'] = settingtax_obj
        else:
            # If not found, create with only these fields
            settingtax_obj = models.Namuna8SettingTax(
                generalWaterUpto300=watertaxslab_data.get('rateUpto300', 0),
                generalWater301_700=watertaxslab_data.get('rate301To700', 0),
                generalWaterAbove700=watertaxslab_data.get('rateAbove700', 0),
                district_id=watertaxslab_data.get('district_id', None),
                taluka_id=watertaxslab_data.get('taluka_id', None),
                gram_panchayat_id=watertaxslab_data.get('gram_panchayat_id', None)
            )
            db.add(settingtax_obj)
            db.commit()
            db.refresh(settingtax_obj)
            result['watertaxslab'] = settingtax_obj
    # Construction Types bulk upsert
    if request.construction_types:
        result_construction_types = []
        for item in request.construction_types:
            if item.id is not None:
                obj = db.query(models.ConstructionType).filter(models.ConstructionType.id == item.id).first()
                if obj:
                    obj.name = item.name
                    obj.rate = item.rate
                    obj.bandhmastache_dar = item.bandhmastache_dar
                    obj.bandhmastache_prakar = item.bandhmastache_prakar
                    obj.gharache_prakar = item.gharache_prakar
                    obj.annualLandValueRate = item.annualLandValueRate
                    obj.district_id = item.district_id
                    obj.taluka_id = item.taluka_id
                    obj.gram_panchayat_id = item.gram_panchayat_id
                    db.commit()
                    db.refresh(obj)
                    result_construction_types.append(obj)
                else:
                    new_obj = models.ConstructionType(
                        name=item.name,
                        rate=item.rate,
                        bandhmastache_dar=item.bandhmastache_dar,
                        bandhmastache_prakar=item.bandhmastache_prakar,
                        gharache_prakar=item.gharache_prakar,
                        annualLandValueRate=item.annualLandValueRate,
                        district_id=item.district_id,
                        taluka_id=item.taluka_id,
                        gram_panchayat_id=item.gram_panchayat_id
                    )
                    db.add(new_obj)
                    db.commit()
                    db.refresh(new_obj)
                    result_construction_types.append(new_obj)
            else:
                new_obj = models.ConstructionType(
                    name=item.name,
                    rate=item.rate,
                    bandhmastache_dar=item.bandhmastache_dar,
                    bandhmastache_prakar=item.bandhmastache_prakar,
                    gharache_prakar=item.gharache_prakar,
                    annualLandValueRate=item.annualLandValueRate,
                    district_id=getattr(item, 'district_id', None),
                    taluka_id=getattr(item, 'taluka_id', None),
                    gram_panchayat_id=getattr(item, 'gram_panchayat_id', None)
                )
                db.add(new_obj)
                db.commit()
                db.refresh(new_obj)
                result_construction_types.append(new_obj)
        result['construction_types'] = result_construction_types
    # Building Usage Weightage
    if getattr(request, 'building_usage_weightage', None) is not None:
        db.query(BuildingUsageWeightage).delete()
        for item in request.building_usage_weightage:
            db.add(BuildingUsageWeightage(
                serial_number=item.serial,
                building_usage=item.usage,
                weightage=item.weight,
                district_id=item.district_id,
                taluka_id=item.taluka_id,
                gram_panchayat_id=item.gram_panchayat_id
            ))
        db.commit()
    return result

# --- Village CRUD Operations ---
@router.post("/village/", response_model=schemas.VillageRead, status_code=status.HTTP_201_CREATED)
def create_village(village_data: schemas.VillageCreate, db: Session = Depends(database.get_db)):
    # Check if village with same name already exists
    existing_village = db.query(models.Village).filter(models.Village.name == village_data.name).first()
    if existing_village:
        raise HTTPException(status_code=400, detail="Village with this name already exists")
    
    new_village = models.Village(**village_data.dict())
    db.add(new_village)
    db.commit()
    db.refresh(new_village)
    return new_village

@router.get("/village/", response_model=List[schemas.VillageRead])
def get_all_villages(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    taluka_id: Optional[int] = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: Optional[int] = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Village)
    if district_id is not None:
        query = query.filter(models.Village.district_id == district_id)
    if taluka_id is not None:
        query = query.filter(models.Village.taluka_id == taluka_id)
    if gram_panchayat_id is not None:
        query = query.filter(models.Village.gram_panchayat_id == gram_panchayat_id)
    return query.all()

@router.get("/village/{village_id}", response_model=schemas.VillageRead)
def get_village(village_id: int, db: Session = Depends(database.get_db)):
    village = db.query(models.Village).filter(models.Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    return village

@router.get("/village/name/{village_name}", response_model=schemas.VillageRead)
def get_village_by_name(village_name: str, db: Session = Depends(database.get_db)):
    village = db.query(models.Village).filter(models.Village.name == village_name).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    return village

@router.put("/village/{village_id}", response_model=schemas.VillageRead)
def update_village(village_id: int, village_data: schemas.VillageCreate, db: Session = Depends(database.get_db)):
    village = db.query(models.Village).filter(models.Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    
    # Check if new name conflicts with existing village
    if village_data.name != village.name:
        existing_village = db.query(models.Village).filter(models.Village.name == village_data.name).first()
        if existing_village:
            raise HTTPException(status_code=400, detail="Village with this name already exists")
    
    for key, value in village_data.dict().items():
        setattr(village, key, value)
    
    village.updated_at = datetime.now()
    db.commit()
    db.refresh(village)
    return village

@router.delete("/village/{village_id}")
def delete_village(village_id: int, db: Session = Depends(database.get_db)):
    village = db.query(models.Village).filter(models.Village.id == village_id).first()
    if not village:
        raise HTTPException(status_code=404, detail="Village not found")
    
    # Check if village has associated properties or owners
    if village.properties or village.owners:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete village that has associated properties or owners. Please delete all properties and owners first."
        )
    
    db.delete(village)
    db.commit()
    return {"message": "Village deleted successfully"}

@router.post("/village/bulk", response_model=List[schemas.VillageRead], status_code=status.HTTP_201_CREATED)
def create_bulk_villages(villages: List[schemas.VillageCreate], db: Session = Depends(database.get_db)):
    created_villages = []
    for village_data in villages:
        # Check if village with same name already exists
        existing_village = db.query(models.Village).filter(models.Village.name == village_data.name).first()
        if existing_village:
            continue  # Skip duplicates
        new_village = models.Village(**village_data.dict())
        db.add(new_village)
        db.commit()
        db.refresh(new_village)
        created_villages.append(new_village)
    return created_villages

@router.get("/owners/", response_model=List[schemas.Owner])
def get_all_owners(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    taluka_id: Optional[int] = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: Optional[int] = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Owner)
    if district_id is not None:
        query = query.filter(models.Owner.district_id == district_id)
    if taluka_id is not None:
        query = query.filter(models.Owner.taluka_id == taluka_id)
    if gram_panchayat_id is not None:
        query = query.filter(models.Owner.gram_panchayat_id == gram_panchayat_id)
    return query.all()

@router.get("/owners_by_village/", response_model=List[schemas.Owner])
def get_owners_by_village(village_id: int, db: Session = Depends(database.get_db)):
    return db.query(models.Owner).filter(models.Owner.village_id == village_id).all()

@router.get("/properties_by_owner_village/", response_model=List[schemas.PropertyRead])
def get_properties_by_owner_village(
    village_id: int,
    district_id: int = Query(..., description="District ID"),
    taluka_id: int = Query(..., description="Taluka ID"),
    gram_panchayat_id: int = Query(..., description="Gram Panchayat ID"),
    db: Session = Depends(database.get_db)
):
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

    properties = (
        db.query(models.Property)
        .join(models.Property.owners)
        .filter(models.Owner.village_id == village_id)
        .all()
    )
    return [build_property_response(p, db, gram_panchayat_id) for p in properties]


@router.get("/properties_by_village/", response_model=List[schemas.PropertyRead])
def get_properties_by_village(
    village_id: int, 
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
    
    properties = db.query(models.Property).filter(models.Property.village_id == village_id).all()

    return [build_property_response(p, db, gram_panchayat_id) for p in properties]


@router.post("/serialize_properties/")
def serialize_properties(
    village_id: int = Body(...),
    district_id: int = Body(...),
    taluka_id: int = Body(...),
    gram_panchayat_id: int = Body(...),
    start_number: int = Body(...),
    change_malmatta: bool = Body(False),
    db: Session = Depends(database.get_db)
):
    """
    Serialize property anuKramank numbers starting from start_number + 1.
    Updates QR codes and moves owner photos based on new anuKramank.
    """
    try:
        with db.begin():
            # Validate location hierarchy
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
            
            # Get all properties for the village, sorted by current anuKramank
            properties = db.query(models.Property).filter(
                models.Property.village_id == village_id
            ).order_by(models.Property.anuKramank).all()
            
            if not properties:
                return {"success": True, "message": "No properties found for this village", "updated_count": 0}
            
            updated_count = 0
            
            for index, db_property in enumerate(properties):
                old_anuKramank = db_property.anuKramank
                new_anuKramank = start_number + index + 1
                
                # Skip if anuKramank is already correct
                if old_anuKramank == new_anuKramank:
                    continue
                
                # Check if new anuKramank already exists in this village
                existing = db.query(models.Property).filter(
                    models.Property.village_id == village_id,
                    models.Property.anuKramank == new_anuKramank
                ).first()
                if existing and existing.id != db_property.id:
                    logging.warning(f"Skipping property {db_property.id}: anuKramank {new_anuKramank} already exists")
                    continue
                
                # Delete old QR code files
                if db_property.qrcode:
                    old_qr_path = db_property.qrcode
                    if os.path.exists(old_qr_path):
                        try:
                            os.remove(old_qr_path)
                        except Exception as e:
                            logging.warning(f"Could not delete old QR code {old_qr_path}: {e}")
                    
                    # Also delete old QR directory if empty
                    old_qr_dir = os.path.dirname(old_qr_path)
                    if os.path.exists(old_qr_dir) and not os.listdir(old_qr_dir):
                        try:
                            os.rmdir(old_qr_dir)
                        except Exception:
                            pass
                
                # Delete old QR template HTML files (stored with anuKramank in filename)
                try:
                    district_obj = db.query(location_models.District).filter(location_models.District.id == db_property.district_id).first()
                    taluka_obj = db.query(location_models.Taluka).filter(location_models.Taluka.id == db_property.taluka_id).first()
                    gram_panchayat_obj = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == db_property.gram_panchayat_id).first()
                    village_obj = db.query(models.Village).filter(models.Village.id == db_property.village_id).first()
                    
                    def safe_name(value: str) -> str:
                        try:
                            value = value.strip()
                            value = re.sub(r"\s+", "_", value)
                            value = re.sub(r"[^\w\-\.\u0900-\u097F]", "", value)
                            return value[:80] if len(value) > 80 else value
                        except Exception:
                            return str(value)
                    
                    district_name = safe_name(district_obj.name if district_obj else str(db_property.district_id))
                    taluka_name = safe_name(taluka_obj.name if taluka_obj else str(db_property.taluka_id))
                    gp_name = safe_name(gram_panchayat_obj.name if gram_panchayat_obj else str(db_property.gram_panchayat_id))
                    village_name = safe_name(village_obj.name if village_obj else str(db_property.village_id))
                    
                    old_qr_template_dir = os.path.join(
                        "uploaded_images",
                        "qrTemplate",
                        district_name,
                        taluka_name,
                        gp_name,
                        village_name,
                    )
                    old_qr_template_path = os.path.join(old_qr_template_dir, f'qr_template_{old_anuKramank}.html')
                    if os.path.exists(old_qr_template_path):
                        try:
                            os.remove(old_qr_template_path)
                            logging.info(f"Deleted old QR template: {old_qr_template_path}")
                        except Exception as e:
                            logging.warning(f"Could not delete old QR template {old_qr_template_path}: {e}")
                except Exception as e:
                    logging.warning(f"Error deleting old QR template: {e}")
                
                # Note: Owner photos are stored by owner_id, not anuKramank
                # Path structure: uploaded_images/owners/{district_id}/{taluka_id}/{gram_panchayat_id}/{owner_id}/
                # Since owner_id doesn't change during serialization, no need to move owner photos
                
                # Update anuKramank
                db_property.anuKramank = new_anuKramank
                
                # Update malmattaKramank if requested
                if change_malmatta:
                    db_property.malmattaKramank = str(new_anuKramank)
                
                db.flush()
                try:
                    docs = db.query(PropertyDocument).filter(
                        PropertyDocument.property_anuKramank == old_anuKramank
                    ).all()
                    for doc in docs:
                        # update DB field
                        doc.property_anuKramank = new_anuKramank

                        def migrate_path(path_value):
                            if not path_value:
                                return None
                            # resolve absolute path
                            abs_path = path_value if os.path.isabs(path_value) else os.path.join(os.getcwd(), path_value)
                            if not os.path.exists(abs_path):
                                return None
                            # try to replace directory segment that equals old anuKramank
                            old_seg = os.sep + str(old_anuKramank) + os.sep
                            if old_seg in abs_path:
                                new_abs = abs_path.replace(old_seg, os.sep + str(new_anuKramank) + os.sep)
                            else:
                                # fallback: replace occurrences of the number (safe within upload tree)
                                new_abs = abs_path.replace(str(old_anuKramank), str(new_anuKramank))
                            new_dir = os.path.dirname(new_abs)
                            os.makedirs(new_dir, exist_ok=True)
                            try:
                                shutil.move(abs_path, new_abs)
                            except Exception:
                                try:
                                    shutil.copy2(abs_path, new_abs)
                                    os.remove(abs_path)
                                except Exception:
                                    return None
                            # return relative path for DB (forward slashes)
                            return os.path.relpath(new_abs, start=os.getcwd()).replace(os.sep, '/')

                        new_doc_image = migrate_path(getattr(doc, 'document_image', None))
                        if new_doc_image:
                            doc.document_image = new_doc_image
                        new_doc_path = migrate_path(getattr(doc, 'document_path', None))
                        if new_doc_path:
                            doc.document_path = new_doc_path

                    db.flush()
                except Exception as e:
                    logging.warning(f"PropertyDocument migration failed for {old_anuKramank} -> {new_anuKramank}: {e}")
                # --- END INSERTED MIGRATION LOGIC ---

                # Generate new QR code
                try:
                    record_response = get_property_record(
                        db_property.anuKramank,
                        db_property.village_id,
                        db_property.district_id,
                        db_property.taluka_id,
                        db_property.gram_panchayat_id,
                        db
                    )
                    
                    vpanikar_qr = record_response.get('vpanikar', 0)
                    totalTax_qr = record_response.get('totaltax', 0)
                    totalTax = totalTax_qr - vpanikar_qr
                    totalArea = round(record_response.get('totalArea', 0) or 0, 2)
                    
                    owners_list = list(db_property.owners)
                    owner_name = owners_list[0].name if owners_list else None
                    wife_name = owners_list[0].wifeName if owners_list and getattr(owners_list[0], "wifeName", None) else None
                    occupant_name = owners_list[0].occupantName if owners_list and getattr(owners_list[0], "occupantName", None) else record_response.get('occupantName')
                    mobile_number = owners_list[0].mobileNumber if owners_list and getattr(owners_list[0], "mobileNumber", None) else record_response.get('mobileNumber')
                    
                    # Construction area (exclude 'खाली जागा')
                    constructionArea = sum(
                        (c.length or 0) * (c.width or 0)
                        for c in db_property.constructions
                        if not (c.construction_type and c.construction_type.name.strip().startswith('खाली जागा'))
                    )
                    constructionArea = round(constructionArea, 2)
                    openArea = round(totalArea - constructionArea, 2)
                    
                    boundary_east = record_response.get('boundaryEast') or getattr(db_property, 'eastBoundary', None)
                    boundary_west = record_response.get('boundaryWest') or getattr(db_property, 'westBoundary', None)
                    boundary_north = record_response.get('boundaryNorth') or getattr(db_property, 'northBoundary', None)
                    boundary_south = record_response.get('boundarySouth') or getattr(db_property, 'southBoundary', None)
                    
                    def safe_name(value: str) -> str:
                        try:
                            value = value.strip()
                            value = re.sub(r"\s+", "_", value)
                            value = re.sub(r"[^\w\-\.\u0900-\u097F]", "", value)
                            return value[:80] if len(value) > 80 else value
                        except Exception:
                            return str(value)
                    
                    district_obj = db.query(location_models.District).filter(location_models.District.id == db_property.district_id).first()
                    taluka_obj = db.query(location_models.Taluka).filter(location_models.Taluka.id == db_property.taluka_id).first()
                    gram_panchayat_obj = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == db_property.gram_panchayat_id).first()
                    village_obj = db.query(models.Village).filter(models.Village.id == db_property.village_id).first()
                    
                    district_name = safe_name(district_obj.name if district_obj else str(db_property.district_id))
                    taluka_name = safe_name(taluka_obj.name if taluka_obj else str(db_property.taluka_id))
                    gp_name = safe_name(gram_panchayat_obj.name if gram_panchayat_obj else str(db_property.gram_panchayat_id))
                    
                    qr_data = {
                        "अनुक्रमांक": db_property.anuKramank,
                        "मालकाचे नाव": owner_name,
                        "एकूण क्षेत्रफळ": totalArea,
                        "बांधकाम क्षेत्रफळ": constructionArea,
                        "खुली जागा": openArea,
                        "एकूण कर": totalTax,
                    }
                    if wife_name:
                        qr_data["पत्नीचे नाव"] = wife_name
                    
                    # Create location-based QR directory structure
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
                    QRCodeGeneration.createQRcodeTemp(qr_data, qr_path)
                    db_property.qrcode = qr_path.replace(os.sep, "/")
                    db.flush()
                    
                    # Generate QR template
                    try:
                        area_unit_for_template = getattr(db_property, 'areaUnit', 'sqft') or 'sqft'
                        total_area_sqft = round(float(getattr(db_property, 'totalAreaSqFt', 0) or totalArea or 0), 2)
                        construction_area_sqft = round((constructionArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((constructionArea or 0), 2)
                        open_area_sqft = round((openArea * 10.7639), 2) if area_unit_for_template == 'sqm' else round((openArea or 0), 2)
                        
                        qr_data_template = {
                            "ग्रा. पं.": gp_name,
                            "ता.": taluka_name,
                            "जि.": district_name,
                            "मा क्र": getattr(db_property, 'malmattaKramank', None),
                            "मा. धा. नाव": owner_name,
                            "भो. नाव": occupant_name,
                            "पू.": boundary_east,
                            "प.": boundary_west,
                            "उ.": boundary_north,
                            "द.": boundary_south,
                            "मो नं": mobile_number,
                            "ए क्षे. चौ. फू": total_area_sqft,
                            "ए बां. चौ. फू": construction_area_sqft,
                            "ए खा .जागा चौ.फू": open_area_sqft,
                            "ए कर": totalTax,
                        }
                        if wife_name:
                            qr_data_template["पत्नीचे नाव"] = wife_name
                        
                        qr_path_template = os.path.join(qr_dir, "qrcode_template.png")
                        QRCodeGeneration.createQRcodeTemp(qr_data_template, qr_path_template)
                        
                        # Generate QR template HTML file (same as in create method)
                        try:
                            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                            template_dir = os.path.join(base_dir, 'templates')
                            namuna8_template_dir = os.path.join(template_dir, 'Namuna8')
                            env = Environment(loader=FileSystemLoader(namuna8_template_dir))
                            template = env.get_template('qrTemplate.html')
                            
                            qr_template_dir = os.path.join(
                                "uploaded_images",
                                "qrTemplate",
                                district_name,
                                taluka_name,
                                gp_name,
                                village_name,
                            )
                            os.makedirs(qr_template_dir, exist_ok=True)
                            
                            # Create relative paths for template
                            report_images_dir = os.path.join(base_dir, 'ReportImages')
                            reports_dir = os.path.join(base_dir, 'reports')
                            rel_report_images = os.path.relpath(report_images_dir, start=qr_template_dir)
                            rel_reports = os.path.relpath(reports_dir, start=qr_template_dir)
                            
                            # Convert QR code path to relative path
                            qr_code_abs_path = os.path.abspath(qr_path_template)
                            rel_qrcode = os.path.relpath(qr_code_abs_path, start=qr_template_dir)
                            
                            context = {
                                "district_id": str(db_property.district_id),
                                "taluka_id": str(db_property.taluka_id),
                                "gram_panchayat_id": str(db_property.gram_panchayat_id),
                                "village_id": str(db_property.village_id),
                                "district_name": district_obj.name if district_obj else "",
                                "taluka_name": taluka_obj.name if taluka_obj else "",
                                "gram_panchayat_name": gram_panchayat_obj.name if gram_panchayat_obj else "",
                                "village_name": village_obj.name if village_obj else "",
                                "owner_name": owner_name,
                                "malmatta_kramank": getattr(db_property, 'malmattaKramank', None),
                                "report_images": rel_report_images,
                                "reports": rel_reports,
                                "qrcode": rel_qrcode,
                            }
                            rendered_html = template.render(**context)
                            qr_template_html_path = os.path.join(qr_template_dir, f'qr_template_{db_property.anuKramank}.html')
                            with open(qr_template_html_path, 'w', encoding='utf-8') as f:
                                f.write(rendered_html)
                            logging.info(f"Generated QR template HTML: {qr_template_html_path}")
                        except Exception as e:
                            logging.error(f"Error generating QR template HTML for property {db_property.id}: {e}")
                    except Exception as e:
                        logging.error(f"Error generating QR template for property {db_property.id}: {e}")
                    
                    updated_count += 1
                    logging.info(f"Updated property {db_property.id}: anuKramank {old_anuKramank} -> {new_anuKramank}")
                    
                except Exception as e:
                    logging.error(f"Error generating QR code for property {db_property.id}: {e}")
                    # Continue with next property even if QR generation fails
            
            return {
                "success": True,
                "message": f"Successfully serialized {updated_count} properties",
                "updated_count": updated_count
            }
            
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Database error during property serialization: {e}")
        raise HTTPException(status_code=500, detail="Failed to serialize properties: " + str(e))
    except Exception as e:
        db.rollback()
        logging.error(f"Unexpected error during property serialization: {e}")
        raise HTTPException(status_code=500, detail="Failed to serialize properties: " + str(e))


@router.get("/properties_by_owner/", response_model=List[schemas.PropertyRead])
def get_properties_by_owner(
    owner_id: int, 
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
    
    owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
    if not owner:
        return []
    return [build_property_response(p, db, gram_panchayat_id) for p in owner.properties]

@router.get("/properties/bulk", response_model=list[schemas.PropertyRead])
def get_properties_bulk(
    ids: str = Query(...), 
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
    
    # ids is a comma-separated string of property IDs
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    properties = db.query(models.Property).filter(models.Property.anuKramank.in_(id_list)).all()
    return [build_property_response(p, db, gram_panchayat_id) for p in properties]

def get_tax_rate_by_area(db: Session, area: float, field: str, gram_panchayat_id: int):
    # Fetch settings filtered by gram_panchayat_id
    settings = db.query(Namuna8SettingTax).filter(Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not settings:
        return 0
    if area <= 300:
        return getattr(settings, field + 'Upto300', 0)
    elif 301 <= area <= 700:
        return getattr(settings, field + '301_700', 0)
    else:
        return getattr(settings, field + 'Above700', 0)

@router.post("/admin/recalculate_taxes", status_code=200)
def recalculate_all_property_taxes(
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
    settings = db.query(models.Namuna8SettingTax).filter(models.Namuna8SettingTax.gram_panchayat_id == gram_panchayat_id).first()
    if not settings:
        return {"detail": "No settings found"}
    def get_tax_by_area(area, field):
        if area is None:
            area = 0
        if area <= 300:
            return getattr(settings, field + 'Upto300', 0) or 0
        elif 301 <= area <= 700:
            return getattr(settings, field + '301_700', 0) or 0
        else:
            return getattr(settings, field + 'Above700', 0) or 0
    properties = db.query(models.Property).filter(models.Property.gram_panchayat_id == gram_panchayat_id).all()
    for prop in properties:
        total_area = prop.totalAreaSqFt or 0
        prop.divaKar = get_tax_by_area(total_area, 'light') if not prop.divaArogyaKar else 0
        prop.aarogyaKar = get_tax_by_area(total_area, 'health') if not prop.divaArogyaKar else 0
        prop.cleaningTax = get_tax_by_area(total_area, 'cleaning') if prop.safaiKar else 0
        toilet_tax = get_tax_by_area(total_area, 'bathroom') if prop.shauchalayKar else 0.0
        prop.toiletTax = toilet_tax
    db.commit()
    return {"detail": "All property taxes recalculated and updated."}

@router.get("/all_properties/")
def get_all_properties(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    taluka_id: Optional[int] = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: Optional[int] = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(database.get_db)
):
    query = db.query(models.Property)
    
    # Apply location filters if provided
    if district_id is not None:
        query = query.filter(models.Property.district_id == district_id)
    if taluka_id is not None:
        query = query.filter(models.Property.taluka_id == taluka_id)
    if gram_panchayat_id is not None:
        query = query.filter(models.Property.gram_panchayat_id == gram_panchayat_id)
    
    return query.all()
from sqlalchemy import and_
@router.delete("/{anu_kramank}/{village_id}", status_code=200)
def delete_property(anu_kramank: int,village_id:int, db: Session = Depends(database.get_db)):
    import os
    import shutil
    
    prop = (
    db.query(models.Property)
    .filter(
        and_(
            models.Property.anuKramank == anu_kramank,
            models.Property.village_id == village_id
        )
    )
    .first()
)
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    
    # Clean up files before deleting database records
    try:
        # Clean up QR code files
        if prop.qrcode:
            qr_file_path = prop.qrcode
            if os.path.exists(qr_file_path):
                try:
                    os.remove(qr_file_path)
                except Exception:
                    pass  # Continue even if file deletion fails
        
        # Clean up QR code directory
        qr_dir = os.path.join("uploaded_images", "qrcode", str(prop.district_id), str(prop.taluka_id), str(prop.gram_panchayat_id), str(prop.village_id), str(prop.anuKramank))
        if os.path.exists(qr_dir):
            try:
                shutil.rmtree(qr_dir)
            except Exception:
                pass  # Continue even if directory deletion fails
        
        # Clean up owner photos
        for owner in prop.owners:
            if owner.ownerPhoto:
                owner_photo_path = owner.ownerPhoto
                if os.path.exists(owner_photo_path):
                    try:
                        os.remove(owner_photo_path)
                    except Exception:
                        pass  # Continue even if file deletion fails
    except Exception:
        pass  # Continue with database deletion even if file cleanup fails
    
    # -----------------------------------------
    # DELETE PROPERTY DOCUMENT FILES
    # -----------------------------------------

    docs = (
        db.query(PropertyDocument)
        .filter(
            and_(
                PropertyDocument.property_anuKramank == anu_kramank,
                PropertyDocument.village_id == village_id
            )
        )
        .all()
    )


    for doc in docs:
        # Delete document_image and document_path from filesystem
        for attr in ("document_image", "document_path"):
            path_val = getattr(doc, attr, None)
            if not path_val:
                continue

            abs_path = path_val if os.path.isabs(path_val) else os.path.join(os.getcwd(), path_val)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except:
                    pass

            # Try to remove empty folder
            try:
                parent = os.path.dirname(abs_path)
                if parent.startswith(os.path.join(os.getcwd(), "uploaded_images", "property_documents")):
                    if os.path.exists(parent) and not os.listdir(parent):
                        os.rmdir(parent)
            except:
                pass

        # Delete DB record
        db.delete(doc)

    db.commit()

    # Delete entire directory for this property (safe cleanup)
    prop_docs_dir = os.path.join(
        "uploaded_images",
        "property_documents",
        str(village_id),
        str(anu_kramank)
    )

    if os.path.exists(prop_docs_dir):
        try:
            shutil.rmtree(prop_docs_dir)
        except:
            pass

    # Remove associations with owners (many-to-many)
    prop.owners = []
    db.commit()
    # Explicitly delete all constructions associated with this property
    for construction in list(prop.constructions):
        db.delete(construction)
    db.commit()
    # Delete the property
    db.delete(prop)
    db.commit()
    return {"message": f"Property {anu_kramank} deleted successfully."}

class HolderNoAssignment(BaseModel):
    anuKramank: int
    ownerIds: List[int]

@router.post("/set_holdernos/")
def set_holdernos(assignments: List[HolderNoAssignment], db: Session = Depends(database.get_db)):
    for assignment in assignments:
        for owner_id in assignment.ownerIds:
            owner = db.query(models.Owner).filter(models.Owner.id == owner_id).first()
            if owner:
                owner.holderno = assignment.anuKramank
    db.commit()
    return {"detail": "Holder numbers set for all provided owners."}

@router.get("/property_qrcode/{anu_kramank}")
def get_property_qrcode(
    village_id:int,
    anu_kramank: int,
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
    
    # Validate that the property belongs to the specified location hierarchy
    property_obj = db.query(models.Property).filter(
        models.Property.village_id == village_id,
        models.Property.anuKramank == anu_kramank,
        models.Property.district_id == district_id,
        models.Property.taluka_id == taluka_id,
        models.Property.gram_panchayat_id == gram_panchayat_id
    ).first()
    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found in the specified location")
    
    # Use location-based QR path
    qr_path = os.path.join("uploaded_images", "qrcode", str(district_id), str(taluka_id), str(gram_panchayat_id),str(village_id), str(anu_kramank), "qrcode.png")
    if not os.path.exists(qr_path):
        raise HTTPException(status_code=404, detail="QR code not found")
    return FileResponse(qr_path, media_type="image/png")

@router.get("/settings/building_usage_weightage/get")
def get_building_usage_weightage(
    district_id: Optional[int] = Query(None, description="Filter by district ID"),
    taluka_id: Optional[int] = Query(None, description="Filter by taluka ID"),
    gram_panchayat_id: Optional[int] = Query(None, description="Filter by gram panchayat ID"),
    db: Session = Depends(database.get_db)
):
    query = db.query(BuildingUsageWeightage)
    
    # Apply location filters if provided
    if district_id is not None:
        query = query.filter(BuildingUsageWeightage.district_id == district_id)
    if taluka_id is not None:
        query = query.filter(BuildingUsageWeightage.taluka_id == taluka_id)
    if gram_panchayat_id is not None:
        query = query.filter(BuildingUsageWeightage.gram_panchayat_id == gram_panchayat_id)
    
    rows = query.order_by(BuildingUsageWeightage.serial_number).all()
    
    # If no data found, return empty array (frontend will show defaults)
    if not rows:
        return []
    
    return [
        {
            "serial_number": row.serial_number,
            "building_usage": row.building_usage,
            "weightage": row.weightage
        }
        for row in rows
    ]
    