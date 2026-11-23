/* नमुना-9 रजिस्टर (Pg2, Gen, Pani, वसुली, सूट सह, विशेष पाणी...): रकमा आपल्या
   रकान्याच्या border आत.
   - data rows मधल्या रकमा (अ.क्र. व मिळकत नंबर सोडून) आणि गोषवारा / एकूण बेरीज (tfoot) मधले
     सर्व आकडे एका span.n9amt मध्ये (एका ओळीत, nowrap).
   - नेहमीपेक्षा लहान अक्षर: data rows 0.86em, tfoot 0.8em (प्रिंटमध्ये tfoot 8px तसाच).
   - तरीही न मावणारा आकडा (स्क्रीन, प्रिंट, PDF) त्या cell पुरता आणखी लहान केला जातो.
   रकाने रुंदी / पान / rows-per-page बदल नाही. 9 All चं स्वतःचं .amt-box script आहे. */
(function () {
    var NUM = /^-?[0-9][0-9,]*(\.[0-9]+)?$/;
    var css = document.createElement('style');
    css.textContent =
        '.main-table td .n9amt { white-space: nowrap; display: inline-block; }' +
        '.main-table tbody td .n9amt { font-size: 0.86em; }' +
        '.main-table tfoot td .n9amt { font-size: 0.8em; }' +
        '@media print { .main-table tfoot td .n9amt { font-size: 1em; } }';
    document.head.appendChild(css);

    var spans = [];
    var tables = document.querySelectorAll('.main-table');
    for (var k = 0; k < tables.length; k++) {
        var cells = tables[k].querySelectorAll('tbody td, tfoot td');
        for (var i = 0; i < cells.length; i++) {
            var td = cells[i];
            if (td.querySelector('.amt-box, .n9amt') || td.children.length) continue;
            var t = td.textContent.trim();
            var inFoot = td.parentNode.parentNode.tagName === 'TFOOT';
            if (!inFoot && td.cellIndex < 2) continue;   // अ.क्र., मिळकत नंबर
            if (!NUM.test(t)) continue;
            var sp = document.createElement('span');
            sp.className = 'n9amt';
            sp.textContent = t;
            td.textContent = '';
            td.appendChild(sp);
            spans.push(sp);
        }
    }

    function fit() {
        for (var i = 0; i < spans.length; i++) spans[i].style.fontSize = '';
        for (var j = 0; j < spans.length; j++) {
            var sp = spans[j], td = sp.parentNode;
            if (!td.offsetWidth) continue;   // लपलेलं पान
            var cs = getComputedStyle(td);
            var avail = td.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
            var w = sp.scrollWidth;
            if (avail > 0 && w > avail + 0.5) {
                var f = parseFloat(getComputedStyle(sp).fontSize) * (avail / w) * 0.97;
                sp.style.fontSize = Math.max(4, f) + 'px';
            }
        }
    }

    // लपलेली पानं (showPage) पण मोजावीत म्हणून प्रिंट layout मध्ये पुन्हा.
    fit();
    window.addEventListener('resize', fit);
    if (window.matchMedia) {
        var mq = window.matchMedia('print');
        var onChange = function () { fit(); };
        if (mq.addEventListener) mq.addEventListener('change', onChange); else if (mq.addListener) mq.addListener(onChange);
    }
    window.addEventListener('beforeprint', fit);
    window.addEventListener('afterprint', fit);
})();
