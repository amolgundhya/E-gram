/*
 * नमुना ९ क / ९ क-2 / लेख / लेख-2 / विशेष पाणी ९ क / ९ क-2 viewer: पानं (बिलं) व QR.
 *
 * QR images (मालमत्ता / घर कर / पाणी कर) टेम्प्लेटमध्ये src ऐवजी data-src मध्ये असतात - viewer
 * उघडताच सगळ्या (उदा. 916) बिलांचे QR मागवले जात नाहीत. जे बिल स्क्रीनवर दिसतं त्याचेच QR
 * लोड होतात; Print बटण From..To मधल्या बिलांचे QR आधी लोड करून मग प्रिंट करतं
 * (ReportPages.ready). Share (PDF) फक्त From..To ची बिलं पाठवतो (report_share.js).
 *
 * <script src="/report_assets/report_pages.js" data-unit=".outer-border"></script>
 *   data-unit = एक पान (टेम्प्लेटचा printPage ज्यांना दाखवतो/लपवतो): .outer-border किंवा .report-grid
 *
 * फक्त ES5 + जुने DOM API - Windows 8 वरच्या Chrome/Edge 109 मध्ये चालावं म्हणून.
 */
(function () {
    'use strict';
    if (window.ReportPages) return;

    var script = document.currentScript;
    var UNIT = (script && script.getAttribute('data-unit')) || '.outer-border';
    var WAIT_MS = 60000;  // QR लोड व्हायला कमाल इतका वेळ - नंतर जे आहे ते प्रिंट

    function units() { return document.querySelectorAll(UNIT); }

    function inputValue(a, b) {
        var el = document.getElementById(a) || document.getElementById(b);
        return el ? parseInt(el.value, 10) : NaN;
    }

    // टेम्प्लेटच्या printPage सारखाच From..To (रिकामं From = 1, रिकामं To = शेवटचं पान)
    function range() {
        var total = units().length;
        var from = inputValue('printFrom', 'fromPage');
        var to = inputValue('printTo', 'toPage');
        if (!(from >= 1)) from = 1;
        if (!(to >= 1)) to = total;
        from = Math.max(1, Math.min(from, total));
        to = Math.max(from, Math.min(to, total));
        return { from: from, to: to, total: total };
    }

    function inRange() {
        var r = range(), all = units(), out = [];
        for (var i = r.from - 1; i < r.to && i < all.length; i++) out.push(all[i]);
        return out;
    }

    function loadImg(img) {
        var src = img.getAttribute('data-src');
        if (src === null) return;
        img.removeAttribute('data-src');
        img.setAttribute('src', src);
    }

    // els मधल्या सगळ्या QR चं src लावून, सगळे लोड (किंवा error) झाल्यावर cb
    var busy = false;
    function ready(els, cb) {
        if (busy) return;  // Print दोनदा दाबलं तरी एकच प्रिंट
        busy = true;
        var imgs = [];
        for (var i = 0; i < els.length; i++) {
            var list = els[i].getElementsByTagName('img');
            for (var j = 0; j < list.length; j++) {
                loadImg(list[j]);
                if (list[j].getAttribute('src') && !list[j].complete) imgs.push(list[j]);
            }
        }
        var left = imgs.length, done = false, timer = null;
        function finish() {
            if (done) return;
            done = true;
            if (timer) clearTimeout(timer);
            busy = false;
            cb();
        }
        function one() { left--; if (left <= 0) finish(); }
        if (!left) { finish(); return; }
        for (var k = 0; k < imgs.length; k++) {
            imgs[k].addEventListener('load', one);
            imgs[k].addEventListener('error', one);
        }
        timer = setTimeout(finish, WAIT_MS);
    }

    // स्क्रीनवर दिसणाऱ्या बिलांचे QR (पान बदललं / पहिल्यांदा उघडलं)
    function loadVisible() {
        var pending = document.querySelectorAll('img[data-src]');
        for (var i = 0; i < pending.length; i++) {
            if (pending[i].getClientRects().length) loadImg(pending[i]);
        }
    }
    var scheduled = false;
    function schedule() {
        if (scheduled) return;
        scheduled = true;
        setTimeout(function () { scheduled = false; loadVisible(); }, 0);
    }

    // load वर (टेम्प्लेटच्या window.onload -> showPage(1) नंतर - तो आधी नोंदलेला असतो): त्याआधी
    // सगळी बिलं दिसत असतात, तेव्हा तपासलं तर सगळेच QR लोड होतील.
    window.addEventListener('load', function () {
        loadVisible();
        if (window.MutationObserver && document.body) {
            new MutationObserver(schedule).observe(document.body,
                { attributes: true, attributeFilter: ['style'], subtree: true });
        }
    });
    window.addEventListener('beforeprint', loadVisible);

    window.ReportPages = { unit: UNIT, units: units, range: range, inRange: inRange, ready: ready };
})();
