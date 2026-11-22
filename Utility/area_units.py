"""चौ.फु. <-> चौ.मी. रूपांतर - संपूर्ण सॉफ्टवेअरमध्ये (नमुना-8 नोंद/PUT/print/QR, खाली जागा,
नमुना-9 screen/sync/print, "सर्व कर पुन्हा मोजा") हाच एक आकडा व हाच राउंडिंग नियम वापरायचा.
फ्रंटएंडमध्ये हाच आकडा src/lib/areaUnits.ts मध्ये आहे - बदलला तर दोन्हीकडे बदला.

क्लायंट (Nov-2026): 1 चौ.मी. = 10.764 चौ.फु.; चौ.मी. क्षेत्रफळ 2 दशांश स्थळांपर्यंत
(1140 चौ.फु. / 10.764 = 105.9086 -> 105.91).
क्लायंट (22-Nov-2026): भांडवली मूल्य व कर मोजतानाही हाच 2 दशांशाचा चौ.मी. आकडा
(round(चौ.फु. ÷ 10.764, 2)) - area_sqm_for_tax. उदा. 252.85 चौ.फु. -> 23.49.
"""
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN  # noqa: F401  (ROUND_DOWN = कापणे, क्लायंट ठरवेल)

SQFT_PER_SQM = 10.764
SQM_DECIMALS = 2
# चौ.मी. राउंडिंग: ROUND_HALF_UP -> 105.91. कापायचं (105.90) ठरलं तर फक्त ही ओळ ROUND_DOWN करा.
SQM_ROUNDING = ROUND_HALF_UP


def round_sqm(value) -> float:
    """चौ.मी. क्षेत्रफळ 2 दशांश स्थळांपर्यंत (SQM_ROUNDING नियमाने)."""
    return float(Decimal(repr(float(value or 0))).quantize(Decimal(1).scaleb(-SQM_DECIMALS), rounding=SQM_ROUNDING))


def sqft_to_sqm(sqft) -> float:
    """चौ.फु. -> चौ.मी., 2 दशांश (round_sqm)."""
    return round_sqm((sqft or 0) / SQFT_PER_SQM)


def sqm_to_sqft(sqm) -> float:
    """चौ.मी. -> चौ.फु., 2 दशांश (साधारण round)."""
    return round((sqm or 0) * SQFT_PER_SQM, 2)


def to_sqft(value, unit) -> float:
    """value त्याच्या एककात (unit: 'sqm' किंवा इतर = चौ.फु.) -> चौ.फु. (गोल न करता)."""
    return (value or 0) * SQFT_PER_SQM if unit == 'sqm' else (value or 0)


def area_sqm_for_tax(value, unit) -> float:
    """भांडवली मूल्य / कर मोजण्यासाठी चौ.मी. क्षेत्रफळ = प्रिंटवर दिसणारा 2 दशांशाचा आकडा
    (क्लायंट 22-Nov-2026: छापलेलं क्षेत्रफळ x दर = छापलेलं भांडवली मूल्य; "Round Up All Area"
    चा यावर परिणाम नाही). unit 'sqm' -> round_sqm(value), नाहीतर चौ.फु. 2 दशांश करून
    sqft_to_sqm (round(चौ.फु. ÷ 10.764, 2)). उदा. 252.85 चौ.फु. -> 23.49."""
    v = float(value or 0)
    return round_sqm(v) if unit == 'sqm' else sqft_to_sqm(round_sqm(v))


def convert_area(value, from_unit, to_unit) -> float:
    """एका एककातून दुसऱ्यात (गोल न करता) - खाली जागेच्या वजाबाकीसाठी."""
    v = value or 0
    if from_unit == to_unit:
        return v
    return v * SQFT_PER_SQM if from_unit == 'sqm' else v / SQFT_PER_SQM
