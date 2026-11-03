# नमुना-9 गोषवारा रिपोर्ट्सचे पान-विभाजन (pages) - ओळींच्या अंदाजे उंचीनुसार.
#
# आधी प्रत्येक पानावर ठराविक 6 ओळी (गुंज साठी 363 पानं) - कारण प्रत्येक पानावर पूर्ण
# मथळा (report-top) repeat होत होता आणि सर्वात लांब नावं धरून आकडा ठरवला होता. आता
# मथळा फक्त पहिल्या पानावर, बाकी पानांवर फक्त कॉलम हेडर + "या पानाची बेरीज", आणि
# प्रत्येक ओळीची उंची तिच्या मजकुरावरून (नाव/भोगवटदार/मिळकत नंबर किती ओळींत मोडेल)
# अंदाजे काढून पान भरतो - साधी नावं असतील तर ~18-25 ओळी, लांब नावं जास्त जागा घेतात.
#
# प्रत्येक टेम्प्लेटचा वेगळा profile (_PROFILES): पानाची छापील उंची, हेडर/गोषवारा/मथळा
# उंची, एका ओळीची उंची, वाढीव ओळीची उंची आणि प्रत्येक कॉलममध्ये एका ओळीत किती
# "अक्षरं" मावतात. हे आकडे headless Chrome मध्ये प्रत्यक्ष प्रिंट-लेआउट मोजून (गुंज,
# 2176 ओळी, सर्व 17 टेम्प्लेट्स) काढले आहेत, आणि सर्व px "छापील" आहेत - म्हणजे पोर्ट्रेट
# A4 वर रुंद टेबल Chrome जितकं लहान (shrink-to-fit) करून छापतो ते धरून, आणि एखादं
# पान एकटं छापलं तरी (From/To) मावेल अशा सर्वात वाईट scale ने.
# SAFETY: अंदाज चुकला तरी एकही पान दुसऱ्या शीटवर जाऊ नये म्हणून पानाची फक्त
# एवढीच उंची वापरतो. ज्या टेम्प्लेट्समध्ये (Vasuli) टेबलचे कॉलम प्रत्येक पानावरच्या
# मजकुरानुसार रुंद/अरुंद होतात (table-layout auto + रिकामे पावती कॉलम) तिथे नावाची
# ओळ-संख्या पाना-पानाला बदलते - त्यांचा profile मध्ये स्वतःचा कमी 'safety' आहे,
# सर्वात भरलेलं पान एकटं छापलं तरी ~93% पेक्षा जास्त भरू नये इतका.
# Chrome रुंद टेबल जास्तीत जास्त 2/3 पर्यंतच लहान करतो (त्यापेक्षा रुंद असेल तर
# उजवीकडचे कॉलम कापले जातात) - profiles मधल्या उंच्या तेच धरून आहेत.
import re

SAFETY = 0.90

# अक्षराची अंदाजे रुंदी (एका सामान्य मराठी अक्षराच्या प्रमाणात). मात्रा/अनुस्वार
# वर-खाली येतात (0), ा ि ी ो ौ बाजूला थोडी जागा घेतात, ् ने जोडाक्षर होऊन आधीचं
# अक्षर अर्धं होतं.
_ZERO = set('\u0901\u0902\u093c\u0941\u0942\u0943\u0944\u0945\u0947\u0948\u0962\u0963\u200c\u200d')
_HALF = set('\u093e\u093f\u0940\u0949\u094a\u094b\u094c\u0903')
_VIRAMA = '\u094d'
_SPACE_W = 0.4


def _word_width(word):
    w = 0.0
    for ch in word:
        if ch in _ZERO:
            continue
        if ch == _VIRAMA:
            w -= 0.5
        elif ch in _HALF:
            w += 0.5
        elif ch.isascii():
            w += 0.6 if ch in '.,;:()/-\'"' else 0.75
        else:
            w += 1.0
    return max(w, 0.0)


def wrap_lines(text, cpl):
    """text एका ओळीत cpl "अक्षरं" मावणाऱ्या कॉलममध्ये किती ओळींत मोडेल (greedy
    word wrap; एकच शब्द ओळीपेक्षा मोठा असेल तर तोही तोडला जातो)."""
    text = (text or '').strip()
    if not text:
        return 1
    lines, cur = 1, 0.0
    for word in re.split(r'\s+', text):
        w = _word_width(word)
        if cur == 0.0:
            cur = w
        elif cur + _SPACE_W + w <= cpl:
            cur += _SPACE_W + w
        else:
            lines += 1
            cur = w
        while cur > cpl:
            lines += 1
            cur -= cpl
    return lines


def estimate_lines(property_number, owner_name, occupant, cpl):
    return max(wrap_lines(property_number, cpl['prop']),
               wrap_lines(owner_name, cpl['name']),
               wrap_lines(occupant, cpl['occ']))


def _longest_word(text):
    return max((_word_width(w) for w in re.split(r'\s+', (text or '').strip()) if w), default=0.0)


