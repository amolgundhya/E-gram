from fastapi import APIRouter , Depends
from fastapi.responses import JSONResponse
import requests
from Utility.JWTUtil import create_license_token , verify_license_token , encrypt_token , decrypt_token
from JWTapi import tokenModel as models
from pydantic import BaseModel
from sqlalchemy.orm import Session
import database
from cryptography.fernet import InvalidToken
import bcrypt
from sqlalchemy import inspect
import datetime
from sqlalchemy import text
from sqlalchemy.sql.sqltypes import Boolean

class license(BaseModel):
    license_key : str

router = APIRouter()
@router.get('/generate-license')
def generate_token():
    try:
        token = create_license_token()
        encrypted_license_key = encrypt_token(token)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "License generated successfully",
                "data" : {
                    "license" : encrypted_license_key
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e),
                "data" : []
            }
        )
        
@router.post('/verify-license')
def verfiy_token(token : str):
    try:
        payload  = verify_license_token(token)
        return JSONResponse(
            status_code=200,
            content={
                "success" : True,
                "message" : "license verified successfully",
                "data" : {
                    "payload" : payload
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e),
                "data" : []
            }
        )
    
@router.post("/store-encrypted-license")
def store_encrypted_license(license : license , db : Session = Depends(database.get_db)):
    try:
            license_key = license.license_key
            encrypted_key = bcrypt.hashpw(license_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                new_license = models.license(
                    encrypted_license_key = encrypted_key
                )
                db.add(new_license)
                db.commit()
                db.refresh(new_license)
                db.close()
                return JSONResponse(
                    status_code=200,
                    content={
                        "success" : True,
                        "messgae" : "Encrypted license added successfully",
                        "data" : {
                            "encrypted_license_key" : encrypted_key,
                            "license_key" : license_key
                        }
                    }
                )
            except Exception as e:
                return JSONResponse(
                    status_code=400,
                    content={
                        "success" : False,
                        "message" : f"Error adding in db : {str(e)}",
                        "data" : []
                    }
                )
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success" : False,
                "message" : str(e),
                "data" : []
            }
        )

@router.post("/verify-encrypted-license")
def verify_encrypted_license(license : license , db : Session = Depends(database.get_db)):
    try:
        license_key = license.license_key
        licenses = db.query(models.license).all()

        for lic in licenses:
            if bcrypt.checkpw(license_key.encode('utf-8'), lic.encrypted_license_key.encode('utf-8')):
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "message": "License Verified Successfully",
                        "data": []
                    }
                )

        return JSONResponse(
            status_code=401,
            content={
                "success": False,
                "message": "License Not Verified, not authorized to move forward",
                "data": []
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal server error: {str(e)}",
                "data": []
            }
        )

def is_connected():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except requests.RequestException:
        return False
    
@router.post('/check-license-hosted')
def check_license_hosted(license : license , db : Session=Depends(database.get_db)):
    try:
        license_key = license.license_key.strip()

      
        local_licenses = db.query(models.license).all()

        if not local_licenses:
            if not is_connected():
                return JSONResponse(
                    status_code=503,
                    content={
                        "success": False,
                        "message": "To check with the license key , Please connected to the internet",
                        "data": []
                    }
                )
            else:
                    headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                    }

                    response = requests.post(
                        "https://egrampanchayat.gunadhyasoftware.com/api/update-usage",
                        json={"license_key": license_key},
                        headers=headers,
                        timeout=5,
                    )
                    print('license_key --->'  , license_key)
                    print('header --->' , headers)
                    print('response ---> ' , response)
                    if response.status_code == 200:
                        encrypted_key = bcrypt.hashpw(license_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                        try:
                            new_license = models.license(
                                encrypted_license_key = encrypted_key
                            )
                            db.add(new_license)
                            db.commit()
                            db.refresh(new_license)
                            db.close()
                            return JSONResponse(
                                status_code=200,
                                content={
                                    "success" : True,
                                    "messgae" : "Encrypted license key verified added successfully.Now you can use this license key without internet",
                                    "data" : []
                                }
                            )
                        except Exception as e:
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "success" : False,
                                    "message" : f"Error adding in db : {str(e)}",
                                    "data" : []
                                }
                            )
                    else:
                        error_response = response.json()
                        message = error_response.get("messages", {}).get("error", "Something went wrong.")
                        return JSONResponse(
                                status_code=response.status_code,
                                content={
                                    "success" : False,
                                    "messgae" : message,
                                    "data" : []
                                }
                            )
                # except Exception as e:
                #     print("ERROR:", e)  # Add this line for debugging
                #     return JSONResponse(
                #         status_code=503,
                #         content={
                #             "success": False,
                #             "message": "Unable to reach hosted server. Check your internet connection.",
                #             "data": []
                #         }
                #     )

        else:
            for lic in local_licenses:
               
                if bcrypt.checkpw(license_key.encode('utf-8'), lic.encrypted_license_key.encode('utf-8')):
                    return JSONResponse(
                        status_code=200,
                        content={
                            "success": True,
                            "message": "License Verified Successfully",
                            "data": []
                        }
                    )

            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "message": "License Not Verified, Please provide the correct license key",
                    "data": []
                }
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Internal server error: {str(e)}",
                "data": []
            }
        )

