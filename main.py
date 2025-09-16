from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from namuna8 import namuna8_apis
from namuna9 import namuna9_apis
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

# Import database components and models
from database import engine, Base
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
            "name": "आर सी सी इमारत",
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
            "name": "दगड विट सिमेंटची इमारत",
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
            "name": "दगड मातीची इमारत",
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
            "name": "झोपडी मातीचे इमारत",
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
app.include_router(namuna9_apis.router)
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