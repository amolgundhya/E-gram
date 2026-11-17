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

    function fit() {
        var sheets = document.querySelectorAll('.outer-border');
        if (!sheets.length) return;
        var de = document.documentElement;
        var oldWidth = de.style.width;
        var restore = emulatePrintMedia();
        var limit = PAPER_H_MM * PX_PER_MM * FILL;
        var plan = [];
        try {
            de.style.width = (PAPER_W_MM * PX_PER_MM) + 'px';
            for (var i = 0; i < sheets.length; i++) {
                var el = sheets[i];
                el.style.zoom = '';
                if (!el.getClientRects().length) continue; // लपवलेलं (स्क्रीनवर दुसरं पान)
                var cs = window.getComputedStyle(el);
                var total = el.getBoundingClientRect().height + px(cs.marginTop) + px(cs.marginBottom);
                if (total > limit) plan.push([el, limit / total]);
            }
        } finally {
            de.style.width = oldWidth;
            restore();
        }
        for (var j = 0; j < plan.length; j++) plan[j][0].style.zoom = String(Math.floor(plan[j][1] * 1000) / 1000);
    }

    // लपवलेली (स्क्रीनवर दुसऱ्या पानावरची) बिलं मोजता येत नाहीत - प्रत्येक बिल मोजण्यासाठी
    // क्षणभर सगळी दाखवतो, मोजून झाल्यावर पुन्हा जसं होतं तसं.
    function fitAll() {
        var sheets = document.querySelectorAll('.outer-border');
        var display = [];
        for (var i = 0; i < sheets.length; i++) {
            display.push(sheets[i].style.display);
            if (sheets[i].style.display === 'none') sheets[i].style.display = '';
        }
        try {
            fit();
        } catch (e) {
            if (window.console) console.error('fit sheets:', e);
        } finally {
            for (var k = 0; k < sheets.length; k++) sheets[k].style.display = display[k];
        }
    }

    window.addEventListener('load', fitAll);
    window.addEventListener('beforeprint', fitAll);
})();
