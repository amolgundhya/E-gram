# "सर्व मालमत्तांचा कर पुन्हा मोजा" (UTILITY) - ग्रामपंचायतीच्या सर्व मालमत्तांच्या बांधकाम
# रो चं भांडवली मूल्य व घरपट्टी चालू नियमांनुसार (गॅझेट घसारा, construction_types मधले
# दर, आकारणी वर्ष) पुन्हा मोजतो - प्रत्येक मालमत्ता नमुना-8 मध्ये उघडून पुन्हा सेव्ह
# केल्यासारखाच निकाल (compute_construction_values हेच फंक्शन PUT सुद्धा वापरतो).
#
# सुरक्षितता:
#  - काहीही बदलण्याआधी DB ची पूर्ण बॅकअप प्रत (sqlite backup API, integrity_check सह);
#    बॅकअप जमला नाही तर काहीच बदलत नाही.
#  - सर्व बदल एकाच transaction मध्ये - commit आधी नमुना-8 प्रिंटचा डेटा (तोच
#    property_records_by_village) प्रत्येक मालमत्तेसाठी अपेक्षित घरपट्टीशी जुळतो का ते
#    तपासतो; एकही चूक/अपवाद आला तर संपूर्ण rollback (all-or-nothing).
#  - फक्त constructions.capitalValue / constructions.houseTax बदलतात. पावत्या
#    (namuna9_receipts), नमुना-9 (namuna9 / namuna9_property_data - चालू वा जुनी
#    कोणतीही वर्षं), मालमत्तेचं क्षेत्रफळ, मालक, QR फाईल्स - काहीच बदलत नाही. (QR
#    /namuna8/property_qrcode मागितल्यावर मजकूर बदलला असेल तर आपोआप नवीन बनतो.)
#  - आधी/नंतर अहवाल: बदललेल्या मालमत्ता, एकूण घरपट्टी आधी/नंतर आणि मालमत्तावार Excel.
import json
import os
import re
import sqlite3
import threading
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import selectinload

import database
from namuna8 import namuna8_model as models
from namuna8.mastertab import mastertabmodels as settingModels
from namuna8.calculations.naumuna8_calculations import calculate_depreciation_rate, get_assessment_year
from namuna8.calculations.construction_tax import compute_construction_values
from namuna8.recordresponses.property_record_response import get_property_records_by_village

BACKUP_DIR_NAME = "backups_before_tax_recalc"
REPORT_DIR_NAME = "tax_recalc_reports"
REPORT_FILE_RE = re.compile(r"tax_recalc_(preview_)?\d+_\d{8}_\d{6}\.xlsx")

# एकाच वेळी दोनदा (डबल क्लिक / दोन विंडो) चालू होऊ नये म्हणून.
_RUN_LOCK = threading.Lock()


class RecalculationBusy(Exception):
    pass


class RecalculationFailed(Exception):
    def __init__(self, message, backup_path=None):
        super().__init__(message)
        self.backup_path = backup_path


def _db_file():
    return os.path.abspath(database.engine.url.database)


def report_dir():
    return os.path.join(os.path.dirname(_db_file()), REPORT_DIR_NAME)


def report_path(file_name):
    """डाउनलोडसाठी - फक्त याच फीचरने बनवलेल्या नावाची फाईल, फक्त अहवाल फोल्डरमधून."""
    if not file_name or not REPORT_FILE_RE.fullmatch(file_name):
        return None
    path = os.path.join(report_dir(), file_name)
    return path if os.path.isfile(path) else None


def backup_database(stamp):
    """DB ची पूर्ण प्रत <DB फोल्डर>/backups_before_tax_recalc/ मध्ये. sqlite backup API
    वापरतो (फाईल कॉपी नाही) - अॅप चालू असतानाही सुसंगत प्रत मिळते. प्रत तपासूनच
    (integrity_check + बांधकाम/पावती रो संख्या) path परत करतो, नाहीतर RuntimeError."""
    src_path = _db_file()
    dest_dir = os.path.join(os.path.dirname(src_path), BACKUP_DIR_NAME)
    os.makedirs(dest_dir, exist_ok=True)
    dest_path = os.path.join(dest_dir, "grampanchayat_BEFORE_tax_recalc_%s.db" % stamp)
    src = sqlite3.connect(src_path)
    dest = sqlite3.connect(dest_path)
    try:
        src.backup(dest)
        ok = dest.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        for table in ("constructions", "properties", "namuna9_property_data", "namuna9_receipts"):
            q = "SELECT COUNT(*) FROM %s" % table
            if src.execute(q).fetchone()[0] != dest.execute(q).fetchone()[0]:
                ok = False
    finally:
        dest.close()
        src.close()
    if not ok:
        try:
            os.remove(dest_path)
        except OSError:
            pass
        raise RuntimeError("DB बॅकअप तपासणीत अयशस्वी")
    return dest_path


