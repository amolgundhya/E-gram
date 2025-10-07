from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import get_db
from datetime import datetime
from certificates.birth_certificate_model import BirthCertificate
from certificates.death_certificate_model import DeathCertificate
from certificates.birthdeath_unavailability_model import BirthDeathUnavailabilityCertificate
from certificates.resident_certificate_model import ResidentCertificate
from certificates.family_certificate_model import FamilyCertificate
from certificates.toilet_certificate_model import ToiletCertificate
from certificates.no_objection_certificate_model import NoObjectionCertificate
from certificates.no_benefit_certificate_model import NoBenefitCertificate
from certificates.life_certificate_model import LifeCertificate
from certificates.good_conduct_certificate_model import GoodConductCertificate
from certificates.niradhar_certificate_model import NiradharCertificate
from certificates.marriage_certificate_model import MarriageCertificate
from certificates.no_arrears_certificate_model import NoArrearsCertificate
from certificates.widow_certificate_model import WidowCertificate
from certificates.unemployment_certificate_model import UnemploymentCertificate
from location_management import models as location_models

router = APIRouter(prefix="/certificates", tags=["certificates"])

@router.get("/all", response_model=dict)
def get_all_certificates(
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db)
):
    # Parse dates
    from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
    to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
    result = []
    # Track common location IDs across all records
    district_ids = set()
    taluka_ids = set()
    gp_ids = set()
    # Simple caches to avoid repeated DB hits
    district_cache: dict[int, str | None] = {}
    taluka_cache: dict[int, str | None] = {}
    gp_cache: dict[int, str | None] = {}

    def get_district_name(district_id):
        if not district_id:
            return None
        if district_id in district_cache:
            return district_cache[district_id]
        district = db.query(location_models.District).filter(location_models.District.id == district_id).first()
        name = getattr(district, "name", None) if district else None
        district_cache[district_id] = name
        return name

    def get_taluka_name(taluka_id):
        if not taluka_id:
            return None
        if taluka_id in taluka_cache:
            return taluka_cache[taluka_id]
        taluka = db.query(location_models.Taluka).filter(location_models.Taluka.id == taluka_id).first()
        name = getattr(taluka, "name", None) if taluka else None
        taluka_cache[taluka_id] = name
        return name

    def get_gp_name(gp_id):
        if not gp_id:
            return None
        if gp_id in gp_cache:
            return gp_cache[gp_id]
        gp = db.query(location_models.GramPanchayat).filter(location_models.GramPanchayat.id == gp_id).first()
        name = getattr(gp, "name", None) if gp else None
        gp_cache[gp_id] = name
        return name

    # Helper: add certs to result
    def add_certs(query, cert_type, name_field, date_field, id_field, village_field):
        for cert in query:
            # Track IDs for top-level fields
            did = getattr(cert, "district_id", None)
            tid = getattr(cert, "taluka_id", None)
            gid = getattr(cert, "gram_panchayat_id", None)
            if did is not None:
                district_ids.add(did)
            if tid is not None:
                taluka_ids.add(tid)
            if gid is not None:
                gp_ids.add(gid)
            # Append record without repeating location names
            result.append({
                "type": cert_type,
                "name": getattr(cert, name_field, ""),
                "village": getattr(cert, village_field, ""),
                "registered_date": getattr(cert, date_field, None),
                "certificate_id": getattr(cert, id_field, None),
                "price": 20,
            })
    # Query each table (except receipt certificates)
    # BirthCertificate: child_name
    add_certs(
        db.query(BirthCertificate).filter(BirthCertificate.register_date.between(from_dt, to_dt)),
        "जन्म दाखला", "child_name", "register_date", "id", "village"
    )
    # DeathCertificate: deceased_name
    add_certs(
        db.query(DeathCertificate).filter(DeathCertificate.register_date.between(from_dt, to_dt)),
        "मृत्यू दाखला", "deceased_name", "register_date", "id", "village"
    )
    # BirthDeathUnavailabilityCertificate: applicant_name
    add_certs(
        db.query(BirthDeathUnavailabilityCertificate).filter(BirthDeathUnavailabilityCertificate.register_date.between(from_dt, to_dt)),
        "जन्म मृत्यू अनुपलब्धता दाखला", "applicant_name", "register_date", "id", "village"
    )
    # ResidentCertificate: applicant_name
    add_certs(
        db.query(ResidentCertificate).filter(ResidentCertificate.date.between(from_dt, to_dt)),
        "रहिवासी दाखला", "applicant_name", "date", "id", "village"
    )
    # FamilyCertificate: family_name
    add_certs(
        db.query(FamilyCertificate).filter(FamilyCertificate.registration_date.between(from_dt, to_dt)),
        "दारिद्र्य रेषेखालील दाखला", "family_name", "registration_date", "id", "village"
    )
    # ToiletCertificate: applicant_name
    add_certs(
        db.query(ToiletCertificate).filter(ToiletCertificate.registration_date.between(from_dt, to_dt)),
        "शौचालय दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # NoObjectionCertificate: applicant_name
    add_certs(
        db.query(NoObjectionCertificate).filter(NoObjectionCertificate.registration_date.between(from_dt, to_dt)),
        "ना हरकत प्रमाणपत्र", "applicant_name", "registration_date", "id", "village"
    )
    # NoBenefitCertificate: applicant_name
    add_certs(
        db.query(NoBenefitCertificate).filter(NoBenefitCertificate.registration_date.between(from_dt, to_dt)),
        "लाभ न मिळाल्याचे प्रमाणपत्र", "applicant_name", "registration_date", "id", "village"
    )
    # LifeCertificate: applicant_name
    add_certs(
        db.query(LifeCertificate).filter(LifeCertificate.registration_date.between(from_dt, to_dt)),
        "हयातीचा दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # GoodConductCertificate: applicant_name
    add_certs(
        db.query(GoodConductCertificate).filter(GoodConductCertificate.registration_date.between(from_dt, to_dt)),
        "चांगल्या वर्तनाचीचा दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # NiradharCertificate: applicant_name
    add_certs(
        db.query(NiradharCertificate).filter(NiradharCertificate.registration_date.between(from_dt, to_dt)),
        "निराधार दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # MarriageCertificate: wife_name
    add_certs(
        db.query(MarriageCertificate).filter(MarriageCertificate.registration_date.between(from_dt, to_dt)),
        "विवाहाचा दाखला", "wife_name", "registration_date", "id", "village"
    )
    # NoArrearsCertificate: applicant_name
    add_certs(
        db.query(NoArrearsCertificate).filter(NoArrearsCertificate.registration_date.between(from_dt, to_dt)),
        "थकबाकी नसल्याचा दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # WidowCertificate: applicant_name
    add_certs(
        db.query(WidowCertificate).filter(WidowCertificate.registration_date.between(from_dt, to_dt)),
        "विधवा असल्याचा दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # UnemploymentCertificate: applicant_name
    add_certs(
        db.query(UnemploymentCertificate).filter(UnemploymentCertificate.registration_date.between(from_dt, to_dt)),
        "बेरोजगाराचा दाखला", "applicant_name", "registration_date", "id", "village"
    )
    # Sort by registered_date
    result.sort(key=lambda x: (x["registered_date"] or datetime.min))

    # Compute top-level location names (only if consistent across records)
    jilha = get_district_name(next(iter(district_ids))) if len(district_ids) == 1 else None
    taluka = get_taluka_name(next(iter(taluka_ids))) if len(taluka_ids) == 1 else None
    gram_panchayat = get_gp_name(next(iter(gp_ids))) if len(gp_ids) == 1 else None

    return {
        "jilha": jilha,
        "taluka": taluka,
        "gramPanchayat": gram_panchayat,
        "records": result,
    }