/*
 * नमुना-8 single print (प्रकार 1 / 2, विशेष पाणी, Range, विशेष पाणी Range): सहीसाठी जागा (क्लायंट 16 व 19-Nov).
 *
 * "ग्रामपंचायत अधिकारी" च्या वर किमान ~10mm जागा (.n8-sign-space, min-height; सहीचा फोटो असल्यास
 * तो याच जागेत) टेम्पलेटमध्येच आहे. ती जागा
 * आल्यामुळे जी मालमत्ता आधी एका पानावर मावत होती ती दोन पानांवर जाऊ नये: प्रिंटच्या आधी
 * (beforeprint) प्रत्येक दिसणारी मालमत्ता (.record-page, नाहीतर #mainContent) प्रिंटच्या रुंदीवर
 * दोनदा मोजतो - जागेसह आणि जागेशिवाय. जागेशिवाय एका पानात मावत होती पण जागेसह मावत नाही, तेवढ्याच
 * मालमत्तेला CSS zoom ने थोडं लहान करतो. zoom 0.88 पेक्षा कमी कधीच नाही (क्लायंट: अक्षर ~88% पर्यंतच
 * लहान) - तेवढ्यावरही मावत नसेल तर त्या मालमत्तेची जागाच मावेल इतकी कमी करतो. जी मालमत्ता आधीच
 * दोन पानांवर जात होती (सहीची ओळ दुसऱ्या पानावर) ती तशीच - तिथे दुसऱ्या पानावर भरपूर जागा असते.
 * प्रिंट झाल्यावर (afterprint) सगळं परत (स्क्रीनवरचा zoom तसाच).
 *
 * page_numbers.js च्या आधी लोड करावं - Windows 8 वर तो zoom लागल्यानंतरच पानं मोजतो.
 * फक्त ES5 + जुने DOM API - Windows 8 वरच्या Chrome/Edge 109 मध्ये चालावं म्हणून.
 */
