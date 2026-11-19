/*
 * एक मालमत्ता/बिल = एक A4 शीट (नमुना ९ क, ९ क-2, लेख, लेख-2): प्रत्येक .outer-border एका
 * शीटवर मावलं पाहिजे. मालकांची नावं खूप लांब असली (उदा. 4 मालक) तर बिलाचा शेवटचा भाग
 * (सहीची ओळ) पुढच्या शीटवर जायचा. हे script प्रिंट-रुंदीवर (A4, @page margin 0) प्रत्येक
 * .outer-border ची उंची मोजतं आणि शीटपेक्षा उंच असेल तेवढंच बिल (CSS zoom ने) लहान करतं -
 * बाकीची बिलं जशीच्या तशी. पानावर load झाल्यावर आणि प्रिंटच्या आधी (beforeprint) चालतं.
 *
 * फक्त ES5 + जुने DOM API - Windows 8 वरच्या Chrome/Edge 109 मध्ये चालावं म्हणून.
 */
(function () {
    'use strict';
    if (window.__fitSheets) return;
    window.__fitSheets = true;

    var PX_PER_MM = 96 / 25.4;
    var PAPER_W_MM = 210, PAPER_H_MM = 297;
    // उंची मोजणं आणि प्रत्यक्ष प्रिंट यात थोडा फरक पडू शकतो (अक्षरांची रुंदी) - तेवढी जागा राखतो.
    var FILL = 0.97;

    // विशेष पाणी ९ क-2: एका A4 वर 2x2 ठराविक (148mm) चौकटी (.report-cell, overflow hidden) - तिथे बिल
    // शीटऐवजी आपल्या चौकटीत मावलं पाहिजे, नाहीतर खालचा भाग (सहीची ओळ) कापला जातो. हे फक्त ज्या
    // पानावर <script src=".../fit_sheets.js" data-fit-cells="1"> आहे तिथेच (साधा ९ क-2 तसाच).
    var me = document.currentScript;
    var FIT_CELLS = !!(me && me.getAttribute('data-fit-cells'));
    // चौकटीत आज मावणारी बिलं जशीच्या तशी - फक्त खरंच चौकटीबाहेर जाणारं बिल लहान (साधा ९ क-2: 2 बिलं)
    var CELL_FILL = 1.0;

    function eachRule(rules, fn) {
        for (var i = 0; i < rules.length; i++) {
            fn(rules[i]);
            if (rules[i].cssRules && rules[i].type === 4) eachRule(rules[i].cssRules, fn);
        }
    }

    // मोजताना print CSS लागू: @media print -> all, @media screen -> not all.
    function emulatePrintMedia() {
        var flips = [];
        var sheets = document.styleSheets;
        for (var s = 0; s < sheets.length; s++) {
            var rules;
            try { rules = sheets[s].cssRules; } catch (e) { continue; }
            if (!rules) continue;
            eachRule(rules, function (rule) {
                if (rule.type !== 4) return;
                var text = rule.media.mediaText;
                var p = /\bprint\b/i.test(text), sc = /\bscreen\b/i.test(text);
                var next = (p && !sc) ? 'all' : ((sc && !p) ? 'not all' : null);
                if (next !== null) { flips.push([rule.media, text]); rule.media.mediaText = next; }
            });
        }
        return function () {
            for (var i = flips.length - 1; i >= 0; i--) flips[i][0].mediaText = flips[i][1];
        };
    }

    function px(v) { return parseFloat(v) || 0; }

    function visible(el) { return el.getClientRects().length > 0; }

    // फक्त दिसणारी (स्क्रीनवरचं पान / प्रिंटसाठी निवडलेली From..To) बिलं मोजतो - आधी सगळी
    // (उदा. 916) बिलं क्षणभर दाखवून प्रत्येकी एक layout व्हायचा, त्यामुळे एका बिलाच्या Print
    // लाही 10+ सेकंद लागायचे. आता: आधी सगळ्यांचा zoom काढतो, मग एकाच layout मध्ये सगळ्यांच्या
    // उंच्या वाचतो, मग zoom लावतो (मधे लिहिणं-वाचणं आलटून पालटून नाही).
    function fit(list) {
        if (!list.length) return;
        var de = document.documentElement;
        var oldWidth = de.style.width;
        var restore = emulatePrintMedia();
        var pageLimit = PAPER_H_MM * PX_PER_MM * FILL;
        var plan = [];
        try {
            de.style.width = (PAPER_W_MM * PX_PER_MM) + 'px';
            for (var i = 0; i < list.length; i++) list[i].style.zoom = '';
            for (var k = 0; k < list.length; k++) {
                var el = list[k];
                var cs = window.getComputedStyle(el);
                var total = el.getBoundingClientRect().height + px(cs.marginTop) + px(cs.marginBottom);
                var limit = pageLimit, cell = FIT_CELLS ? el.parentNode : null;
                if (cell && cell.className && /(^|\s)report-cell(\s|$)/.test(cell.className)) {
                    var ccs = window.getComputedStyle(cell);
                    limit = (cell.clientHeight - px(ccs.paddingTop) - px(ccs.paddingBottom)) * CELL_FILL;
                }
                if (total > limit) plan.push([el, limit / total]);
            }
        } finally {
            de.style.width = oldWidth;
            restore();
        }
        for (var j = 0; j < list.length; j++) list[j].__fitZoom = '';
        for (var n = 0; n < plan.length; n++) {
            var z = String(Math.floor(plan[n][1] * 1000) / 1000);
            plan[n][0].style.zoom = z;
            plan[n][0].__fitZoom = z;
        }
        if (FIT_CELLS && plan.length) refineCells(plan);
    }

    // थोड्या zoom ने अक्षरांचा आकार पूर्ण px ला गोल होतो - उंची zoom इतकी कमी होत नाही (उदा. 0.985 ने
    // 544 -> 541.5px, चौकट 536px). म्हणून चौकटीतलं बिल अजून बाहेर जात असेल (चौकटीचं scrollHeight >
    // clientHeight) तर त्याच प्रमाणात थोडं अजून लहान करतो - जास्तीत जास्त 6 वेळा.
    function refineCells(plan) {
        var de = document.documentElement;
        for (var pass = 0; pass < 6; pass++) {
            var oldWidth = de.style.width, restore = emulatePrintMedia(), adj = [];
            try {
                de.style.width = (PAPER_W_MM * PX_PER_MM) + 'px';
                for (var i = 0; i < plan.length; i++) {
                    var el = plan[i][0], cell = el.parentNode;
                    if (!cell || !/(^|\s)report-cell(\s|$)/.test(cell.className || '')) continue;
                    if (cell.scrollHeight > cell.clientHeight) adj.push([el, cell.clientHeight / cell.scrollHeight]);
                }
            } finally {
                de.style.width = oldWidth;
                restore();
            }
            if (!adj.length) return;
            for (var k = 0; k < adj.length; k++) {
                var z = String(Math.floor(((parseFloat(adj[k][0].style.zoom) || 1) * adj[k][1] - 0.005) * 1000) / 1000);
                adj[k][0].style.zoom = z;
                adj[k][0].__fitZoom = z;
            }
        }
    }

    function visibleSheets() {
        var sheets = document.querySelectorAll('.outer-border'), out = [];
        for (var i = 0; i < sheets.length; i++) if (visible(sheets[i])) out.push(sheets[i]);
        return out;
    }

    function fitVisible() {
        try {
            var list = visibleSheets();
            for (var i = 0; i < list.length; i++) list[i].__fitSeen = true;
            fit(list);
        } catch (e) {
            if (window.console) console.error('fit sheets:', e);
        }
    }

    // स्क्रीनवर नवीन दिसलेली बिलं (पुढचं पान वगैरे) - आधी लोड वेळी सगळी बिलं मोजली जायची,
    // आता पहिल्यांदा दिसताना. वापरकर्त्याने Zoom +/- केलं असेल (zoom आपण लावलेला नाही) तर
    // तसंच ठेवतो - आधीही Zoom सगळ्या बिलांवर लागायचा.
    function fitNewlyVisible() {
        try {
            var sheets = document.querySelectorAll('.outer-border'), list = [];
            for (var i = 0; i < sheets.length; i++) {
                var el = sheets[i];
                var shown = visible(el);
                if (shown && !el.__fitSeen) {
                    var z = el.style.zoom;
                    if (z === '' || z === '1' || z === el.__fitZoom) list.push(el);
                }
                el.__fitSeen = shown;
            }
            fit(list);
        } catch (e) {
            if (window.console) console.error('fit sheets:', e);
        }
    }

    var scheduled = false;
    function schedule() {
        if (scheduled) return;
        scheduled = true;
        setTimeout(function () { scheduled = false; fitNewlyVisible(); }, 0);
    }

    window.addEventListener('load', function () {
        fitVisible();
        if (window.MutationObserver && document.body) {
            new MutationObserver(schedule).observe(document.body,
                { attributes: true, attributeFilter: ['style'], subtree: true });
        }
    });
    window.addEventListener('beforeprint', fitVisible);
})();
