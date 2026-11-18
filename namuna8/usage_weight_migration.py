# एकदाच (migration_flags): नमुना-8 ड्रॉपडाउनने साठवलेलं जुनं वापर-नाव ("वाणिज्य") मास्टरमधल्या
# नावाने ("वाणिज्यिक") बदलतो, मग फक्त त्याच मालमत्तांचा कर "सर्व कर पुन्हा मोजा" सारखाच
# (compute_construction_values, मालमत्तेचे सर्व बांधकाम रो) पुन्हा मोजतो आणि त्यांचाच चालू
# नमुना-9 रो (current_year_sync.sync_property - फक्त सर्वात नवीन वर्ष, आधीच जतन झालेला रो)
# अद्ययावत करतो. आधी नाव जुळत नसल्याने भारांक 1 धरला जायचा (Utility/usage_weight.py).
#
# सुरक्षितता: बदल असतील तरच आधी DB बॅकअप (Databasessqllite मध्येच, integrity_check सह);
# बॅकअप न झाल्यास काहीच बदलत नाही व flag लावत नाही (पुढच्या वेळी पुन्हा प्रयत्न). सर्व बदल +
# flag एकाच transaction मध्ये - त्रुटी आली तर संपूर्ण rollback. पावत्या, वसुली, मागील बाकी,
# दंड/फी, जुनी नमुना-9 वर्षं बदलत नाहीत. प्रत्येक मालमत्ता (आधी -> नंतर घरपट्टी) लॉग होते.
import sqlite3
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import selectinload

import database
from namuna8 import namuna8_model as models
from namuna8.mastertab import mastertabmodels as settingModels
from namuna8.calculations.naumuna8_calculations import get_assessment_year
from namuna8.calculations.construction_tax import compute_construction_values
from location_management import models as location_models
from namuna9 import current_year_sync
from Utility.usage_weight import USAGE_ALIASES

MIGRATION_FLAG_USAGE_NAME = "bharank_vanijya_name_fix"


def _log(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))


def _backup(db_file, stamp):
    backup_file = "%s.before_bharank_fix_%s.db" % (db_file, stamp)
    src = sqlite3.connect(db_file)
    dst = sqlite3.connect(backup_file)
    try:
        src.backup(dst)
        ok = dst.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for table in ("constructions", "properties", "namuna9_property_data", "namuna9_receipts"):
            q = "SELECT COUNT(*) FROM %s" % table
            if src.execute(q).fetchone()[0] != dst.execute(q).fetchone()[0]:
                ok = False
    finally:
        dst.close()
        src.close()
    if not ok:
        raise RuntimeError("DB बॅकअप तपासणीत अयशस्वी: %s" % backup_file)
    return backup_file


def fix_usage_names_once(engine=None):
    engine = engine or database.engine
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE IF NOT EXISTS migration_flags (name TEXT PRIMARY KEY, applied_at TEXT)")
            if conn.exec_driver_sql("SELECT 1 FROM migration_flags WHERE name = ?", (MIGRATION_FLAG_USAGE_NAME,)).fetchone():
                return None
    except Exception as e:
        _log("[Migration] भारांक नाव: migration_flags तपासता आलं नाही: %s" % e)
        return None

    db = database.SessionLocal()
    try:
        master = {r.building_usage for r in db.query(settingModels.BuildingUsageWeightage).all()}
        # फक्त ज्या alias चं मास्टर नाव खरंच आहे आणि alias स्वतः मास्टरमध्ये नाही तेच बदलतो.
        renames = {old: new for old, new in USAGE_ALIASES.items() if new in master and old not in master}
        rows = []
        if renames:
            rows = [c for c in db.query(models.Construction).filter(models.Construction.bharank.isnot(None)).all()
                    if (c.bharank or "").strip() in renames]
        property_ids = sorted({c.property_id for c in rows})

        backup_file = None
        if rows:
            backup_file = _backup(database.engine.url.database, datetime.now().strftime("%Y%m%d_%H%M%S"))
            _log("[Migration] भारांक नाव: बॅकअप %s" % backup_file)

        general_setting = db.query(settingModels.GeneralSetting).filter_by().first()
        formula1 = general_setting.capitalFormula1 if general_setting else None
        weightage_map = {r.building_usage: r.weightage for r in db.query(settingModels.BuildingUsageWeightage).all()}
        assessment_years, n9_ctx = {}, {}
        changed = []
        for c in rows:
            c.bharank = renames[c.bharank.strip()]
        db.flush()
        props = (db.query(models.Property)
                 .options(selectinload(models.Property.constructions).selectinload(models.Construction.construction_type))
                 .filter(models.Property.id.in_(property_ids)).all()) if property_ids else []
        for prop in props:
            gp_id = prop.gram_panchayat_id
            if gp_id not in assessment_years:
                gp = db.query(location_models.GramPanchayat).filter_by(id=gp_id).first()
                assessment_years[gp_id] = get_assessment_year(gp)
                n9_ctx[gp_id] = current_year_sync.demand_context(db, gp_id)
            unit = getattr(prop, 'constructionAreaUnit', None) or getattr(prop, 'areaUnit', None) or 'sqft'
            old_tax = new_tax = 0.0
            for c in prop.constructions:
                if c.construction_type is None:
                    continue
                cap, tax = compute_construction_values(
                    db, c.construction_type, c.length, c.width, c.constructionYear, c.bharank,
                    unit, assessment_years[gp_id], formula1, weightage_map, gp_id,
                )
                old_tax += float(c.houseTax or 0)
                new_tax += float(tax)
                c.capitalValue = cap
                c.houseTax = tax
            db.flush()
            n9 = current_year_sync.sync_property(db, prop, ctx=n9_ctx[gp_id], commit=False)
            changed.append(prop.id)
            _log("[Migration] भारांक नाव: मालमत्ता %s (id=%s) बांधकाम घरपट्टी %s -> %s, नमुना-9 %s"
                 % (prop.malmattaKramank, prop.id, old_tax, new_tax,
                    ("%s अद्ययावत" % n9["yearslap"]) if n9 and n9.get("updated") else "बदल नाही / रो नाही"))
        db.execute(text("INSERT INTO migration_flags (name, applied_at) VALUES (:n, :t)"),
                   {"n": MIGRATION_FLAG_USAGE_NAME, "t": datetime.now().isoformat()})
        db.commit()
        _log("[Migration] भारांक नाव ('वाणिज्य' -> 'वाणिज्यिक'): %d बांधकाम रो, %d मालमत्ता पुन्हा मोजल्या (one-time)."
             % (len(rows), len(changed)))
        return {"constructions": len(rows), "properties": changed, "backup": backup_file}
    except Exception as e:
        db.rollback()
        _log("[Migration] भारांक नाव दुरुस्ती अयशस्वी (काहीही बदललं नाही): %s" % e)
        return None
    finally:
        db.close()
