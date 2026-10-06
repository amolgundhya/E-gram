from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from namuna8 import namuna8_apis
from namuna9 import namuna9_apis
from namuna9 import namuna9_property_data_apis
from namuna9 import deleted_receipts_apis
from certificates import birth_certificate_apis, death_certificate_apis, birthdeath_unavailability_apis, resident_certificate_apis, family_certificate_apis, toilet_certificate_apis, no_objection_certificate_apis, no_benefit_certificate_apis, life_certificate_apis, good_conduct_certificate_apis, niradhar_certificate_apis, no_arrears_certificate_apis, unemployment_certificate_apis, receipt_certificate_apis, marriage_certificate_apis, widow_certificate_apis, allcertificates
from location_management import apis as location_apis
from namuna8.recordresponses import property_record_response
from namuna8.namuna7 import namuna7_apis
from namuna8.namuna7.ReportCreationUsingJinja import namuna7Print
from namuna8.utilitytab.owner_transfer_api import router as owner_transfer_router
from namuna8.utilitytab.owners_with_properties_api import router as owners_with_properties_router
from namuna8.mastertab.transfer_apis import router as transfer_router
from namuna8.madhila.madhila_apis import router as madhila_router
from namuna8.PropertyDocuments import property_document_apis
from ferfar.ReportCreationUsingJinja import ferfarprint
from namuna8 import ferfar_apis
from namuna8 import staff_apis

# Import database components and models
from database import engine, Base
from sqlalchemy import text
from namuna8 import namuna8_model
from namuna9 import namuna9_model
from JWTapi import tokenModel
from certificates import birth_certificate_model, receipt_certificate_model
from location_management import models as location_models
from namuna8.ReportCreationUsingJinja import namuna8Print
from namuna9.ReportCreationUsingJinja import namuna9Print
from Yadi.ReportCreationUsingJinja import yadiPrint
from namuna10.ReportCreationUsingJinja import namuna10print
from certificates.ReportCreationUsingJinja import certificate
from reportRoute import reportAPI
from JWTapi import tokenapi
from fastapi.staticfiles import StaticFiles
from namuna8.mastertab.mastertabapis import router as mastertab_router
from Ghoshawara.ReportCreationUsingJinja import ghoshawaraprint
from LogBook.ReportCreationUsingJinja import logbookPrint
from reportstab.outward_entries_apis import router as outward_entries_router

from location_management.models import District, Taluka, GramPanchayat
from certificates.marriage_certificate_model import MarriageCertificate
from certificates.widow_certificate_model import WidowCertificate
from certificates.receipt_certificate_model import ReceiptCertificate
from certificates.no_arrears_certificate_model import NoArrearsCertificate
from namuna8.namuna8_model import Property
from namuna8.property_owner_history_model import PropertyOwnerHistory
from namuna8.owner_history_model import OwnerHistory
from sqlalchemy.orm import Session
from namuna8.namuna8_model import ConstructionType
from namuna8 import staff_model
Base.metadata.create_all(bind=engine, checkfirst=True)

# Ensure critical certificate tables are created explicitly (helps in packaged/installer runs)
try:
    MarriageCertificate.__table__.create(bind=engine, checkfirst=True)
    WidowCertificate.__table__.create(bind=engine, checkfirst=True)
except Exception:
    # Safe to ignore; if engine is read-only or tables already exist
    pass

def init_construction_types():
    defaults = [
        {
            "id": 1,
            "name": "आरसीसी पद्धतीची इमारत",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        },
        {
            "id": 2,
            "name": "दगड विटांची व चुना किंवा सिमेंट वापरून उभारलेली इमारत",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        },
        {
            "id": 3,
            "name": "दगड किंवा विटा वापरलेली मातीची इमारत",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        },
        {
            "id": 4,
            "name": "झोपडी किंवा मातीची इमारत",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        },
        {
            "id": 5,
            "name": "टिन शेड",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        },
        {
            "id": 6,
            "name": "खाली जागा",
            "rate": 0.0,
            "bandhmastache_dar": 0.0,
            "bandhmastache_prakar": 0,
            "gharache_prakar": 0,
            "annualLandValueRate": 0.0,
            "district_id": 1,
            "taluka_id": 1,
            "gram_panchayat_id": 1
        }
    ]
    with Session(engine) as db:
        for row in defaults:
            exists = db.query(ConstructionType).filter_by(name=row["name"]).first()
            if not exists:
                db.add(ConstructionType(**row))
        db.commit()