(function () {
    'use strict';
    if (window.__n8SignFit) return;
    window.__n8SignFit = true;

    var PX_PER_MM = 96 / 25.4;
    var DEFAULT_MARGIN_MM = 10.16;      // @page मध्ये margin नसेल तर Chrome चे default (~0.4 inch)
    var FLOOR = 0.88;                   // याहून लहान अक्षर नको
    var TARGET = 0.97;                  // प्रत्यक्ष प्रिंटमध्ये अक्षरांची रुंदी थोडी वेगळी - तेवढी जागा राखतो
    var MAX_SHRINK = 1.5;               // रुंद मजकूर Chrome जास्तीत जास्त एवढा लहान करून छापतो (page_numbers.js)
    // Windows 8 (Chrome/Edge 109) वर page_numbers.js "पृष्ठ 1 / 1" ची ओळ मजकुरात टाकतो आणि पान
    // 97% भरलं तरच एका पानात ठेवतो; Windows 10/11 वर क्रमांक पानाच्या margin मध्ये - जागा लागत नाही.
    var OLD_CHROME = typeof window.CSSMarginRule === 'undefined';
    var PAGE_NO_ROOM = OLD_CHROME ? 20 : 0;
    var TODAY_FIT = OLD_CHROME ? 0.97 : 1.0;

    var css = document.createElement('style');
    css.textContent = '.n8-sign-off .n8-sign-space { min-height: 0 !important; }';
    (document.head || document.documentElement).appendChild(css);

    function eachRule(rules, fn) {
        for (var i = 0; i < rules.length; i++) {
            fn(rules[i]);
            if (rules[i].cssRules && rules[i].type === 4) eachRule(rules[i].cssRules, fn);
        }
    }
    function eachSheetRule(fn) {
        var sheets = document.styleSheets;
        for (var s = 0; s < sheets.length; s++) {
            var rules;
            try { rules = sheets[s].cssRules; } catch (e) { continue; }
            if (rules) eachRule(rules, fn);
        }
    }
    // मोजताना print CSS लागू: @media print -> all, @media screen -> not all.
    function emulatePrintMedia() {
        var flips = [];
        eachSheetRule(function (rule) {
            if (rule.type !== 4) return;
            var text = rule.media.mediaText;
            var p = /\bprint\b/i.test(text), sc = /\bscreen\b/i.test(text);
            var next = (p && !sc) ? 'all' : ((sc && !p) ? 'not all' : null);
            if (next !== null) { flips.push([rule.media, text]); rule.media.mediaText = next; }
        });
        return function () {
            for (var i = flips.length - 1; i >= 0; i--) flips[i][0].mediaText = flips[i][1];
        };
    }
    function toMm(v) {
        var m = /^(-?[\d.]+)(mm|cm|in|px|pt)?$/.exec(String(v || '').trim());
        if (!m) return null;
        var n = parseFloat(m[1]);
        return m[2] === 'cm' ? n * 10 : m[2] === 'in' ? n * 25.4 : m[2] === 'px' ? n / PX_PER_MM : m[2] === 'pt' ? n * 25.4 / 72 : n;
    }
    // @page (A4 landscape + margin) वरून छापील भागाची रुंदी / उंची (px)
    function pageBox() {
        var size = '', mg = { top: null, right: null, bottom: null, left: null };
        eachSheetRule(function (rule) {
            if (rule.type !== 6 || (rule.selectorText && rule.selectorText.trim())) return;
            if (rule.style.getPropertyValue('size')) size = rule.style.getPropertyValue('size');
            for (var side in mg) {
                var v = rule.style.getPropertyValue('margin-' + side);
                if (v) mg[side] = toMm(v);
            }
        });
        var w = 210, h = 297;
        if (/landscape/i.test(size)) { w = 297; h = 210; }
        function m(v) { return v === null ? DEFAULT_MARGIN_MM : v; }
        return { w: (w - m(mg.left) - m(mg.right)) * PX_PER_MM, h: (h - m(mg.top) - m(mg.bottom)) * PX_PER_MM };
    }

    function visible(el) { return el.getClientRects().length > 0; }

    var undo = [];
    function restoreAll() {
        while (undo.length) { try { undo.pop()(); } catch (e) { /* बाकीचं तरी परत */ } }
    }

    function fitAll() {
        restoreAll();
        var pages = document.querySelectorAll('.record-page'), units = [], single = false;
        for (var i = 0; i < pages.length; i++) if (visible(pages[i])) units.push(pages[i]);
        if (!pages.length) {
            var mc = document.getElementById('mainContent');
            if (mc) { units.push(mc); single = true; }
        }
        if (!units.length) return;
        var de = document.documentElement, body = document.body;
        var mc0 = document.getElementById('mainContent');
        var box = pageBox();
        var oldWidth = de.style.width, oldMcZoom = mc0 ? mc0.style.zoom : '';
        var restoreMedia = emulatePrintMedia();
        var plan = [];

        // मजकूर पानापेक्षा रुंद असेल (नमुना-8 चं रुंद टेबल) तर Chrome तो जास्तीत जास्त 1.5 पट रुंदीवर
        // मांडतो आणि तेवढा लहान करून छापतो (page_numbers.js प्रमाणे) - म्हणजे एका पानात तेवढ्याच
        // प्रमाणात जास्त उंची मावते. ती रुंदी लावून एका पानाची उंची (layout px) परत देतो.
        function layoutPage() {
            de.style.width = box.w + 'px';
            var sw = Math.max(de.scrollWidth, body.scrollWidth);
            var lw = Math.min(Math.max(box.w, sw), box.w * MAX_SHRINK);
            if (lw > box.w) de.style.width = lw + 'px';
            return box.h * lw / box.w;
        }
        // एका मालमत्तेची छापील उंची. single: body + body margin (8px वर + खाली); range: ती .record-page
        // (पहिल्या दिसणाऱ्यावर body चा वरचा 8px).
        function baseHeights() {
            var out = [];
            for (var k = 0; k < units.length; k++) {
                out.push(single ? body.getBoundingClientRect().height + 16 : units[k].getBoundingClientRect().height + (k === 0 ? 8 : 0));
            }
            return out;
        }
        // zoom लावलेल्या घटकाची स्वतःची उंची जुन्या Chrome मध्ये नीट येत नाही - म्हणून पालकाची (zoom
        // नसलेला) उंची ती मालमत्ता दाखवून व लपवून मोजतो.
        function measured(p) {
            if (single) return body.getBoundingClientRect().height + 16;
            var par = p.u.parentNode, shown = par.getBoundingClientRect().height, disp = p.u.style.display;
            p.u.style.display = 'none';
            var hidden = par.getBoundingClientRect().height;
            p.u.style.display = disp;
            return shown - hidden + (p.first ? 8 : 0);
        }
        function fitsAt(p, z) {
            p.u.style.zoom = z;
            var pageH = layoutPage();
            return measured(p) + PAGE_NO_ROOM <= pageH * TARGET;
        }
        function floor3(v) { return Math.floor(v * 1000) / 1000; }

        try {
            if (mc0) mc0.style.zoom = '';           // स्क्रीनवरचा zoom मोजताना नको
            var pageH = layoutPage();
            var withSpace = baseHeights();
            de.className += ' n8-sign-off';
            var without = baseHeights();
            de.className = de.className.replace(/\s*n8-sign-off/g, '');
            for (var k = 0; k < units.length; k++) {
                // +1px: मोजणी अगदी काठावर (उदा. 885.0 / 885.1) - आज एका पानावर असलेली सुटू नये
                if (without[k] + PAGE_NO_ROOM <= pageH * TODAY_FIT + 1 && withSpace[k] + PAGE_NO_ROOM > pageH * TARGET) {
                    plan.push({ u: units[k], h: withSpace[k], first: !single && k === 0 });
                }
            }
            if (plan.length) {
                // पहिला अंदाज: त्याच रुंदीवर zoom z ने उंची <= z * उंची (रुंदी वाढून ओळी कमी मोडतात),
                // म्हणून (पान / उंची) हा zoom नक्की मावतो.
                for (var n = 0; n < plan.length; n++) {
                    plan[n].z = Math.max(FLOOR, floor3((pageH * TARGET - PAGE_NO_ROOM) / plan[n].h));
                    plan[n].u.style.zoom = plan[n].z;
                }
                // zoom मुळे मजकूर अरुंद होऊन Chrome चं लहान करणं कमी झालं (उदा. एकच मालमत्ता छापताना) किंवा
                // अंदाज FLOOR ला अडला - तर प्रत्येकासाठी प्रत्यक्ष मोजून ठरवतो.
                var recheck = single || layoutPage() < pageH - 0.5;
                for (var m = 0; m < plan.length; m++) {
                    var p = plan[m];
                    if (!recheck && p.z > FLOOR) continue;
                    if (fitsAt(p, p.z)) continue;
                    if (fitsAt(p, FLOOR)) {
                        var lo = FLOOR, hi = p.z;
                        for (var it = 0; it < 7; it++) { var mid = (lo + hi) / 2; if (fitsAt(p, mid)) lo = mid; else hi = mid; }
                        p.z = floor3(lo);
                    } else {
                        // FLOOR वरही मावत नाही - या मालमत्तेची सहीची जागा मावेल इतकीच ठेवतो
                        p.z = FLOOR;
                        var sp = p.u.querySelectorAll('.n8-sign-space'), a = 0, b = 10 * PX_PER_MM;
                        for (var t = 0; t < 7 && sp.length; t++) {
                            var c = (a + b) / 2;
                            for (var q = 0; q < sp.length; q++) sp[q].style.minHeight = c + 'px';
                            if (fitsAt(p, FLOOR)) a = c; else b = c;
                        }
                        p.space = Math.floor(a);
                        for (var r = 0; r < sp.length; r++) sp[r].style.minHeight = '';
                    }
                    p.u.style.zoom = p.z;
                }
            }
        } finally {
            for (var x = 0; x < plan.length; x++) plan[x].u.style.zoom = '';
            de.className = de.className.replace(/\s*n8-sign-off/g, '');
            de.style.width = oldWidth;
            if (mc0) mc0.style.zoom = oldMcZoom;
            restoreMedia();
        }
        var applied = [], reduced = 0;
        for (var j = 0; j < plan.length; j++) {
            (function (p) {
                var old = p.u.style.zoom;
                p.u.style.zoom = String(p.z);
                applied.push(p.z);
                undo.push(function () { p.u.style.zoom = old; if (single && typeof updateZoom === 'function') updateZoom(); });
                if (p.space !== undefined) {
                    reduced++;
                    var sp = p.u.querySelectorAll('.n8-sign-space');
                    for (var q = 0; q < sp.length; q++) {
                        sp[q].style.minHeight = p.space + 'px';
                        (function (el) { undo.push(function () { el.style.minHeight = ''; }); })(sp[q]);
                    }
                }
            })(plan[j]);
        }
        window.__n8SignFitLast = { units: units.length, fitted: applied, reducedSpace: reduced };
    }

    window.addEventListener('beforeprint', function () {
        try { fitAll(); } catch (e) { restoreAll(); if (window.console) console.error('n8 sign fit:', e); }
    });
    window.addEventListener('afterprint', restoreAll);
})();
