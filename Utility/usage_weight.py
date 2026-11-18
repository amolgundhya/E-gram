# बांधकाम रो चा भारांक (वापर: निवासी / औद्योगिक / वाणिज्यिक) - building_usage_weightage
# मास्टरमधल्या नावावरून. नमुना-8 ड्रॉपडाउन आधी "वाणिज्य" साठवायचा, तर मास्टरमध्ये नाव
# "वाणिज्यिक" आहे - नाव जुळत नसल्याने भारांक 1 धरला जायचा (कर गुणाकार होत नव्हता).
# क्रम: नेमकं नाव -> (मोकळ्या जागा काढून) जुनं/चुकीचं नाव (USAGE_ALIASES) -> 1.
# कर (construction_tax.py) व नमुना-8 प्रिंटचा रकाना 14 (property_record_response.py) हेच वापरतात.

USAGE_ALIASES = {
    "वाणिज्य": "वाणिज्यिक",
    "औधोगिक": "औद्योगिक",
}


def canonical_usage(bharank):
    """साठवलेल्या वापराचं मास्टरमधलं नाव (alias असेल तर), नाहीतर तेच (strip केलेलं)."""
    if bharank is None:
        return None
    name = str(bharank).strip()
    return USAGE_ALIASES.get(name, name)


def usage_weight(weightage_map, bharank, default=1):
    """weightage_map: {building_usage: weightage}. नाव मास्टरमध्ये नसेल तर default (1)."""
    if not weightage_map or bharank is None:
        return default
    if bharank in weightage_map:
        return weightage_map[bharank]
    name = str(bharank).strip()
    if name in weightage_map:
        return weightage_map[name]
    alias = USAGE_ALIASES.get(name)
    if alias is not None and alias in weightage_map:
        return weightage_map[alias]
    return default