# Call initializer after tables are created
init_construction_types()

# Ensure new columns exist for namuna9_property_data (SQLite simple migration)
def ensure_namuna9_property_data_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(namuna9_property_data)").fetchall()
            existing = {c[1] for c in cols}
            to_add = [
                ("vasuliGhar", "REAL"),
                ("vasuliChaluGhar", "REAL"),
                ("vasuliDiva", "REAL"),
                ("vasuliChaluDiva", "REAL"),
                ("vasuliAarogyaKar", "REAL"),
                ("vasuliChaluAarogyaKar", "REAL"),
                ("vasuliSapanikar", "REAL"),
                ("vasuliChaluSapanikar", "REAL"),
                ("vasuliVpanikar", "REAL"),
                ("vasuliChaluVpanikar", "REAL"),
                ("vasuliCleaningTax", "REAL"),
                ("vasuliChaluCleaningTax", "REAL"),
                ("vasuliDand", "REAL"),
                ("vasuliNoticeFee", "REAL"),
                ("vasuliWarrantFee", "REAL"),
            ]
            for col, coltype in to_add:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE namuna9_property_data ADD COLUMN "{col}" {coltype} DEFAULT 0')
    except Exception as e:
        print("[Migration] Could not ensure namuna9_property_data columns:", e)

ensure_namuna9_property_data_columns()

# Ensure new columns exist for properties (SQLite simple migration)
def ensure_properties_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(properties)").fetchall()
            existing = {c[1] for c in cols}
            to_add = [
                ("dwarPurv", "BOOLEAN"),
                ("dwarPashchim", "BOOLEAN"),
                ("dwarUttar", "BOOLEAN"),
                ("dwarDakshin", "BOOLEAN"),
                ("exServiceman", "BOOLEAN"),
            ]
            for col, coltype in to_add:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE properties ADD COLUMN "{col}" {coltype} DEFAULT 0')
            # Text columns must NOT get a numeric DEFAULT (would backfill existing
            # rows with the literal string "0" instead of blank/NULL).
            text_to_add = [
                ("toiletBenefitYear", "TEXT"),
                ("gharkul", "TEXT"),
                ("gharkulYojana", "TEXT"),
                ("gharkulBenefitYear", "TEXT"),
                ("constructionAreaUnit", "TEXT"),
            ]
            for col, coltype in text_to_add:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE properties ADD COLUMN "{col}" {coltype}')
    except Exception as e:
        print("[Migration] Could not ensure properties columns:", e)

ensure_properties_columns()

# मालमत्ता यादीतला डिस्प्ले-क्रम (sort_order) - जतन केलेला anuKramank (अ.क्र., QR/नमुना-9
# लिंकसाठी वापरलेला) कुठेच बदलत नाही; हा फक्त "कुठल्या क्रमाने दाखवायचं" ठरवणारा वेगळा
# आकडा आहे, कारण मालमत्ता क्रमांकाच्या मजकुरावरून (नैसर्गिक क्रमवारी) क्रम काढणं "1 भाग"
# सारख्या टाईप केलेल्या मजकुरासाठी अविश्वसनीय ठरतं.
def ensure_property_sort_order_column():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(properties)").fetchall()
            existing = {c[1] for c in cols}
            if "sort_order" not in existing:
                conn.exec_driver_sql('ALTER TABLE properties ADD COLUMN "sort_order" REAL')
    except Exception as e:
        print("[Migration] Could not ensure properties.sort_order column:", e)

ensure_property_sort_order_column()

