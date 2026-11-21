"""नवीन कॉलम रिकामे (NULL) राहिले असतील तर त्यांना सुरक्षित मूल्य - सर्व्हर सुरू होताना आणि
प्रत्येक Import (IMP. DATA FRM DB) नंतर चालतो.

का: hosted सर्व्हरवरचा जुना बॅकअप (किंवा नवीन कॉलम न ठेवणारा सर्व्हर) Import केल्यावर हे
कॉलम रिकामे येतात - उदा. sort_order नसेल तर मालमत्ता यादीचा अ.क्र. क्रम बिघडतो, is_deleted
रिकामं असेल तर पावती कुठल्याच यादीत दिसत नाही (यादी `is_deleted == False` ने गाळते).

नियम: फक्त NULL असलेल्या रोंनाच मूल्य देतो - आधीच मूल्य असलेल्या रोंना अजिबात स्पर्श करत
नाही, त्यामुळे कितीही वेळा चालवलं तरी सुरक्षित (idempotent). टेबल/कॉलम नसेल तर तो भाग
सोडून देतो.

मुद्दाम न भरलेले कॉलम:
  - properties.constructionAreaUnit: रिकामं = "एकूण जागेच्याच एककात" (areaUnit) - इथे
    'sqft' भरल्यास चौ.मी. मालमत्तांचं बांधकाम चौ.फु. धरलं जाऊन कर बदलेल.
  - घरकुल / शौचालय लाभ वर्ष / योजना: रिकामं = माहिती नाही, तेच बरोबर.
"""
from natural_sort import malmatta_kramank_sort_key

# (टेबल, कॉलम) -> NULL असल्यास द्यायचं मूल्य (मॉडेलमधल्या default प्रमाणेच)
NULL_DEFAULTS = [
    ("properties", "dwarPurv", 0),
    ("properties", "dwarPashchim", 0),
    ("properties", "dwarUttar", 0),
    ("properties", "dwarDakshin", 0),
    ("properties", "exServiceman", 0),
    ("namuna9_property_data", "shaktiToiletTax", 0.0),
    ("namuna9_property_data", "chaluToiletTax", 0.0),
    ("namuna9_property_data", "ekunToiletTax", 0.0),
    ("namuna9_property_data", "vasuliToiletTax", 0.0),
    ("namuna9_property_data", "vasuliChaluToiletTax", 0.0),
    ("namuna9_receipts", "vasuliToiletTax", 0.0),
    ("namuna9_receipts", "vasuliChaluToiletTax", 0.0),
    ("namuna9_receipts", "is_deleted", 0),
    ("namuna7", "is_deleted", 0),
    ("gram_panchayats", "show_bank_scanner_in_reports", 0),
    ("namuna8_setting_checklist", "pageNumber", 0),
    ("namuna8_setting_checklist", "exServicemanTip", 0),
    ("namuna8DropdownAddSettings", "taxRoundingMode", "ceil"),
]

SORT_ORDER_STEP = 10.0


def _columns(conn, table):
    return {row[1] for row in conn.exec_driver_sql('PRAGMA table_info("%s")' % table).fetchall()}


def _backfill_sort_order(conn):
    """sort_order नसलेल्या मालमत्तांना, प्रत्येक गावासाठी वेगळं, मालमत्ता क्रमांकाच्या नैसर्गिक
    क्रमवारीनुसार (Serialize सारखीच) त्या गावातल्या सध्याच्या सर्वात मोठ्या sort_order नंतर
    10, 20, 30... - आधी sort_order असलेल्या रोंचा क्रम तसाच राहतो. anuKramank बदलत नाही."""
    cols = _columns(conn, "properties")
    if not {"sort_order", "village_id", "malmattaKramank"} <= cols:
        return 0
    rows = conn.exec_driver_sql(
        "SELECT id, village_id, malmattaKramank, sort_order FROM properties"
    ).fetchall()
    by_village = {}
    for row_id, village_id, malmatta, sort_order in rows:
        by_village.setdefault(village_id, []).append((row_id, malmatta, sort_order))
    filled = 0
    for village_rows in by_village.values():
        missing = [r for r in village_rows if r[2] is None]
        if not missing:
            continue
        existing_max = max([r[2] for r in village_rows if r[2] is not None], default=0)
        missing.sort(key=lambda r: malmatta_kramank_sort_key(r[1]))
        for i, (row_id, _malmatta, _so) in enumerate(missing, start=1):
            conn.exec_driver_sql(
                "UPDATE properties SET sort_order = ? WHERE id = ? AND sort_order IS NULL",
                (existing_max + i * SORT_ORDER_STEP, row_id),
            )
            filled += 1
    return filled