@router.post("/sync/upload")
def sync_all_tables(db : Session=Depends(database.get_db)):
    try:
        inspector = inspect(db.bind)
        all_tables = inspector.get_table_names()

        tables_to_sync = [table for table in all_tables if table not in ['license']]

        # List of modules that contain models
        import importlib
        model_modules = [
            'location_management.models',  # Contains District, Taluka, GramPanchayat
            'namuna8.namuna8_model',      # Contains Village
            'certificates.birth_certificate_model',
            'certificates.death_certificate_model', 
            'certificates.family_certificate_model',
            'certificates.good_conduct_certificate_model',
            'certificates.life_certificate_model',
            'certificates.marriage_certificate_model',
            'certificates.niradhar_certificate_model',
            'certificates.no_arrears_certificate_model',
            'certificates.no_benefit_certificate_model',
            'certificates.no_objection_certificate_model',
            'certificates.receipt_certificate_model',
            'certificates.resident_certificate_model',
            'certificates.toilet_certificate_model',
            'certificates.unemployment_certificate_model',
            'certificates.widow_certificate_model',
            'certificates.birthdeath_unavailability_model',
            'namuna8.namuna8_model',
            'namuna8.namuna7.namuna7_model',
            'namuna8.mastertab.mastertabmodels',
            'namuna8.PropertyDocuments.property_document_model',
            'namuna8.owner_history_model',
            'namuna8.property_owner_history_model',
            'namuna8.mastertab.transfer_apis',
            'namuna9.namuna9_model',
            'reportstab.outward_entries_model'
        ]
        # Dictionary to store all model classes
        all_models = {}
        # Import and collect all models
        for module_name in model_modules:
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, '__tablename__') and hasattr(attr, '__table__'):
                        all_models[attr.__tablename__] = attr
            except ImportError as e:
                # print(f"Warning: Could not import {module_name}: {e}")
                continue

        # Define the correct sync order to satisfy foreign key constraints
        ordered_tables = [
            'districts',
            'talukas',
            'gram_panchayats',
            'villages',
        ]
        # Add the rest of the tables, preserving their original order but skipping already added
        ordered_tables += [t for t in tables_to_sync if t not in ordered_tables]

        data_to_sync = {}

        # Only sync tables that exist in the MySQL schema
        mysql_tables = set([
            'districts', 'talukas', 'gram_panchayats', 'villages', 'construction_types', 'namuna8_setting_checklist',
            'namuna8DropdownAddSettings', 'namuna8SettingTax', 'namuna8WaterTaxSettings', 'namuna8GeneralWaterTaxSlabSettings',
            'generalSetting', 'newYojna', 'building_usage_weightage', 'namuna9_year_setups', 'namuna9', 'namuna9_settings',
            'no_arrears_certificates', 'birth_certificates', 'death_certificates', 'birthdeath_unavailability_certificates',
            'resident_certificates', 'family_certificates', 'toilet_certificates', 'no_objection_certificates',
            'no_benefit_certificates', 'life_certificates', 'good_conduct_certificates', 'niradhar_certificates',
            'unemployment_certificates', 'receipt_certificates', 'owners', 'properties', 'property_owner_association',
            'constructions', 'property_documents', 'property_transfer_logs', 'namuna7', 'outward_entries'
        ])

        for table_name in ordered_tables:
            if table_name not in mysql_tables:
                # print(f"Skipping table '{table_name}' as it does not exist in MySQL schema.")
                continue
            model_class = all_models.get(table_name)
            if not model_class:
                # print(f"Warning: No model found for table '{table_name}'")
                continue
            try:
                rows = db.query(model_class).all()
                row_dicts = []
                for row in rows:
                    row_dict = {}
                    for column in model_class.__table__.columns:
                        value = getattr(row, column.name)
                        if hasattr(value, 'isoformat'):
                            value = value.isoformat()
                        row_dict[column.name] = value
                    row_dicts.append(row_dict)
                data_to_sync[table_name] = row_dicts
                # print(f"Synced {len(row_dicts)} rows from table '{table_name}'")
            except Exception as e:
                # print(f"Error syncing table '{table_name}': {e}")
                continue

        # Manually include many-to-many association table (no declarative model)
        try:
            assoc_table = None
            if 'property_owner_associationowners' in all_tables:
                assoc_table = 'property_owner_associationowners'
            elif 'property_owner_association' in all_tables:
                assoc_table = 'property_owner_association'
            if assoc_table:
                assoc_rows = db.execute(text(f"SELECT id, owner_id FROM {assoc_table}"))
                # Alias to Python key expected by PHP (Livecode normalizes this key)
                data_to_sync['property_owner_association'] = [dict(r) for r in assoc_rows.mappings()]
        except Exception:
            pass

        # print(f"Tables found: {ordered_tables}")
        # print(f"Total tables with data: {len(data_to_sync)}")
        # print(f"Tables successfully synced: {list(data_to_sync.keys())}")
        # print(f"Tables with no data: {[table for table in ordered_tables if table not in data_to_sync]}")
        
        # Send to PHP hosted server
        try:
            headers = {
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
                    }
            php_server_url = "https://egrampanchayat.gunadhyasoftware.com/api/sync/upload_data"
            sync_payload = {
                "sync_data": data_to_sync,
                "sync_timestamp": datetime.datetime.now().isoformat(),
                "total_tables": len(data_to_sync),
                "tables_synced": list(data_to_sync.keys())
            }
            # print(f"Sending data to PHP server: {php_server_url}")
            response = requests.post(php_server_url,headers=headers, json=sync_payload, timeout=30)
            if response.status_code == 200:
                response_data = response.json()
                return {
                    "success": True, 
                    "message": "Data synced to hosted server successfully",
                    "php_response": response_data,
                    "data": data_to_sync
                }
            else:
                return {
                    "success": False, 
                    "message": f"Failed to sync to PHP server. Status: {response.status_code}",
                    "details": response.text,
                    "data": data_to_sync
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False, 
                "message": f"Network error while syncing to PHP server: {str(e)}",
                "data": data_to_sync
            }
        except Exception as e:
            return {
                "success": False, 
                "message": f"Error syncing to PHP server: {str(e)}",
                "data": data_to_sync
            }

    except Exception as e:
        return {"success": False, "message": str(e)}

