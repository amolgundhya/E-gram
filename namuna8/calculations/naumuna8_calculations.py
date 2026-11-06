# घसारा दर (Depreciation rate) - महाराष्ट्र शासन राजपत्र दि. 31-12-2015 नुसार.
# gharache_prakar = 1 : राजपत्रातील रकाना 3 (दगड/विटा + चुना/सिमेंट, आर.सी.सी.)
# gharache_prakar = 2 : राजपत्रातील रकाना 2 (झोपडी, मातीची, दगड/विटा मातीची)
# शेवटचा गट (61+ वर्षं) खुला ठेवलाय (end=None) - इमारत कितीही जुनी असो, घसारा दर
# त्याखाली (30% / 15% च्या खाली) कधीच जात नाही.
type1 = {
    (0, 2): 100,
    (3, 5): 95,
    (6, 10): 90,
    (11, 20): 80,
    (21, 30): 70,
    (31, 40): 60,
    (41, 50): 50,
    (51, 60): 40,
    (61, None): 30,
}

type2 = {
    (0, 2): 100,
    (3, 5): 95,
    (6, 10): 85,
    (11, 20): 75,
    (21, 30): 60,
    (31, 40): 45,
    (41, 50): 30,
    (51, 60): 20,
    (61, None): 15,
}

from datetime import datetime
from sqlalchemy.orm import Session
from namuna8.namuna8_model import ConstructionType
from database import SessionLocal  # adjust import path


def get_assessment_year(gram_panchayat) -> int:
    """चालू कर-आकारणी चक्राचं सुरुवातीचं वर्ष (उदा. GramPanchayat.from_yearslap =
    '2026-2027' => 2026). from_yearslap ग्रामपंचायत तयार करतानाच एकदा ठरतं आणि चक्र
    संपेपर्यंत (साधारण 4 वर्षं) बदलत नाही - घसारा दर याच स्थिर वर्षावरून मोजायचा,
    आजच्या तारखेवरून (datetime.now()) नाही. नाहीतर एकाच आकारणी चक्रात मधेच
    मालमत्ता संपादित केली की घसारा दर (आणि त्यामुळे कर) आपोआप बदलून जाईल.
    gram_panchayat नसेल किंवा from_yearslap रिकामं/अवैध असेल तर आहे तसं
    (datetime.now().year) वापरतो."""
    raw = getattr(gram_panchayat, 'from_yearslap', None) if gram_panchayat is not None else None
    if raw:
        try:
            return int(str(raw).split('-')[0].strip())
        except (ValueError, IndexError):
            pass
    return datetime.now().year


# बांध. वर्ष युजर कॅलेंडरमधून निवडू शकतो किंवा हाताने टाईप करू शकतो - त्यामुळे साधं वर्ष
# ("2015") नसून पूर्ण तारीख ("12/06/2015", "2015-06-12", "12-06-2015") साठवलेली असू शकते.
# साधं वर्ष आधीसारखंच int() ने वाचतो; ते न जमल्यास तारखेतून फक्त वर्ष काढतो. काहीच ओळखता
# न आल्यास None (=> घसारा 0, आधीसारखंच).
_CONSTRUCTION_DATE_FORMATS = ('%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y', '%Y-%m-%d', '%Y/%m/%d')


def parse_construction_year(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    if value is None:
        return None
    s = str(value).strip()[:10]
    for fmt in _CONSTRUCTION_DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).year
        except ValueError:
            continue
    return None


def calculate_depreciation_rate(year: int, name: str, assessment_year: int = None):
    """year: बांधकामाचे वर्ष (construction year). assessment_year: चालू आकारणी
    चक्राचं सुरुवातीचं वर्ष (get_assessment_year() ने काढलेलं) - दिलं नाही तर
    आधीसारखंच datetime.now().year वापरतो (जुने कॉलर्स / खाली-जागेसाठीचा
    "वय नेहमी 0" हा वापर यामुळे मोडत नाही)."""
    reference_year = assessment_year if assessment_year is not None else datetime.now().year

    year = parse_construction_year(year)
    if year is None:
        return 0

    # अवास्तव/अशक्य बांधकाम वर्ष (रिकामं वर आधीच return झालंय; इथे उदा. वर्ष चुकून
    # 3-अंकी टाईप झालेलं '206', किंवा आकारणी वर्षानंतरचं भविष्यातलं वर्ष) - आधीच्या
    # (bug असलेल्या पण) वर्तनाप्रमाणेच 0 देतो, नवीन गॅझेट कोष्टक लावत नाही - अशा मालमत्ता
    # वेगळ्या यादीत दाखवून युजरला कळवायच्या, आपोआप चुकीचा घसारा दर लावायचा नाही.
    if year < 1850 or year > reference_year:
        return 0

    year_diff = reference_year - year

    db: Session = SessionLocal()
    try:
        # Fetch construction type by name
        construction = db.query(ConstructionType).filter(ConstructionType.name == name).first()
        if not construction:
            return 0   # if no match, return 0

        if construction.gharache_prakar == 1:
            depreciation_map = type1
        elif construction.gharache_prakar == 2:
            depreciation_map = type2
        else:
            return 0   # if घसारा प्रकार = 0 or invalid

        # Match year_diff with depreciation map
        for (start, end), value in depreciation_map.items():
            if end is None:
                if year_diff >= start:
                    return value
            elif start <= year_diff <= end:
                return value

        return 0
    finally:
        db.close()