_PROFILES = {
    'namuna9All.html': dict(page_h=733, top=141, thead=83, tfoot=40, grand=40,
        line1=23.0, extra=20.0, cpl=dict(prop=6, name=17, occ=5), safety=0.881),
    # लँडस्केप A4 (L. Page)
    'namuna9Gen.html': dict(page_h=717, top=157, thead=82, tfoot=51, grand=51,
        line1=25.9, extra=24.6, cpl=dict(prop=6, name=22, occ=13)),
    'namuna9Pani.html': dict(page_h=1046, top=149, thead=78, tfoot=49, grand=26,
        line1=26.0, extra=23.0, cpl=dict(prop=8, name=22, occ=10)),
    'namuna9Vasuli1.html': dict(page_h=717, top=123, thead=67, tfoot=37, grand=37,
        line1=17.9, extra=15.9, cpl=dict(prop=4, name=8, occ=4), min_content=True),
    'namuna9Vasuli2.html': dict(page_h=717, top=144, thead=78, tfoot=43, grand=43,
        line1=21.0, extra=18.7, cpl=dict(prop=6, name=8, occ=4), safety=0.872, min_content=True),
    # नाव कॉलम रुंद + ओळी घट्ट केल्यानंतर headless Chrome मध्ये पुन्हा मोजलेलं (साधी नावं:
    # पहिल्या पानावर ~20, पुढच्या पानांवर ~27 ओळी).
    'namuna9Vasuli3.html': dict(page_h=717, top=149, thead=80, tfoot=22, grand=22,
        line1=20.6, extra=17.6, cpl=dict(prop=5, name=25, occ=11), safety=0.92),
    # सूट सह All/Gen लँडस्केप A4 (L. Page) - headless Chrome मध्ये 1047px छापील रुंदीवर
    # मोजलेलं (All चा टेबल 1178px -> 0.889 ने लहान, Gen 1068px -> 0.98). name=18 वर
    # All चं एक पान दुसऱ्या शीटवर जातं, 17 पर्यंत नाही - सुरक्षिततेसाठी 16.
    'namuna9AllSutSaha.html': dict(page_h=717, top=132.5, thead=69.4, tfoot=46.3, grand=46.3,
        line1=23.2, extra=20.5, cpl=dict(prop=5, name=16, occ=10)),
    'namuna9GenSutSaha.html': dict(page_h=717, top=146.1, thead=76.5, tfoot=51.0, grand=51.0,
        line1=25.5, extra=22.6, cpl=dict(prop=5, name=16, occ=10)),
    # विशेष पाणी All/Gen/Pani लँडस्केप A4 (L. Page) - headless Chrome मध्ये 1047px छापील
    # रुंदीवर मोजलेलं (All चा टेबल 1157px -> 0.905, Gen/Pani 994px -> 1.0). cpl: All
    # name=20 / Gen name=24 वर पानं दुसऱ्या शीटवर जातात - त्याखाली सुरक्षित आकडे.
    'namuna9AllVisheshPain.html': dict(page_h=717, top=134.8, thead=70.6, tfoot=47.1, grand=47.1,
        line1=23.5, extra=20.8, cpl=dict(prop=5, name=16, occ=10)),
    'namuna9GenVisheshPain.html': dict(page_h=717, top=149, thead=78, tfoot=26, grand=49,
        line1=26.0, extra=23.0, cpl=dict(prop=6, name=20, occ=12)),
    'namuna9PaniVisheshPain.html': dict(page_h=717, top=149, thead=78, tfoot=26, grand=49,
        line1=26.0, extra=23.0, cpl=dict(prop=6, name=26, occ=14)),
    # विशेष पाणी Vasuli1 लँडस्केप A4 (L. Page) + मिळकत नंबर कॉलम - 1047px छापील रुंदीवर
    # मोजलेलं (टेबल 1236px -> 0.847). सर्वात लहान ओळही 2 ओळींची (49px) म्हणून line1 =
    # 2 ओळींची उंची. min_content ऐवजी ठराविक cpl - name=24 वर पान दुसऱ्या शीटवर जातं, 20
    # पर्यंत नाही; 18 सुरक्षित (लांब नावांसह आणि फक्त प्रत्यक्ष डेटासह दोन्ही तपासलं).
    'namuna9Vasuli1VisheshPain.html': dict(page_h=717, top=126.3, thead=80.5, tfoot=44.1, grand=44.1,
        line1=41.6, extra=19.5, cpl=dict(prop=6, name=18, occ=9)),
    # विशेष पाणी Vasuli2 लँडस्केप A4 (L. Page) + मिळकत नंबर कॉलम - 1047px छापील रुंदीवर
    # मोजलेलं (टेबल 994px, लहान करावं लागत नाही). फक्त प्रत्यक्ष (लहान) नावांच्या पानांवर
    # नाव-कॉलम अरुंद होतो - name=20 वर तसं पान दुसऱ्या शीटवर गेलं, 16 पर्यंत नाही; 14 सुरक्षित.
    'namuna9Vasuli2VisheshPain.html': dict(page_h=717, top=149, thead=95, tfoot=52, grand=52,
        line1=26.0, extra=23.0, cpl=dict(prop=6, name=14, occ=7)),
    # विशेष पाणी (सफाई कर सह) All/Gen लँडस्केप A4 (L. Page) - 1047px छापील रुंदीवर मोजलेलं
    # (All चा टेबल 1267px -> 0.826, Gen 1046px -> 1.0). दोन्हींत name=20 वर पानं दुसऱ्या
    # शीटवर जातात; 14 सुरक्षित (लांब नावांसह आणि फक्त प्रत्यक्ष डेटासह दोन्ही तपासलं).
    'namuna9AllVisheshPaniSafai.html': dict(page_h=717, top=123.1, thead=64.5, tfoot=43.0, grand=43.0,
        line1=21.5, extra=19.0, cpl=dict(prop=5, name=14, occ=9)),
    'namuna9GenVisheshPaniSafai.html': dict(page_h=717, top=149, thead=78, tfoot=26, grand=49,
        line1=26.0, extra=23.0, cpl=dict(prop=5, name=14, occ=9)),
    # विशेष पाणी (सफाई सह) Vasuli1 लँडस्केप A4 (L. Page) + मिळकत नंबर कॉलम - 1047px छापील
    # रुंदीवर मोजलेलं (टेबल 1337px -> 0.783; सर्वात लहान ओळही 2 ओळींची). name=20/24 वर
    # सर्वात भरलेलं पान 91-94% - खूप घट्ट; 16 वर 84% (लांब नावांसह आणि प्रत्यक्ष डेटासह तपासलं).
    'namuna9Vasuli1VisheshPaniSafai.html': dict(page_h=717, top=116.7, thead=74.4, tfoot=40.8, grand=40.8,
        line1=38.4, extra=18.0, cpl=dict(prop=6, name=16, occ=8)),
    # विशेष पाणी (सफाई सह) Vasuli2 लँडस्केप A4 (L. Page) + मिळकत नंबर कॉलम - 1047px छापील
    # रुंदीवर मोजलेलं (टेबल 1075px -> 0.974; सर्वात लहान ओळही 2 ओळींची). name=24 वर पान
    # दुसऱ्या शीटवर जातं, 20 वर 95% भरतं; 16 वर 83% (लांब नावांसह व प्रत्यक्ष डेटासह तपासलं).
    'namuna9Vasuli2VisheshPaniSafai.html': dict(page_h=717, top=145.1, thead=92.5, tfoot=50.6, grand=50.6,
        line1=47.7, extra=22.4, cpl=dict(prop=6, name=16, occ=8)),
}