# एकदाच चालणारा बॅकफिल - sort_order अजून सेट नसलेल्या रोंना (नवीन कॉलम जोडल्यावर सगळ्याच
# जुन्या रोंसाठी, किंवा दुसऱ्या क्लायंटच्या डेटाबेसवर पहिल्यांदा अपडेट केल्यावर) प्रत्येक
# गावासाठी वेगळं, सध्याच्या मालमत्ता-क्रमांक नैसर्गिक क्रमवारीनुसार 10,20,30... अशी मोकळी
# जागा ठेवून sort_order देतो. sort_order आधीच असलेल्या रोंना अजिबात स्पर्श करत नाही आणि
# जतन केलेला anuKramank किंवा इतर कुठलाही डेटा बदलत नाही, त्यामुळे सर्व्हर पुन्हा सुरू
# केला तरी सुरक्षितपणे पुन्हा चालतं (idempotent) - हीच पद्धत इतर क्लायंटच्या डेटाबेसवरही
# आपोआप एकदा चालून मालमत्ता यादीला sort_order देईल.
def backfill_property_sort_order():
    try:
        from database import SessionLocal
        from namuna8 import namuna8_model as namuna8_models
        from natural_sort import malmatta_kramank_sort_key
        db = SessionLocal()
        try:
            villages_with_gaps = (
                db.query(namuna8_models.Property.village_id)
                .filter(namuna8_models.Property.sort_order.is_(None))
                .distinct()
                .all()
            )
            for (village_id,) in villages_with_gaps:
                props = (
                    db.query(namuna8_models.Property)
                    .filter(namuna8_models.Property.village_id == village_id)
                    .all()
                )
                props_needing_order = [p for p in props if p.sort_order is None]
                if not props_needing_order:
                    continue
                existing_max = max(
                    [p.sort_order for p in props if p.sort_order is not None], default=0
                )
                ordered = sorted(props_needing_order, key=lambda p: malmatta_kramank_sort_key(p.malmattaKramank))
                for i, p in enumerate(ordered, start=1):
                    p.sort_order = existing_max + i * 10.0
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print("[Migration] Could not backfill properties.sort_order:", e)

backfill_property_sort_order()

# Ensure new columns exist for the Namuna8 print settings checklist (SQLite simple migration)
def ensure_namuna8_setting_checklist_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(namuna8_setting_checklist)").fetchall()
            existing = {c[1] for c in cols}
            to_add = [
                ("pageNumber", "BOOLEAN"),
                ("exServicemanTip", "BOOLEAN"),
                ("exportPassword", "VARCHAR"),
            ]
            for col, coltype in to_add:
                if col not in existing:
                    # TEXT/VARCHAR कॉलमला numeric DEFAULT देत नाही - फक्त BOOLEAN ला 0.
                    default_clause = " DEFAULT 0" if coltype == "BOOLEAN" else ""
                    conn.exec_driver_sql(f'ALTER TABLE namuna8_setting_checklist ADD COLUMN "{col}" {coltype}{default_clause}')
    except Exception as e:
        print("[Migration] Could not ensure namuna8_setting_checklist columns:", e)

ensure_namuna8_setting_checklist_columns()

# Ensure new tax-rounding setting column exists on namuna8DropdownAddSettings
# ("नमुना ८ संबंधी इतर सेटिंग") - existing rows default to "ceil" (जुनी पद्धत),
# त्यामुळे सेटिंग स्पष्टपणे न बदलल्यास काहीही बदलत नाही.
def ensure_namuna8_dropdown_settings_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql('PRAGMA table_info("namuna8DropdownAddSettings")').fetchall()
            existing = {c[1] for c in cols}
            if "taxRoundingMode" not in existing:
                conn.exec_driver_sql(
                    'ALTER TABLE "namuna8DropdownAddSettings" ADD COLUMN "taxRoundingMode" VARCHAR DEFAULT \'ceil\''
                )
                conn.exec_driver_sql(
                    'UPDATE "namuna8DropdownAddSettings" SET "taxRoundingMode" = \'ceil\' WHERE "taxRoundingMode" IS NULL'
                )
    except Exception as e:
        print("[Migration] Could not ensure namuna8DropdownAddSettings columns:", e)

ensure_namuna8_dropdown_settings_columns()

