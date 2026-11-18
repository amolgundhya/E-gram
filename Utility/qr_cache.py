"""मालमत्ता QR (/namuna8/property_qrcode) - जतन केलेली PNG थेट द्यायची की आधी तपासायची.

QR मजकूर (अ.क्र., मालमत्ता क्र., मालक, भोगवटदार, एकूण कर - Utility/qr_text.build_property_qr_text_short)
get_property_record() वरून बनतो. तो काढायला प्रत्येक QR ला ~25 ms लागतात; ९ क / लेख च्या viewer
मध्ये 916 बिलांचे QR म्हणजे दर वेळी 50-80 सेकंद. पण हा मजकूर फक्त डेटाबेस बदलला तरच बदलतो:
  - मालमत्ता / मालक / बांधकाम सेव्ह, Transfer, कर पुन्हा मोजा, Bulk Update, एकदाचे fixes,
  - अ.क्र. (sort_order - Serialize / Insert / जागा बदला / मालमत्ता delete - इतर मालमत्तांचाही),
  - Master दर / भारांक / checklist (एकूण कर लगेच बदलतो - कर साठवलेला नसून मोजला जातो),
  - Import (delete + insert),
किंवा तारीख बदलली (घसारा - चालू आकारणी वर्ष).

म्हणून प्रत्येक write-path मध्ये QR पुन्हा बनवायचा कोड न घालता (एखादा path राहून जुना QR
दिसण्याचा धोका) SQLite triggers वापरतो: खालच्या DENY यादीतली टेबलं सोडून (QR मजकुरावर ज्यांचा
परिणाम होत नाही - नमुना-9/7, दाखले, लॉग्ज...) प्रत्येक टेबलवर INSERT/UPDATE/DELETE झाला की
qr_cache_state.gen एकाने वाढतो. हे ORM, raw SQL, migration, दुसरी प्रोसेस (exe + main.py) - सगळ्यांना
लागू होतं, आणि त्याच transaction मध्ये.

property_qrcode: शेजारच्या qrcode.stamp मध्ये "gen|तारीख|PNG mtime|PNG size" - सगळं जुळलं तर
जतन केलेली PNG थेट (मधे काहीच बदललेलं नाही). न जुळल्यास पूर्वीसारखंच: मजकूर काढून तुलना,
वेगळा असेल तर PNG पुन्हा, आणि नवीन stamp. triggers नसले (उदा. टेबल पुन्हा बनवलं) तर stamp
कधीच जुळत नाही - म्हणजे पूर्वीसारखी प्रत्येक वेळी तपासणी.

नमुना-9 रकमा QR मजकुरात नाहीत (एकूण कर नमुना-8 हिशोबातून), म्हणून नमुना-9 टेबलं DENY मध्ये.
"""
import datetime
import logging
import os
import threading

from sqlalchemy import text

STATE_TABLE = "qr_cache_state"
TRIGGER_PREFIX = "qrgen_"

# QR मजकुरावर परिणाम न करणारी टेबलं - यांच्या बदलाने सगळे QR पुन्हा तपासायची गरज नाही.
# इथे नसलेलं प्रत्येक टेबल (नवीन टेबलसुद्धा) gen वाढवतं - शंका असेल तर तपासणी, जुना QR नाही.
DENY = {
    STATE_TABLE,
    "namuna7", "namuna9", "namuna9_property_association", "namuna9_property_data",
    "namuna9_receipts", "namuna9_settings", "namuna9_year_setups",
    "outward_entries", "gram_panchayat_staff", "license", "migration_flags",
    "owner_history", "property_owner_history", "property_transfer_logs", "property_documents",
}


def _denied(table):
    return table in DENY or table.endswith("_certificates") or table.startswith("sqlite_")


def _q(name):
    return '"' + name.replace('"', '""') + '"'


def ensure_qr_cache(engine=None):
    """सुरुवातीला व Import नंतर: state टेबल + प्रत्येक (DENY सोडून) टेबलवर 3 triggers; gen एकाने
    वाढवतो (बंद असताना दुसऱ्या प्रोग्रामने DB बदलला असेल तर). परत चालवलं तरी सुरक्षित."""
    if engine is None:
        from database import engine
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE TABLE IF NOT EXISTS %s (id INTEGER PRIMARY KEY, gen INTEGER NOT NULL DEFAULT 0, "
            "triggers INTEGER NOT NULL DEFAULT 0)" % STATE_TABLE)
        conn.exec_driver_sql("INSERT OR IGNORE INTO %s (id, gen, triggers) VALUES (1, 0, 0)" % STATE_TABLE)
        tables = [r[0] for r in conn.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        wanted = set()
        for t in tables:
            if _denied(t):
                continue
            for op, tag in (("INSERT", "ins"), ("UPDATE", "upd"), ("DELETE", "del")):
                name = "%s%s_%s" % (TRIGGER_PREFIX, t, tag)
                wanted.add(name)
                conn.exec_driver_sql(
                    "CREATE TRIGGER IF NOT EXISTS %s AFTER %s ON %s BEGIN "
                    "UPDATE %s SET gen = gen + 1 WHERE id = 1; END" % (_q(name), op, _q(t), STATE_TABLE))
        # DENY मध्ये नंतर टाकलेल्या टेबलचे जुने triggers काढतो
        for (name,) in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='trigger' AND substr(name, 1, %d) = '%s'"
                % (len(TRIGGER_PREFIX), TRIGGER_PREFIX)).fetchall():
            if name not in wanted:
                conn.exec_driver_sql("DROP TRIGGER IF EXISTS %s" % _q(name))
        conn.exec_driver_sql("UPDATE %s SET gen = gen + 1, triggers = %d WHERE id = 1" % (STATE_TABLE, len(wanted)))
    return len(wanted)


def current_token(db):
    """आत्ताचा cache token ("gen|YYYY-MM-DD") किंवा None (state/triggers नाहीत - तपासणी करा).
    मजकूर काढायच्या आधी वाचायचा: मधे कोणी लिहिलं तर gen बदलतो आणि पुढच्या वेळी पुन्हा तपासणी."""
    try:
        row = db.execute(text(
            "SELECT s.gen, s.triggers, (SELECT count(*) FROM sqlite_master WHERE type='trigger' "
            "AND substr(name, 1, :n) = :p) FROM %s s WHERE s.id = 1" % STATE_TABLE),
            {"n": len(TRIGGER_PREFIX), "p": TRIGGER_PREFIX}).fetchone()
    except Exception:
        return None
    if not row or not row[1] or row[1] != row[2]:
        return None
    return "%s|%s" % (row[0], datetime.date.today().isoformat())


def _png_sig(png_path):
    st = os.stat(png_path)
    return "%d|%d" % (st.st_mtime_ns, st.st_size)


def stamp_path(png_path):
    return os.path.join(os.path.dirname(png_path), "qrcode.stamp")


def is_fresh(png_path, token):
    """token जुळला आणि PNG आपण तपासल्यापासून दुसऱ्या कोणी (उदा. सेव्ह/Transfer) बदललेली नाही."""
    if not token:
        return False
    try:
        with open(stamp_path(png_path), encoding="utf-8") as f:
            saved = f.read()
        return saved == token + "|" + _png_sig(png_path)
    except OSError:
        return False


def write_stamp(png_path, token):
    if not token:
        return
    try:
        path = stamp_path(png_path)
        tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(token + "|" + _png_sig(png_path))
        os.replace(tmp, path)
    except OSError:
        logging.exception("QR stamp could not be written: %s", png_path)
