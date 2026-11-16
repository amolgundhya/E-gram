"""भोगवटदार रिकामा असेल तर "स्वतः" (मालकच राहतो) - नोंद/Update/Bulk जतन करताना आणि
सर्व नमुना-8 रेकॉर्ड्स (प्रिंट, यादी, नमुना-9) मध्ये हाच एक नियम."""

SELF_OCCUPANT = "स्वतः"


def occupant_or_self(value) -> str:
    text = str(value).strip() if value is not None else ""
    return text or SELF_OCCUPANT