# Ensure new columns exist for namuna7 (SQLite simple migration)
def ensure_namuna7_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(namuna7)").fetchall()
            existing = {c[1] for c in cols}
            to_add = [
                ("malmattaKramank", "TEXT"),
                ("anuKramank", "INTEGER"),
                # सॉफ्ट-डिलीट (client requirement: पावती डिलीट केली तरी कायम ठेवायची).
                ("is_deleted", "BOOLEAN DEFAULT 0"),
                ("deleted_at", "DATETIME"),
                ("deleted_by", "TEXT"),
                ("delete_reason", "TEXT"),
            ]
            for col, coltype in to_add:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE namuna7 ADD COLUMN "{col}" {coltype}')
    except Exception as e:
        print("[Migration] Could not ensure namuna7 columns:", e)

ensure_namuna7_columns()

# Ensure new soft-delete columns exist for namuna9_receipts (SQLite simple
# migration, same pattern as above - existing receipts get is_deleted = 0).
def ensure_namuna9_receipts_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(namuna9_receipts)").fetchall()
            existing = {c[1] for c in cols}
            to_add = [
                ("is_deleted", "BOOLEAN DEFAULT 0"),
                ("deleted_at", "DATETIME"),
                ("deleted_by", "TEXT"),
                ("delete_reason", "TEXT"),
            ]
            for col, coltype in to_add:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE namuna9_receipts ADD COLUMN "{col}" {coltype}')
    except Exception as e:
        print("[Migration] Could not ensure namuna9_receipts columns:", e)

ensure_namuna9_receipts_columns()

# Ensure new columns exist for gram_panchayats (SQLite simple migration)
def ensure_gram_panchayats_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(gram_panchayats)").fetchall()
            existing = {c[1] for c in cols}
            text_cols = [("house_tax_qr_url", "TEXT"), ("water_tax_qr_url", "TEXT"), ("signature_url", "TEXT"), ("parent_gram_panchayat_name", "TEXT"), ("bank_scanner_password_hash", "TEXT")]
            bool_cols = [("show_bank_scanner_in_reports", "BOOLEAN")]
            for col, coltype in text_cols:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE gram_panchayats ADD COLUMN "{col}" {coltype}')
            for col, coltype in bool_cols:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE gram_panchayats ADD COLUMN "{col}" {coltype} DEFAULT 0')
    except Exception as e:
        print("[Migration] Could not ensure gram_panchayats columns:", e)

ensure_gram_panchayats_columns()

# Ensure new columns exist for gram_panchayat_staff (SQLite simple migration)
def ensure_gram_panchayat_staff_columns():
    try:
        with engine.begin() as conn:
            cols = conn.exec_driver_sql("PRAGMA table_info(gram_panchayat_staff)").fetchall()
            existing = {c[1] for c in cols}
            text_cols = [("remarks", "TEXT")]
            for col, coltype in text_cols:
                if col not in existing:
                    conn.exec_driver_sql(f'ALTER TABLE gram_panchayat_staff ADD COLUMN "{col}" {coltype}')
    except Exception as e:
        print("[Migration] Could not ensure gram_panchayat_staff columns:", e)

ensure_gram_panchayat_staff_columns()

# Ensure receipts table exists and has all expected columns (SQLite simple migration)
try:
    from namuna9.namuna9_model import Namuna9Receipt
    Namuna9Receipt.__table__.create(bind=engine, checkfirst=True)

    # Add missing columns if the table was created in an older version
    with engine.begin() as conn:
        cols = conn.exec_driver_sql("PRAGMA table_info(namuna9_receipts)").fetchall()
        existing = {c[1] for c in cols}
        to_add = [
            ("gram_panchayat_id", "INTEGER"),
            ("pa_book_kramank", "TEXT"),
            ("pavti_kramank", "INTEGER"),
            ("pavti_date", "DATETIME"),
            ("payment_mode", "TEXT"),
            ("utr_tr_id", "TEXT"),
            ("vasuliGhar", "REAL"),
            ("vasuliChaluGhar", "REAL"),
            ("vasuliDiva", "REAL"),
            ("vasuliChaluDiva", "REAL"),
            ("vasuliAarogyaKar", "REAL"),
            ("vasuliChaluAarogyaKar", "REAL"),
            ("vasuliSapanikar", "REAL"),
            ("vasuliChaluSapanikar", "REAL"),
            ("vasuliVpanikar", "REAL"),
            ("vasuliChaluVpanikar", "REAL"),
            ("vasuliCleaningTax", "REAL"),
            ("vasuliChaluCleaningTax", "REAL"),
            ("vasuliDand", "REAL"),
            ("vasuliNoticeFee", "REAL"),
            ("vasuliWarrantFee", "REAL"),
            ("total", "REAL"),
        ]
        for col, coltype in to_add:
            if col not in existing:
                conn.exec_driver_sql(f'ALTER TABLE namuna9_receipts ADD COLUMN "{col}" {coltype}')