def _print_rows(db, district_id, taluka_id, gram_panchayat_id, village_ids):
    """(village_id, anuKramank) -> नमुना-8 प्रिंटचा रो (फ्रंटएंड प्रिंटला पाठवतो तोच डेटा)."""
    rows = {}
    for village_id in sorted(village_ids):
        resp = get_property_records_by_village(
            village_id=village_id, district_id=district_id, taluka_id=taluka_id,
            gram_panchayat_id=gram_panchayat_id, db=db,
        )
        # Windows 10 बॅकएंड JSONResponse परत करतो, Win8 बॅकएंड साधी list - दोन्ही चालतात.
        records = json.loads(resp.body) if hasattr(resp, "body") else resp
        for r in records:
            rows[(village_id, str(r.get("id")))] = r
    return rows


def _money(v):
    return round(float(v or 0), 2)


def run_recalculation(db, district_id, taluka_id, gram_panchayat, dry_run=False):
    if not _RUN_LOCK.acquire(blocking=False):
        raise RecalculationBusy()
    try:
        return _run(db, district_id, taluka_id, gram_panchayat, dry_run)
    finally:
        _RUN_LOCK.release()


def _run(db, district_id, taluka_id, gram_panchayat, dry_run):
    gram_panchayat_id = gram_panchayat.id
    started = datetime.now()
    stamp = started.strftime("%Y%m%d_%H%M%S")
    assessment_year = get_assessment_year(gram_panchayat)
    # संपादन (PUT) सारखेच सेटिंग्ज
    general_setting = db.query(settingModels.GeneralSetting).filter_by().first()
    formula1 = general_setting.capitalFormula1 if general_setting else None
    weightage_map = {row.building_usage: row.weightage for row in db.query(settingModels.BuildingUsageWeightage).all()}

    properties = (
        db.query(models.Property)
        .options(selectinload(models.Property.constructions).selectinload(models.Construction.construction_type))
        .filter(models.Property.gram_panchayat_id == gram_panchayat_id)
        .all()
    )
    village_ids = {p.village_id for p in properties}
    before_print = _print_rows(db, district_id, taluka_id, gram_panchayat_id, village_ids)

    # 1) फक्त मोजणी - अजून काहीही बदलत नाही.
    plan = []          # (construction, new_cap, new_tax)
    prop_rows = []
    cons_rows = []
    skipped = []
    for prop in properties:
        unit = getattr(prop, 'constructionAreaUnit', None) or getattr(prop, 'areaUnit', None) or 'sqft'
        old_sum_tax = new_sum_tax = 0.0
        old_sum_cap = new_sum_cap = 0.0
        prop_changed = False
        for c in prop.constructions:
            ctype = c.construction_type
            if ctype is None:
                skipped.append({"property_id": prop.id, "malmattaKramank": prop.malmattaKramank, "construction_id": c.id,
                                "reason": "बांधकाम प्रकार सापडला नाही"})
                continue
            new_cap, new_tax = compute_construction_values(
                db, ctype, c.length, c.width, c.constructionYear, c.bharank,
                unit, assessment_year, formula1, weightage_map, prop.gram_panchayat_id,
            )
            old_cap, old_tax = c.capitalValue, c.houseTax
            changed = (old_cap is None or round(old_cap, 2) != new_cap
                       or old_tax is None or float(old_tax) != float(new_tax))
            if changed:
                prop_changed = True
                plan.append((c, new_cap, new_tax))
            old_sum_tax += float(old_tax or 0)
            new_sum_tax += float(new_tax)
            old_sum_cap += float(old_cap or 0)
            new_sum_cap += float(new_cap)
            cons_rows.append({
                "property": prop, "construction": c, "type": ctype.name,
                "depreciation": calculate_depreciation_rate(c.constructionYear, ctype.name, assessment_year),
                "old_cap": old_cap, "new_cap": new_cap, "old_tax": old_tax, "new_tax": new_tax, "changed": changed,
            })
        pr = before_print.get((prop.village_id, str(prop.anuKramank)), {})
        kar_lagu_nahi = bool(prop.karLaguNahi)
        print_tax_before = float(pr.get("totalHouseTax") or 0)
        print_cap_before = float(pr.get("totalCapitalValue") or 0)
        if kar_lagu_nahi:
            # प्रिंट/नमुना-9 वर कर लागू नाही => नेहमी 0, बांधकाम रो मात्र (PUT प्रमाणेच) मोजलेले राहतात.
            print_tax_after, print_cap_after = 0.0, 0.0
        else:
            print_tax_after = print_tax_before - old_sum_tax + new_sum_tax
            print_cap_after = print_cap_before - old_sum_cap + new_sum_cap
        prop_rows.append({
            "property": prop, "print": pr, "changed": prop_changed, "karLaguNahi": kar_lagu_nahi,
            "tax_before": print_tax_before, "tax_after": print_tax_after,
            "cap_before": print_cap_before, "cap_after": print_cap_after,
        })

    summary = {
        "dry_run": bool(dry_run),
        "gram_panchayat": gram_panchayat.name,
        "assessment_year": assessment_year,
        "properties_total": len(properties),
        "properties_changed": sum(1 for r in prop_rows if r["changed"]),
        "properties_print_tax_changed": sum(1 for r in prop_rows if round(r["tax_before"], 2) != round(r["tax_after"], 2)),
        "constructions_total": len(cons_rows),
        "constructions_changed": len(plan),
        "total_house_tax_before": _money(sum(r["tax_before"] for r in prop_rows)),
        "total_house_tax_after": _money(sum(r["tax_after"] for r in prop_rows)),
        "total_capital_value_before": _money(sum(r["cap_before"] for r in prop_rows)),
        "total_capital_value_after": _money(sum(r["cap_after"] for r in prop_rows)),
        "skipped": skipped,
        "backup_path": None,
        "started_at": started.isoformat(timespec="seconds"),
    }

    if not dry_run and plan:
        # 2) बॅकअप - जमला नाही तर इथेच थांबतो (DB ला हात लावलेला नाही).
        try:
            summary["backup_path"] = backup_database(stamp)
        except Exception as e:
            raise RecalculationFailed("DB बॅकअप घेता आला नाही, म्हणून कर पुन्हा मोजला नाही: %s" % e)
        # 3) एकाच transaction मध्ये बदल + commit आधी प्रिंट डेटाशी पडताळणी.
        try:
            for c, new_cap, new_tax in plan:
                c.capitalValue = new_cap
                c.houseTax = new_tax
            db.flush()
            after_print = _print_rows(db, district_id, taluka_id, gram_panchayat_id, village_ids)
            mismatches = []
            for r in prop_rows:
                p = r["property"]
                got = float(after_print.get((p.village_id, str(p.anuKramank)), {}).get("totalHouseTax") or 0)
                if round(got, 2) != round(r["tax_after"], 2):
                    mismatches.append("%s: अपेक्षित %s, प्रिंट %s" % (p.malmattaKramank, r["tax_after"], got))
            if mismatches:
                raise RuntimeError("पडताळणी अयशस्वी (%d मालमत्ता) - उदा. %s" % (len(mismatches), "; ".join(mismatches[:5])))
            db.commit()
        except Exception as e:
            db.rollback()
            raise RecalculationFailed("कर पुन्हा मोजताना त्रुटी - कोणताही बदल जतन केला नाही (rollback): %s" % e,
                                      backup_path=summary["backup_path"])

    # 4) Excel अहवाल (commit नंतर - अहवाल लिहिता आला नाही तरी कर बदल योग्यच राहतात).
    summary["finished_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        os.makedirs(report_dir(), exist_ok=True)
        file_name = "tax_recalc_%s%d_%s.xlsx" % ("preview_" if dry_run else "", gram_panchayat_id, stamp)
        build_report_workbook(summary, prop_rows, cons_rows).save(os.path.join(report_dir(), file_name))
        summary["report_file"] = file_name
    except Exception as e:
        summary["report_file"] = None
        summary["report_error"] = str(e)
    summary["examples"] = [
        {"malmattaKramank": r["property"].malmattaKramank, "tax_before": _money(r["tax_before"]), "tax_after": _money(r["tax_after"])}
        for r in prop_rows if r["changed"]
    ][:10]
    summary["success"] = True
    return summary


# ---------------- Excel ----------------
_HEAD_FONT = Font(bold=True)
_HEAD_FILL = PatternFill("solid", fgColor="DDEBF7")
_CHANGED_FILL = PatternFill("solid", fgColor="FFF2CC")


def _sheet(wb, title, columns, first=False):
    ws = wb.active if first else wb.create_sheet()
    ws.title = title
    for i, (name, width) in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=i, value=name)
        cell.font = _HEAD_FONT
        cell.fill = _HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.freeze_panes = "A2"
    return ws


