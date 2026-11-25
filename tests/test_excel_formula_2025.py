# क्लायंटचा Excel "New Software Formula 2025" (Sheet1) - नमुना-8 भांडवली मूल्य व कर तंतोतंत.
#   भांडवली मूल्य = (क्षेत्रफळ x जमीन दर) + (क्षेत्रफळ x बांधकाम दर x घसारा x भारांक)
#   खुली जागा     = क्षेत्रफळ x जमीन दर
#   कर            = भांडवली मूल्य x कराचा दर / 1000 (साठवताना round_tax_amount: पूर्ण रुपया, half-up)
# DB ला हात लावत नाही: घसारा दर / ConstructionType lookup patch केलेले.
# चालवा: python -m unittest tests.test_excel_formula_2025 -v   (E-gram मधून)
import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from namuna8.calculations import construction_tax, naumuna8_calculations  # noqa: E402
from namuna8.calculations.khali_jaga import khali_jaga  # noqa: E402
from Utility.tax_rounding import round_half_up  # noqa: E402

WEIGHTS = {"निवासी": 1, "वाणिज्यिक": 1.25, "औद्योगिक": 1.5}

# (नाव, क्षेत्रफळ चौ.मी., जमीन दर, बांधकाम दर, घसारा, कराचा दर, Excel भां.मू., Excel कर)
EXCEL_ROWS = [
    ("आरसीसी पद्धतीची इमारत", 140, 800, 15400, 0.80, 1.2, 1836800, 2204.16),
    ("दगड विटांची व चुना किंवा सिमेंट वापरून उभारलेली इमारत", 74, 610, 13860, 0.95, 0.75, 1019498, 764.62),
    ("दगड किंवा विटा वापरलेली मातीची इमारत", 45, 350, 9240, 0.75, 0.6, 327600, 196.56),
    ("झोपडी किंवा मातीची इमारत", 15, 175, 6930, 0.30, 0.3, 33810, 10.14),
    ("टिन शेड", 15, 175, 6930, 0.45, 0.3, 49402.5, 14.82),
]


def ctype(name, land, build, rate):
    return SimpleNamespace(name=name, annualLandValueRate=land, bandhmastache_dar=build, rate=rate)


def compute(ct, area, depreciation, usage="निवासी"):
    # घसारा दर फंक्शन टक्क्यांत परत करतं (80 = 0.8)
    with mock.patch.object(construction_tax, "calculate_depreciation_rate",
                           return_value=round(depreciation * 100, 6)):
        return construction_tax.compute_construction_values(
            db=None, construction_type=ct, length=area, width=1, construction_year=2000,
            bharank=usage, construction_unit="sqm", assessment_year=2026, formula1=True,
            weightage_map=WEIGHTS, gram_panchayat_id=None)


class ExcelFormula2025(unittest.TestCase):
    def test_building_rows_match_excel(self):
        for name, area, land, build, dep, rate, exp_cv, exp_tax in EXCEL_ROWS:
            with self.subTest(name=name):
                cv, tax = compute(ctype(name, land, build, rate), area, dep)
                self.assertEqual(cv, exp_cv)
                self.assertEqual(round(cv * rate / 1000, 2), exp_tax)   # Excel कर (2 दशांश)
                self.assertEqual(tax, round_half_up(exp_tax))           # साठवलेला कर (पूर्ण रुपया)

    def test_khuli_jaga_row(self):
        # बांधकाम तक्त्यातली "खाली जागा" रो (बांधकाम दर 0) व प्रॉपर्टीची खाली जागा - दोन्ही A x जमीन दर
        ct = ctype("खाली जागा", 800, 0, 1.5)
        cv, tax = compute(ct, 140, 1.0)
        self.assertEqual((cv, round(cv * 1.5 / 1000, 2), tax), (112000, 168, 168))
        prop = SimpleNamespace(areaUnit="sqm", constructionAreaUnit="sqm", totalArea=140, totalAreaSqFt=0)
        k = khali_jaga(prop, [], ct, round_half_up)
        self.assertEqual((k["capital_value"], k["house_tax"]), (112000, 168))

    def test_vanijyik_bharank_on_building_only(self):
        cv, tax = compute(ctype("आरसीसी पद्धतीची इमारत", 1480, 15246, 1.2), 37.16, 1.0, "वाणिज्यिक")
        # 37.16x1480 + 37.16x15246x1.0x1.25 = 54996.8 + 708176.7
        self.assertEqual(cv, 763173.5)
        self.assertEqual(round(cv), 763174)      # Excel मधला (पूर्णांक) आकडा
        self.assertEqual(round(cv * 1.2 / 1000, 2), 915.81)
        self.assertEqual(tax, 916)
        # जुन्या (संपूर्ण बेरजेला भारांक) सूत्राने 953966.88 / 1145 आलं असतं
        self.assertNotEqual(cv, round((54996.8 + 566541.36) * 1.25, 2))

    def test_tin_shed_type2_age35(self):
        fake_db = mock.MagicMock()
        fake_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(gharache_prakar=2)
        with mock.patch.object(naumuna8_calculations, "SessionLocal", return_value=fake_db):
            pct = naumuna8_calculations.calculate_depreciation_rate(1991, "टिन शेड", 2026)
            self.assertEqual(pct, 45)
            fake_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(gharache_prakar=1)
            self.assertEqual(naumuna8_calculations.calculate_depreciation_rate(1991, "टिन शेड", 2026), 60)
        # पूर्ण साखळी: 35 वर्षांचा टिन शेड, प्रकार 2 -> Excel 49402.5 / 14.82
        fake_db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(gharache_prakar=2)
        with mock.patch.object(naumuna8_calculations, "SessionLocal", return_value=fake_db):
            cv, tax = construction_tax.compute_construction_values(
                None, ctype("टिन शेड", 175, 6930, 0.3), 15, 1, 1991, "निवासी", "sqm", 2026, True, WEIGHTS, None)
        self.assertEqual((cv, round(cv * 0.3 / 1000, 2), tax), (49402.5, 14.82, 15))


if __name__ == "__main__":
    unittest.main()