@router.post("/sync/download")
def download_and_replace_all_tables(db: Session = Depends(database.get_db)):
    """
    Fetch all data from the hosted PHP API and replace all local tables with it.
    """
    import requests
    import datetime
    import importlib
    from sqlalchemy import text
    from sqlalchemy.types import Boolean

    try:
        # 1. Fetch data from hosted server
        headers = {
            "Content-Type": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
        }
        php_server_url = "https://egrampanchayat.gunadhyasoftware.com/api/sync/download_data"
        response = requests.get(php_server_url, headers=headers, timeout=60)
        if response.status_code != 200:
            return {
                "success": False,
                "message": f"Failed to fetch from hosted server: {response.status_code}",
            }
        sync_data = response.json().get("sync_data", {})
        
        # Debug logging for property_owner_association
        if "property_owner_association" in sync_data:
            rows = sync_data["property_owner_association"]
            print(f"DEBUG: Received {len(rows)} rows for property_owner_association")
            if len(rows) > 0:
                print(f"DEBUG: Sample row: {rows[0]}")
        else:
            print("DEBUG: No property_owner_association data in response")

        # 2. Order of deletion
        truncate_order = [
            "constructions",
            "property_owner_association",
            "property_documents",
            "owners",
            "properties",
            "villages",
            "gram_panchayats",
            "talukas",
            "districts",
            "construction_types",
            "building_usage_weightage",
            "property_transfer_logs",
            "namuna8_setting_checklist",
            "namuna8DropdownAddSettings",
            "namuna8SettingTax",
            "namuna8WaterTaxSettings",
            "namuna8GeneralWaterTaxSlabSettings",
            "generalSetting",
            "newYojna",
            "namuna9_year_setups",
            "namuna9_settings",
            "namuna9",
            "namuna9_property_association",
            "namuna7",
            "no_arrears_certificates",
            "birth_certificates",
            "death_certificates",
            "birthdeath_unavailability_certificates",
            "resident_certificates",
            "family_certificates",
            "toilet_certificates",
            "no_objection_certificates",
            "no_benefit_certificates",
            "life_certificates",
            "good_conduct_certificates",
            "niradhar_certificates",
            "unemployment_certificates",
            "receipt_certificates",
            "outward_entries",
        ]

        insert_order = [
            "districts",
            "talukas",
            "gram_panchayats",
            "villages",
            "owners",
            "properties",
            "construction_types",
            "building_usage_weightage",
            "property_documents",
            "property_transfer_logs",
            "property_owner_association",
            "constructions",
            "namuna8_setting_checklist",
            "namuna8DropdownAddSettings",
            "namuna8SettingTax",
            "namuna8WaterTaxSettings",
            "namuna8GeneralWaterTaxSlabSettings",
            "generalSetting",
            "newYojna",
            "namuna9_year_setups",
            "namuna9_settings",
            "namuna9",
            "namuna9_property_association",
            "namuna7",
            "no_arrears_certificates",
            "birth_certificates",
            "death_certificates",
            "birthdeath_unavailability_certificates",
            "resident_certificates",
            "family_certificates",
            "toilet_certificates",
            "no_objection_certificates",
            "no_benefit_certificates",
            "life_certificates",
            "good_conduct_certificates",
            "niradhar_certificates",
            "unemployment_certificates",
            "receipt_certificates",
            "outward_entries",
        ]

        # 3. Import models dynamically
        model_modules = [
            "location_management.models",
            "namuna8.namuna8_model",
            "certificates.birth_certificate_model",
            "certificates.death_certificate_model",
            "certificates.family_certificate_model",
            "certificates.good_conduct_certificate_model",
            "certificates.life_certificate_model",
            "certificates.marriage_certificate_model",
            "certificates.niradhar_certificate_model",
            "certificates.no_arrears_certificate_model",
            "certificates.no_benefit_certificate_model",
            "certificates.no_objection_certificate_model",
            "certificates.receipt_certificate_model",
            "certificates.resident_certificate_model",
            "certificates.toilet_certificate_model",
            "certificates.unemployment_certificate_model",
            "certificates.widow_certificate_model",
            "certificates.birthdeath_unavailability_model",
            "namuna8.namuna7.namuna7_model",
            "namuna8.mastertab.mastertabmodels",
            "namuna8.PropertyDocuments.property_document_model",
            "namuna8.owner_history_model",
            "namuna8.property_owner_history_model",
            "namuna8.mastertab.transfer_apis",
            "namuna9.namuna9_model",
            "reportstab.outward_entries_model",
        ]

        all_models = {}
        for module_name in model_modules:
            try:
                module = importlib.import_module(module_name)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, "__tablename__") and hasattr(attr, "__table__"):
                        all_models[attr.__tablename__] = attr
                    # Also check for Table objects (like property_owner_association)
                    elif hasattr(attr, "name") and hasattr(attr, "columns"):
                        all_models[attr.name] = attr
            except ImportError:
                continue
        
        # Debug: Print loaded models
        print(f"DEBUG: Loaded models: {list(all_models.keys())}")
        if "property_owner_association" in all_models:
            print("DEBUG: property_owner_association model found")
        else:
            print("DEBUG: property_owner_association model NOT found")

        # 4. Date/boolean parsing helper
        def parse_datetime_fields(row, model):
            for column in model.__table__.columns:
                colname = column.name
                coltype = str(column.type)
                if colname in row:
                    # Handle Boolean fields
                    if isinstance(column.type, Boolean):
                        val = row[colname]
                        if isinstance(val, str):
                            if val.strip() in ["0", "false", "False", ""]:
                                row[colname] = False
                            elif val.strip() in ["1", "true", "True"]:
                                row[colname] = True
                        elif isinstance(val, int):
                            row[colname] = bool(val)
                    # Handle datetime/date fields
                    elif isinstance(row[colname], str):
                        if "DATETIME" in coltype.upper() or "TIMESTAMP" in coltype.upper():
                            try:
                                row[colname] = datetime.datetime.fromisoformat(row[colname])
                            except Exception:
                                try:
                                    row[colname] = datetime.datetime.strptime(
                                        row[colname], "%Y-%m-%d %H:%M:%S"
                                    )
                                except Exception:
                                    pass
                        elif "DATE" in coltype.upper():
                            try:
                                row[colname] = datetime.date.fromisoformat(row[colname])
                            except Exception:
                                try:
                                    row[colname] = datetime.datetime.strptime(
                                        row[colname], "%Y-%m-%d"
                                    ).date()
                                except Exception:
                                    pass
            return row

        # 5. Transaction block: delete + insert
        with db.begin():
            db.execute(text("PRAGMA foreign_keys = OFF;"))

            # Delete all tables
            for table in truncate_order:
                try:
                    db.execute(text(f"DELETE FROM {table};"))
                    db.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}';"))
                except Exception:
                    pass

            db.execute(text("PRAGMA foreign_keys = ON;"))

            # Insert new data
            for table in insert_order:
                rows = sync_data.get(table, [])
                model = all_models.get(table)
                if table == "property_owner_association":
                    print(f"DEBUG: Processing table {table} - model: {model is not None}, rows: {len(rows) if rows else 0}")
                if model is None or not rows:
                    if table == "property_owner_association":
                        print(f"DEBUG: Skipping {table} - model: {model is not None}, rows: {len(rows) if rows else 0}")
                    continue
                
                if table == "property_owner_association":
                    print(f"DEBUG: Processing {len(rows)} rows for {table}")
                    print(f"DEBUG: Model type: {type(model)}")
                for row in rows:
                    if table == "namuna9" and "property_ids" in row and isinstance(row["property_ids"], str):
                        import json

                        try:
                            row["property_ids"] = json.loads(row["property_ids"])
                        except Exception:
                            pass
                    
                    # Handle Table objects differently from Model classes
                    if table == "property_owner_association":
                        # For association tables, use direct insert
                        print(f"DEBUG: Attempting to insert row: {row}")
                        try:
                            result = db.execute(text(f"INSERT INTO {table} (id, owner_id) VALUES (:id, :owner_id)"), row)
                            print(f"DEBUG: Successfully inserted row: {row}")
                        except Exception as e:
                            print(f"DEBUG: Error inserting {table} row: {e}")
                            pass
                    else:
                        # For regular models, use ORM
                        try:
                            row = parse_datetime_fields(row, model)
                            db.add(model(**row))
                        except Exception as e:
                            print(f"DEBUG: Error inserting {table} row: {e}")
                            pass

        db.commit()
        print("DEBUG: Transaction committed successfully")
        return {"success": True, "message": "Local DB replaced with hosted data"}

    except Exception as e:
        return {"success": False, "message": str(e)}