def build_report_workbook(summary, prop_rows, cons_rows):
    wb = Workbook()
    ws = _sheet(wb, "सारांश", [("तपशील", 42), ("मूल्य", 60)], first=True)
    lines = [
        ("ग्रामपंचायत", summary["gram_panchayat"]),
        ("प्रकार", "पूर्वावलोकन (काहीही बदललेलं नाही)" if summary["dry_run"] else "कर पुन्हा मोजला व जतन केला"),
        ("दिनांक / वेळ", summary["started_at"].replace("T", " ")),
        ("घसारा आकारणी वर्ष", summary["assessment_year"]),
        ("एकूण मालमत्ता", summary["properties_total"]),
        ("बदललेल्या मालमत्ता (बांधकाम रो)", summary["properties_changed"]),
        ("प्रिंटवरील घरपट्टी बदललेल्या मालमत्ता", summary["properties_print_tax_changed"]),
        ("बदललेले बांधकाम रो", "%s / %s" % (summary["constructions_changed"], summary["constructions_total"])),
        ("एकूण घरपट्टी - आधी", summary["total_house_tax_before"]),
        ("एकूण घरपट्टी - नंतर", summary["total_house_tax_after"]),
        ("फरक", _money(summary["total_house_tax_after"] - summary["total_house_tax_before"])),
        ("एकूण भांडवली मूल्य - आधी", summary["total_capital_value_before"]),
        ("एकूण भांडवली मूल्य - नंतर", summary["total_capital_value_after"]),
        ("DB बॅकअप", summary.get("backup_path") or "-"),
        ("टीप", "पावत्या व नमुना-9 (कोणतंही वर्ष) बदललेले नाहीत. कर लागू नाही असलेल्या मालमत्तांची प्रिंट/नमुना-9 घरपट्टी 0 च राहते."),
    ]
    for r, (k, v) in enumerate(lines, start=2):
        ws.cell(row=r, column=1, value=k).font = _HEAD_FONT
        ws.cell(row=r, column=2, value=v).alignment = Alignment(wrap_text=True)

    cols = [("अ.क्र.", 8), ("गाव", 16), ("मालमत्ता क्रमांक", 14), ("मालमत्ता धारकाचे नाव", 34), ("कर लागू नाही", 10),
            ("भांडवली मूल्य - आधी", 18), ("भांडवली मूल्य - नंतर", 18), ("घरपट्टी - आधी", 14), ("घरपट्टी - नंतर", 14),
            ("फरक", 12), ("बदल", 8)]
    ws = _sheet(wb, "मालमत्तावार", cols)
    prop_rows = sorted(prop_rows, key=lambda r: (r["property"].village_id, r["print"].get("srNo") or 0))
    row = 2
    for r in prop_rows:
        pr = r["print"]
        values = [pr.get("srNo"), pr.get("village"), r["property"].malmattaKramank, pr.get("ownerName"),
                  "होय" if r["karLaguNahi"] else "", _money(r["cap_before"]), _money(r["cap_after"]),
                  _money(r["tax_before"]), _money(r["tax_after"]), _money(r["tax_after"] - r["tax_before"]),
                  "होय" if r["changed"] else ""]
        for i, v in enumerate(values, start=1):
            cell = ws.cell(row=row, column=i, value=v)
            if r["changed"]:
                cell.fill = _CHANGED_FILL
        row += 1
    ws.cell(row=row, column=4, value="एकूण").font = _HEAD_FONT
    for i, key in ((6, "cap_before"), (7, "cap_after"), (8, "tax_before"), (9, "tax_after")):
        ws.cell(row=row, column=i, value=_money(sum(r[key] for r in prop_rows))).font = _HEAD_FONT
    ws.cell(row=row, column=10, value=_money(sum(r["tax_after"] - r["tax_before"] for r in prop_rows))).font = _HEAD_FONT
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(cols)), row - 1)

    cols = [("मालमत्ता क्रमांक", 14), ("बांधकाम प्रकार", 40), ("मजला", 10), ("बांधकाम वर्ष", 12), ("लांबी", 9), ("रुंदी", 9),
            ("घसारा %", 9), ("भांडवली मूल्य - आधी", 18), ("भांडवली मूल्य - नंतर", 18), ("घरपट्टी - आधी", 14),
            ("घरपट्टी - नंतर", 14), ("बदल", 8)]
    ws = _sheet(wb, "बांधकामवार", cols)
    for row, r in enumerate(cons_rows, start=2):
        c = r["construction"]
        values = [r["property"].malmattaKramank, r["type"], c.floor, c.constructionYear, c.length, c.width,
                  r["depreciation"], r["old_cap"], r["new_cap"], r["old_tax"], r["new_tax"], "होय" if r["changed"] else ""]
        for i, v in enumerate(values, start=1):
            cell = ws.cell(row=row, column=i, value=v)
            if r["changed"]:
                cell.fill = _CHANGED_FILL
    ws.auto_filter.ref = "A1:%s%d" % (get_column_letter(len(cols)), max(len(cons_rows) + 1, 1))
    return wb