except Exception as e:
    print("[Migration] Could not ensure namuna9_receipts:", e)
app = FastAPI()

# Remove or comment out the old static mount
# app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")
app.mount("/ReportImages" , StaticFiles(directory="ReportImages") , name="ReportImages")
# CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(namuna8_apis.router)
app.include_router(staff_apis.router)
app.include_router(namuna9_apis.router)
app.include_router(namuna9_property_data_apis.router)
app.include_router(deleted_receipts_apis.router)
app.include_router(birth_certificate_apis.router)
app.include_router(death_certificate_apis.router)
app.include_router(marriage_certificate_apis.router)
app.include_router(allcertificates.router)
app.include_router(widow_certificate_apis.router)
app.include_router(birthdeath_unavailability_apis.router)
app.include_router(resident_certificate_apis.router)
app.include_router(family_certificate_apis.router)
app.include_router(toilet_certificate_apis.router)
app.include_router(no_objection_certificate_apis.router)
app.include_router(no_benefit_certificate_apis.router)
app.include_router(life_certificate_apis.router)
app.include_router(good_conduct_certificate_apis.router)
app.include_router(niradhar_certificate_apis.router)
app.include_router(no_arrears_certificate_apis.router)
app.include_router(unemployment_certificate_apis.router)
app.include_router(receipt_certificate_apis.router)
app.include_router(property_record_response.router, prefix="/namuna8/recordresponses")
app.include_router(namuna8Print.router , prefix="/namuna8/print")
app.include_router(namuna9Print.router , prefix="/namuna9/print")
app.include_router(yadiPrint.router , prefix="/yadi/print")
app.include_router(tokenapi.router , prefix="/license")
app.include_router(ghoshawaraprint.router , prefix="/ghoshawara/print")
app.include_router(namuna10print.router , prefix="/namuna10/print")
app.include_router(certificate.router , prefix="/certificate/print")
app.include_router(logbookPrint.router , prefix="/logbook/print")
app.include_router(ferfarprint.router , prefix="/ferfar/print")
app.include_router(reportAPI.router , prefix="/reports")
app.include_router(namuna7_apis.router)
app.include_router(namuna7Print.router , prefix="/namuna7")
app.include_router(owner_transfer_router, prefix="/namuna8/utilitytab")
app.include_router(owners_with_properties_router, prefix="/namuna8/utilitytab")
app.include_router(mastertab_router)
app.include_router(transfer_router, prefix="/transfer-setting")
app.include_router(madhila_router)
app.include_router(property_document_apis.router)
app.include_router(outward_entries_router)
app.include_router(ferfar_apis.router, prefix="/ferfar")
app.include_router(location_apis.router)
# --- Auto-register routers in E-gram submodules ---
import importlib
import pkgutil
import sys

api_packages = [
    "namuna8",
    "namuna9",
    "certificates"
]

for package_name in api_packages:
    try:
        package = importlib.import_module(package_name)
        for _, modname, _ in pkgutil.iter_modules(package.__path__):
            module = importlib.import_module(f"{package_name}.{modname}")
            if hasattr(module, "router"):
                print(f"[Auto-register] Including router from {package_name}.{modname}")
                app.include_router(module.router)
    except Exception as e:
        print(f"[Auto-register] Skipped {package_name}: {e}")

# After all routers are included, mount static at root
app.mount("/reports", StaticFiles(directory="reports"), name="reports")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")
app.mount("/ReportImages", StaticFiles(directory="ReportImages"), name="ReportImages")
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# @app.get("/")
# def read_root():
#     return {"message": "Welcome to E-gram Panchayat API"}
from fastapi.responses import FileResponse
import os

@app.get("/")
def serve_react_index():
    return FileResponse(os.path.join("static", "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)