def _row_height(row, p, cpl=None):
    lines = estimate_lines(row.get('propertyNumber'), row.get('ownerName'), row.get('occupant'), cpl or p['cpl'])
    return p['line1'] + (lines - 1) * p['extra']


def _page_height(rows, p):
    """पानावरच्या ओळींची एकूण अंदाजे उंची. 'min_content' profile (Vasuli): टेबल पानापेक्षा
    रुंद असल्याने Chrome नाव/भोगवटदार कॉलम त्या पानावरच्या सर्वात लांब शब्दाइतकाच रुंद
    करतो - पानावर सगळी नावं लहान शब्दांची असतील तर कॉलम अरुंद होऊन प्रत्येक नाव जास्त
    ओळींत मोडतं. म्हणून कॉलमची रुंदी (cpl) त्या पानावरच्या सर्वात लांब शब्दापुरती मर्यादित."""
    cpl = p['cpl']
    if p.get('min_content') and rows:
        cpl = dict(cpl,
                   name=min(cpl['name'], max(_longest_word(r.get('ownerName')) for r in rows)),
                   occ=min(cpl['occ'], max(_longest_word(r.get('occupant')) for r in rows)))
    return sum(_row_height(r, p, cpl) for r in rows)


def paginate_by_height(data, template_name):
    """data ला पानांत वाटतो: पहिल्या पानावर मथळ्याची जागा, शेवटच्या पानावर "एकूण
    बेरीज (सर्व पाने)" ची जागा राखून. रिकामी यादी असली तरी एक (रिकामं) पान."""
    if not data:
        return [[]]
    p = _PROFILES[template_name]
    usable = p['page_h'] * p.get('safety', SAFETY) - p['thead'] - p['tfoot']
    pages, cur = [], []
    budget = usable - p['top']
    for row in data:
        if cur and _page_height(cur + [row], p) > budget:
            pages.append(cur)
            cur, budget = [], usable
        cur.append(row)
    # शेवटच्या पानावर एकूण बेरजेच्या ओळी मावत नसतील तर शेवटच्या ओळी नव्या पानावर.
    tail = []
    while len(cur) > 1 and _page_height(cur, p) + p['grand'] > budget:
        tail.insert(0, cur.pop())
    pages.append(cur)
    if tail:
        pages.append(tail)
    return pages
