# नमुना-9 "मालमत्ता धारकांच्या नावानुसार" क्रमवारी - प्रिंट (namuna9Print.py) आणि
# स्क्रीनवरची यादी (/namuna9/table-data?sortByName=true) दोन्ही हीच key वापरतात,
# जेणेकरून स्क्रीन आणि प्रिंट मधला क्रम नेहमी सारखाच राहील.
#
# साध्या Unicode क्रमाने चालत नाही: तिथे ळ हा ल-व च्या मध्ये येतो (मराठीत ह नंतर),
# क्ष/ज्ञ स्वतंत्र अक्षरं म्हणून शेवटी येत नाहीत, आणि ं/ः हे ा च्याही आधी येतात.
# म्हणून बाराखडी प्रमाणे स्पष्ट क्रम:
#   स्वर: अ आ इ ई उ ऊ ऋ ए ऐ ओ औ अं अः
#   व्यंजन: क ख ग घ ङ च छ ज झ ञ ट ठ ड ढ ण त थ द ध न प फ ब भ म य र ल व श ष स ह ळ क्ष ज्ञ
#   प्रत्येक व्यंजनानंतर: क < का < कि < की < कु < कू < कृ < के < कै < को < कौ < कं < कः
#   आणि त्यानंतर जोडाक्षरे (क्क, क्र ...).
# इंग्रजी अक्षराने सुरू होणारी नावे मराठी नावांनंतर, आणि रिकामी नावे सर्वात शेवटी.

import re

_VOWELS = ['अ', 'आ', 'इ', 'ई', 'उ', 'ऊ', 'ऋ', 'ए', 'ऐ', 'ओ', 'औ', 'अं', 'अः']
_CONSONANTS = ['क', 'ख', 'ग', 'घ', 'ङ', 'च', 'छ', 'ज', 'झ', 'ञ', 'ट', 'ठ', 'ड', 'ढ', 'ण',
               'त', 'थ', 'द', 'ध', 'न', 'प', 'फ', 'ब', 'भ', 'म', 'य', 'र', 'ल', 'व',
               'श', 'ष', 'स', 'ह', 'ळ', 'क्ष', 'ज्ञ']

# व्यंजनानंतरची "स्वर-जागा": काहीच चिन्ह नसेल (अंगभूत अ) तर सर्वात लहान, ्
# (जोडाक्षर) सर्वात मोठं.
_INHERENT_A = 10
_VOWEL_SLOT = {s: 11 + i for i, s in enumerate(
    ['ा', 'ि', 'ी', 'ु', 'ू', 'ृ', 'े', 'ै', 'ो', 'ौ', 'ं', 'ः', '्'])}
_VOWEL_SLOT.update({'ॅ': _VOWEL_SLOT['े'], 'ॉ': _VOWEL_SLOT['ो'], 'ँ': _VOWEL_SLOT['ं']})
_MODIFIERS = {'ं', 'ः', 'ँ'}
# "कां" सारखं - मात्रेनंतर आलेला अनुस्वार: "का" नंतर, पण "काक" च्या आधी.
_MODIFIER_AFTER_SIGN = 5

_LETTER = {v: 100 + i for i, v in enumerate(_VOWELS)}
_LETTER.update({c: 200 + i for i, c in enumerate(_CONSONANTS)})
_LETTER.update({'ऍ': _LETTER['ए'], 'ऑ': _LETTER['ओ'], 'ऱ': _LETTER['र']})
_INDEPENDENT_VOWELS = set(_VOWELS[:11]) | {'ऍ', 'ऑ'}

_LIST_NUMBER_PREFIX = re.compile(r'^[0-9०-९]+\s*[).:\-]\s*')

_SPACE = 1
_DEVANAGARI_DIGITS = '०१२३४५६७८९'
_NUKTA = '़'


def _devanagari_weights(text):
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == _NUKTA:
            i += 1
            continue
        # क्ष / ज्ञ - एकच अक्षर
        tri = text[i:i + 3]
        if tri in ('क्ष', 'ज्ञ'):
            ch, i = tri, i + 3
        else:
            i += 1
        if ch in _CONSONANTS or ch == 'ऱ':
            out.append(_LETTER[ch])
            while i < n and text[i] == _NUKTA:
                i += 1
            nxt = text[i] if i < n else ''
            if nxt in _VOWEL_SLOT:
                out.append(_VOWEL_SLOT[nxt])
                i += 1
                if nxt not in _MODIFIERS and nxt != '्' and i < n and text[i] in _MODIFIERS:
                    out.append(_MODIFIER_AFTER_SIGN)
                    i += 1
            else:
                out.append(_INHERENT_A)
        elif ch in _INDEPENDENT_VOWELS:
            nxt = text[i] if i < n else ''
            if ch == 'अ' and nxt in ('ं', 'ँ'):
                out.append(_LETTER['अं'])
                i += 1
            elif ch == 'अ' and nxt == 'ः':
                out.append(_LETTER['अः'])
                i += 1
            else:
                out.append(_LETTER[ch])
                if nxt in _MODIFIERS:
                    out.append(_MODIFIER_AFTER_SIGN)
                    i += 1
        elif ch.isspace():
            if out and out[-1] != _SPACE:
                out.append(_SPACE)
        elif ch in _DEVANAGARI_DIGITS:
            out.append(50 + _DEVANAGARI_DIGITS.index(ch))
        elif '0' <= ch <= '9':
            out.append(50 + int(ch))
        elif ch.isascii() and ch.isalpha():
            out.append(1000 + ord(ch.lower()))
        # बाकी विरामचिन्हं (. , - इ.) क्रमवारीत दुर्लक्षित
    return tuple(out)


def marathi_name_key(name):
    """मालमत्ता धारकाच्या नावाची sort key: (गट, वजनं). गट 0 = मराठी अक्षराने सुरू,
    1 = इंग्रजी अक्षराने सुरू, 2 = रिकामं/इतर."""
    # अनेक मालक असलेली नावं "1) भाटु जाधव 2) अरूण जाधव" अशी साठवलेली असतात - सुरुवातीचा
    # "1)" धरला तर ती सगळी यादीच्या सुरुवातीला जातात, म्हणून तो क्रमवारीपुरता काढतो.
    # ZWJ/ZWNJ (चव्‍हाण, "1‍)") दिसत नाहीत पण regex/क्रमात अडथळा आणतात.
    text = (name or '').replace('‍', '').replace('‌', '').strip()
    text = _LIST_NUMBER_PREFIX.sub('', text)
    first = next((c for c in text if c.isalpha() or 'ऀ' <= c <= 'ॿ'), '')
    if 'ऀ' <= first <= 'ॿ':
        return (0, _devanagari_weights(text))
    if first.isascii() and first.isalpha():
        return (1, _devanagari_weights(text))
    return (2, _devanagari_weights(text))


def sort_rows_by_owner_name(rows, field='ownerName'):
    """rows नावानुसार लावतो. sorted() stable आहे, त्यामुळे सारखी नावं असतील तर
    त्यांचा आधीचा (अ.क्र.) क्रम तसाच राहतो."""
    return sorted(rows, key=lambda r: marathi_name_key((r or {}).get(field)))


def is_true(value):
    return value in (True, 'true', 'True', '1', 1)
