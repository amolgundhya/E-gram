"""नमुना-10 वसुली हिशोबातल्या रकमा एकसारख्या दाखवण्यासाठी (फक्त दाखवणे).

DB मध्ये रकमा Float - Jinja थेट "30.0" छापतो, तर रिकाम्या रकमेसाठी template "0" छापतो,
त्यामुळे एकाच तक्त्यात "30.0" व "0" मिसळलेले दिसायचे. आता पूर्ण रुपया असेल तर "30" / "0",
पैसे असतील तर नेहमी 2 दशांश ("30.50"). Jinja मध्ये: {{ value|amt }}
"""


def format_amount_display(value) -> str:
    try:
        v = round(float(value or 0), 2)
    except (TypeError, ValueError):
        return str(value) if value is not None else ""
    if v == 0:
        return "0"
    if v == int(v):
        return str(int(v))
    return "%.2f" % v