def _pick_property(candidates, anu, village_id, props):
    """candidates (properties.id) मधून एकच: गाव माहीत असेल तर त्याच गावाच्या; तरी अनेक असतील
    तर ज्यांचा अनुक्रमांक जुळतो त्या. एकच उरली तरच ती, नाहीतर None (अंदाज नाही)."""
    c = [pid for pid in candidates if pid in props]
    if village_id is not None:
        c = [pid for pid in c if props[pid][1] == village_id]
    if len(c) > 1:
        c = [pid for pid in c if props[pid][0] == anu]
    return c[0] if len(c) == 1 else None


def _backfill_transfer_property_refs(conn, tables):
    """property_transfer_logs / property_owner_history चा property_db_id (खरा properties.id).
    जुन्या रोंमध्ये फक्त अनुक्रमांक (property_id) आहे - तो दोन गावांत सारखा असू शकतो. म्हणून
    आधी मालकांवरून: नोंदीतले नवीन (सध्याचे) मालक ज्या मालमत्तेला जोडलेले आहेत ती; ते न जमल्यास
    अनुक्रमांक (+ माहीत असल्यास गाव) एकाच मालमत्तेचा असेल तर ती. संदिग्ध रो रिकामे ठेवतो."""
    import json
    filled = {}
    if not {"properties", "property_owner_association"} <= tables:
        return filled
    props = {pid: (anu, vid) for pid, anu, vid in conn.exec_driver_sql(
        "SELECT id, anuKramank, village_id FROM properties").fetchall()}
    by_owner = {}
    for pid, oid in conn.exec_driver_sql(
            "SELECT id, owner_id FROM property_owner_association").fetchall():
        by_owner.setdefault(oid, set()).add(pid)
    by_anu = {}
    for pid, (anu, _vid) in props.items():
        by_anu.setdefault(anu, []).append(pid)

    def resolve(anu, village_id, owner_ids):
        cands = set()
        for oid in owner_ids:
            cands |= by_owner.get(oid, set())
        pid = _pick_property(cands, anu, village_id, props)
        if pid is None:
            pid = _pick_property(by_anu.get(anu, []), anu, village_id, props)
        return pid

    if "property_transfer_logs" in tables and "property_db_id" in _columns(conn, "property_transfer_logs"):
        n = 0
        for row_id, anu, vid, new_json in conn.exec_driver_sql(
                "SELECT id, property_id, village_id, new_owners_json FROM property_transfer_logs "
                "WHERE property_db_id IS NULL").fetchall():
            try:
                owner_ids = [o.get("id") for o in json.loads(new_json or "[]") if o.get("id") is not None]
            except (ValueError, AttributeError):
                owner_ids = []
            pid = resolve(anu, vid, owner_ids)
            if pid is not None:
                conn.exec_driver_sql(
                    "UPDATE property_transfer_logs SET property_db_id = ?, village_id = COALESCE(village_id, ?) "
                    "WHERE id = ? AND property_db_id IS NULL", (pid, props[pid][1], row_id))
                n += 1
        if n:
            filled["property_transfer_logs.property_db_id"] = n

    if {"property_owner_history", "owner_history"} <= tables and \
            "property_db_id" in _columns(conn, "property_owner_history"):
        current = {}
        for poh_id, oid in conn.exec_driver_sql(
                "SELECT property_owner_history_id, owner_id FROM owner_history "
                "WHERE transferred_from_this_owner_date IS NULL").fetchall():
            current.setdefault(poh_id, []).append(oid)
        n = 0
        for row_id, anu, vid in conn.exec_driver_sql(
                "SELECT id, property_id, village_id FROM property_owner_history "
                "WHERE property_db_id IS NULL").fetchall():
            pid = resolve(anu, vid, current.get(row_id, []))
            if pid is not None:
                conn.exec_driver_sql(
                    "UPDATE property_owner_history SET property_db_id = ? WHERE id = ? AND property_db_id IS NULL",
                    (pid, row_id))
                n += 1
        if n:
            filled["property_owner_history.property_db_id"] = n
    return filled


def apply_new_column_defaults(engine=None):
    """सर्व रिकाम्या नवीन कॉलमना मूल्य. परत: {"टेबल.कॉलम": भरलेल्या रोंची संख्या} (फक्त >0)."""
    if engine is None:
        import database
        engine = database.engine
    filled = {}
    with engine.begin() as conn:
        tables = {row[0] for row in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "properties" in tables:
            n = _backfill_sort_order(conn)
            if n:
                filled["properties.sort_order"] = n
        filled.update(_backfill_transfer_property_refs(conn, tables))
        for table, column, value in NULL_DEFAULTS:
            if table not in tables or column not in _columns(conn, table):
                continue
            result = conn.exec_driver_sql(
                'UPDATE "%s" SET "%s" = ? WHERE "%s" IS NULL' % (table, column, column), (value,)
            )
            if result.rowcount:
                filled["%s.%s" % (table, column)] = result.rowcount
    return filled
