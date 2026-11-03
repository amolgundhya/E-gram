/*
 * सर्व रजिस्टर रिपोर्ट्सवर "पृष्ठ X / Y" पान क्रमांक.
 *
 * Chrome/Edge 131+ (Windows 10/11): @page { @bottom-center { counter(page) } } - ब्राउझरचाच अचूक क्रमांक.
 *
 * Windows 8 वर Chrome/Edge 109 पुढे जात नाही आणि त्यात हे CSS चालत नाही. तिथे प्रिंटच्या आधी
 * (beforeprint) हे script प्रिंट CSS लावून रिपोर्ट मोजतं; पान भरलं की तिथे पान क्रमांकाची ओळ +
 * page-break टाकतं (टेबलचं हेडर Chrome प्रत्येक पानावर स्वतः repeat करतो), आणि प्रिंट झाल्यावर
 * (afterprint) सगळे बदल परत काढतं - स्क्रीनवरचा रिपोर्ट तसाच राहतो. रिपोर्टमधले आधीचे page-break तसेच.
 *
 * दोन्हीमध्ये क्रमांक छापल्या जाणाऱ्या पानांचे: From/To ने 3 ते 5 छापलं तर पृष्ठ 1 / 3 ... 3 / 3.
 *
 * फक्त ES5 + जुने DOM API - Windows 8 वरच्या Chrome/Edge 109 मध्ये चालावं म्हणून.
 */
(function () {
    'use strict';
    if (window.__reportPageNumbers) return;
    window.__reportPageNumbers = true;

    var PX_PER_MM = 96 / 25.4;
    // स्क्रीनवर मोजलेली उंची आणि प्रत्यक्ष प्रिंट यात फरक पडतो - Windows प्रिंटमध्ये अक्षरांची
    // रुंदी थोडी वेगळी धरतो, त्यामुळे काही ओळी वेगळ्या ठिकाणी मोडतात (मोजून ~5% पर्यंत).
    // ओळ पुढच्या शीटवर जाऊन क्रमांक चुकू नये म्हणून पानाची एवढीच उंची भरतो.
    var SAFETY = 0.86;
    // रुंद टेबल असेल तर Chrome पान जास्तीत जास्त एवढं लहान (shrink-to-fit) करून छापतो.
    var MAX_SHRINK = 1.5;
    // @page मध्ये margin नसेल तर Chrome चे "Default" margin (~0.4 inch).
    var DEFAULT_MARGIN_MM = 10.16;
    var PAPER_MM = { a3: [297, 420], a4: [210, 297], a5: [148, 210], letter: [215.9, 279.4], legal: [215.9, 355.6] };
    var LABEL = '\u092a\u0943\u0937\u094d\u0920 ';  // पृष्ठ 

    var undoList = [];
    var fullPageHeight = 0; // एका पानाची पूर्ण छापील उंची (layout px, SAFETY शिवाय)

    function undoAll() {
        while (undoList.length) {
            try { undoList.pop()(); } catch (e) { /* पुढचे बदल तरी परत जावेत */ } 
        }
    }

    function setStyle(el, prop, value) {
        var old = el.style.getPropertyValue(prop);
        var oldPriority = el.style.getPropertyPriority(prop);
        undoList.push(function () {
            if (old) el.style.setProperty(prop, old, oldPriority);
            else el.style.removeProperty(prop);
        });
        el.style.setProperty(prop, value, 'important');
    }

    function insertNode(node, parent, before) {
        parent.insertBefore(node, before || null);
        undoList.push(function () {
            if (node.parentNode) node.parentNode.removeChild(node);
        });
    }

    // ---------- CSS वाचणे ----------

    function eachRule(rules, fn) {
        for (var i = 0; i < rules.length; i++) {
            var rule = rules[i];
            fn(rule);
            if (rule.cssRules && rule.type === 4) eachRule(rule.cssRules, fn); // @media
        }
    }

    function eachSheetRule(fn) {
        var sheets = document.styleSheets;
        for (var i = 0; i < sheets.length; i++) {
            var rules;
            try { rules = sheets[i].cssRules; } catch (e) { continue; } // दुसऱ्या origin चं stylesheet
            if (rules) eachRule(rules, fn);
        }
    }

    // मोजताना स्क्रीनवर print CSS लागू करतो: @media print -> all, @media screen -> not all.
    function emulatePrintMedia() {
        var flips = [];
        eachSheetRule(function (rule) {
            if (rule.type !== 4) return;
            var text = rule.media.mediaText;
            var hasPrint = /\bprint\b/i.test(text);
            var hasScreen = /\bscreen\b/i.test(text);
            var next = null;
            if (hasPrint && !hasScreen) next = 'all';
            else if (hasScreen && !hasPrint) next = 'not all';
            if (next !== null) {
                flips.push([rule.media, text]);
                rule.media.mediaText = next;
            }
        });
        return function restore() {
            for (var i = flips.length - 1; i >= 0; i--) flips[i][0].mediaText = flips[i][1];
        };
    }

    function lengthToMm(value) {
        var m = /^(-?[\d.]+)(mm|cm|in|px|pt)?$/.exec(String(value || '').trim());
        if (!m) return null;
        var n = parseFloat(m[1]);
        switch (m[2]) {
            case 'cm': return n * 10;
            case 'in': return n * 25.4;
            case 'px': return n / PX_PER_MM;
            case 'pt': return n * 25.4 / 72;
            default: return n; // mm किंवा 0
        }
    }

    // @page मधून कागदाचा आकार व margin (mm) - नसेल तर A4 portrait + Chrome default margin.
    function readPageBox() {
        var size = '';
        var margin = { top: null, right: null, bottom: null, left: null };
        eachSheetRule(function (rule) {
            if (rule.type !== 6 || (rule.selectorText && rule.selectorText.trim())) return; // फक्त साधं @page
            var s = rule.style;
            if (s.getPropertyValue('size')) size = s.getPropertyValue('size');
            ['top', 'right', 'bottom', 'left'].forEach(function (side) {
                var v = s.getPropertyValue('margin-' + side);
                if (v) margin[side] = lengthToMm(v);
            });
        });

        var tokens = size.toLowerCase().split(/\s+/).filter(Boolean);
        var w = PAPER_MM.a4[0], h = PAPER_MM.a4[1], landscape = false;
        var lengths = [];
        tokens.forEach(function (t) {
            if (PAPER_MM[t]) { w = PAPER_MM[t][0]; h = PAPER_MM[t][1]; }
            else if (t === 'landscape') landscape = true;
            else if (lengthToMm(t) !== null) lengths.push(lengthToMm(t));
        });
        if (lengths.length) { w = lengths[0]; h = lengths[1] || lengths[0]; }
        else if (landscape) { var tmp = w; w = h; h = tmp; }

        function mm(v) { return v === null ? DEFAULT_MARGIN_MM : v; }
        return {
            width: (w - mm(margin.left) - mm(margin.right)) * PX_PER_MM,
            height: (h - mm(margin.top) - mm(margin.bottom)) * PX_PER_MM
        };
    }

    // ---------- पान क्रमांकाचा घटक ----------

    function styleMarker(el) {
        var s = el.style;
        s.setProperty('font-size', '10px', 'important');
        s.setProperty('line-height', '14px', 'important');
        s.setProperty('text-align', 'center', 'important');
        s.setProperty('color', '#000', 'important');
        s.setProperty('background', 'none', 'important');
        s.setProperty('border', '0', 'important');
        s.setProperty('padding', '2px 0 0 0', 'important');
        s.setProperty('margin', '0', 'important');
        s.setProperty('height', 'auto', 'important');
        s.setProperty('break-inside', 'avoid', 'important');
        s.setProperty('page-break-inside', 'avoid', 'important');
    }

    function makeMarker(text, asRow, cols) {
        if (asRow) {
            var tr = document.createElement('tr');
            tr.className = 'report-page-number';
            var td = document.createElement('td');
            td.colSpan = cols || 1;
            td.textContent = text;
            styleMarker(tr);
            styleMarker(td);
            tr.appendChild(td);
            return tr;
        }
        var div = document.createElement('div');
        div.className = 'report-page-number';
        div.textContent = text;
        styleMarker(div);
        return div;
    }

    function columnCount(row) {
        var n = 0;
        for (var i = 0; i < row.cells.length; i++) n += row.cells[i].colSpan || 1;
        return n || 1;
    }

    function isTableRow(el) { return el.tagName === 'TR'; }

    function isRendered(el) {
        return el.getClientRects().length > 0;
    }

    function hasForcedBreak(value) {
        return value === 'page' || value === 'always' || value === 'left' || value === 'right' ||
            value === 'recto' || value === 'verso';
    }

    // ---------- पानं मोजणे ----------

    function absTop(rect) { return rect.top + window.pageYOffset; }

    // पानं ठरवण्यासाठी क्रमाने "तुकडे" (rows/blocks) आणि forced page-breaks.
    function collect(root, pageHeight, seq) {
        for (var el = root.firstElementChild; el; el = el.nextElementSibling) {
            if (/^(SCRIPT|STYLE|LINK|META|TEMPLATE|NOSCRIPT)$/.test(el.tagName)) continue;
            if (el.className === 'report-page-number' || !isRendered(el)) continue;
            var cs = window.getComputedStyle(el);
            if (cs.position === 'fixed' || cs.position === 'absolute') continue;

            if (hasForcedBreak(cs.breakBefore || cs.pageBreakBefore)) seq.push({ forced: 'before', el: el });

            var rect = el.getBoundingClientRect();
            if (el.tagName === 'TABLE' && /table/.test(cs.display)) {
                collectTable(el, seq);
            } else if (rect.height > pageHeight * 0.5 && el.firstElementChild && !/^inline/.test(cs.display)) {
                collect(el, pageHeight, seq);
            } else {
                seq.push({ el: el, top: absTop(rect), bottom: absTop(rect) + rect.height });
            }

            if (hasForcedBreak(cs.breakAfter || cs.pageBreakAfter)) seq.push({ forced: 'after', el: el });
        }
    }

    function sectionHeight(section) {
        if (!section || !isRendered(section)) return 0;
        return section.getBoundingClientRect().height;
    }

    // Chrome thead/tfoot प्रत्येक पानावर repeat करतो - पण ते पानाच्या 1/4 पेक्षा उंच असेल तरच नाही
    // (नमुना-8 चा मोठा मथळा फक्त पहिल्या पानावर येतो). तेवढीच जागा पुढच्या पानांवर राखून ठेवतो.
    function repeatedHeight(section) {
        var h = sectionHeight(section);
        return h <= fullPageHeight / 4 ? h : 0;
    }

    function collectTable(table, seq) {
        var info = {
            table: table,
            head: repeatedHeight(table.tHead),
            foot: repeatedHeight(table.tFoot)
        };
        if (sectionHeight(table.tHead)) {
            var hr = table.tHead.getBoundingClientRect();
            seq.push({ el: table, isHead: true, top: absTop(hr), bottom: absTop(hr) + hr.height });
        }
        for (var b = 0; b < table.tBodies.length; b++) {
            var rows = table.tBodies[b].rows;
            for (var r = 0; r < rows.length; r++) {
                var row = rows[r];
                if (!isRendered(row) || row.className === 'report-page-number') continue;
                var rr = row.getBoundingClientRect();
                if (!rr.height) continue;
                seq.push({ el: row, table: info, top: absTop(rr), bottom: absTop(rr) + rr.height });
            }
        }
        if (sectionHeight(table.tFoot)) {
            var fr = table.tFoot.getBoundingClientRect();
            seq.push({ el: table.tFoot, isFoot: true, table: info, top: absTop(fr), bottom: absTop(fr) + fr.height });
        }
    }

    // दोन forced page-break मधला मजकूर (उदा. नमुना-9 चं एक .print-page, नमुना-8 प्रकार 4 चे 3 रेकॉर्ड)
    // रिपोर्टनेच एका पानासाठी बनवलेला असतो - तो पूर्ण पानात मावत असेल तर त्यात आणखी break टाकत नाही
    // (नाहीतर SAFETY मुळे जवळजवळ प्रत्येक पान दोनदा छापलं जातं).
    var SEGMENT_FIT = 0.97;

    function segmentFits(seq, from, markerHeight) {
        var top = null, bottom = null;
        for (var i = from; i < seq.length && !seq[i].forced; i++) {
            if (top === null) top = seq[i].top;
            bottom = Math.max(bottom === null ? seq[i].bottom : bottom, seq[i].bottom);
        }
        return top === null || bottom - top + markerHeight <= fullPageHeight * SEGMENT_FIT;
    }

    // पान कुठे संपतं ते ठरवतो. प्रत्येक पानासाठी {end: {...}} - तिथे क्रमांक टाकायचा.
    function paginate(seq, pageHeight, markerHeight) {
        var pages = [];
        var page = null;
        var wholeSegment = segmentFits(seq, 0, markerHeight);

        function close(end) {
            if (page && page.last) {
                page.end = end;
                pages.push(page);
            }
            page = null;
        }

        for (var i = 0; i < seq.length; i++) {
            var item = seq[i];
            if (item.forced) {
                // forced break आधी पान संपतं - "after" असेल तर त्याच घटकाच्या शेवटी क्रमांक
                close({ kind: 'forced-' + item.forced, el: item.el });
                wholeSegment = segmentFits(seq, i + 1, markerHeight);
                continue;
            }
            if (!page) page = { start: item.top, extra: 0, last: null };
            if (wholeSegment) {
                page.last = item;
                continue;
            }

            var footRoom = (item.table && !item.isFoot) ? item.table.foot : 0;
            var used = item.bottom - page.start + page.extra + footRoom + markerHeight;
            if (used > pageHeight && page.last && !item.isFoot) {
                close({ kind: 'before', item: item });
                page = {
                    start: item.top,
                    // या पानावर Chrome टेबलचं हेडर पुन्हा छापेल - तेवढी जागा आधीच गेली
                    extra: (item.table && !item.isHead) ? item.table.head : 0,
                    last: null
                };
            }
            page.last = item;
        }
        close({ kind: 'end' });
        return pages;
    }

    function placeMarker(end, last, text) {
        if (end.kind === 'before') {
            var item = end.item;
            var target = item.isHead ? item.el /* table */ : item.el;
            var asRow = isTableRow(target);
            insertNode(makeMarker(text, asRow, asRow ? columnCount(target) : 0), target.parentNode, target);
            setStyle(target, 'break-before', 'page');
            setStyle(target, 'page-break-before', 'always');
            return;
        }
        if (end.kind === 'forced-before') {
            var el = end.el;
            var row = isTableRow(el);
            insertNode(makeMarker(text, row, row ? columnCount(el) : 0), el.parentNode, el);
            return;
        }
        if (end.kind === 'forced-after') {
            var e = end.el;
            if (isTableRow(e) || e.tagName === 'TABLE') {
                var asTr = isTableRow(e);
                var marker = makeMarker(text, asTr, asTr ? columnCount(e) : 0);
                insertNode(marker, e.parentNode, e.nextSibling);
                // break आता क्रमांकाच्या नंतर
                setStyle(e, 'break-after', 'auto');
                setStyle(e, 'page-break-after', 'auto');
                marker.style.setProperty('break-after', 'page', 'important');
                marker.style.setProperty('page-break-after', 'always', 'important');
            } else {
                insertNode(makeMarker(text, false), e, null);
            }
            return;
        }
        // शेवटचं पान: शेवटच्या ओळीनंतर
        var lastEl = last.el;
        if (isTableRow(lastEl) && !last.isFoot) {
            insertNode(makeMarker(text, true, columnCount(lastEl)), lastEl.parentNode, lastEl.nextSibling);
        } else {
            insertNode(makeMarker(text, false), document.body, null);
        }
    }

    function number() {
        var box = readPageBox();
        var de = document.documentElement;
        var restoreMedia = emulatePrintMedia();
        var seq = [];
        var pageHeight, markerHeight;
        var oldWidth = de.style.width;
        try {
            // प्रिंट-लेआउटसारखी रुंदी; टेबल रुंद असेल तर Chrome सारखं shrink-to-fit
            de.style.width = box.width + 'px';
            var contentWidth = Math.max(de.scrollWidth, document.body.scrollWidth);
            var layoutWidth = box.width;
            if (contentWidth > box.width + 1) {
                layoutWidth = Math.min(contentWidth, box.width * MAX_SHRINK);
                de.style.width = layoutWidth + 'px';
            }
            var scale = box.width / layoutWidth;
            fullPageHeight = box.height / scale;
            pageHeight = fullPageHeight * SAFETY;

            var probe = makeMarker(LABEL + '0 / 0', false);
            document.body.appendChild(probe);
            markerHeight = probe.getBoundingClientRect().height;
            document.body.removeChild(probe);

            collect(document.body, pageHeight, seq);
        } finally {
            de.style.width = oldWidth;
            restoreMedia();
        }

        var pages = paginate(seq, pageHeight, markerHeight);
        for (var i = 0; i < pages.length; i++) {
            placeMarker(pages[i].end, pages[i].last, LABEL + (i + 1) + ' / ' + pages.length);
        }
    }

    // Chrome/Edge 131+ (Windows 10/11): ब्राउझरचाच पान क्रमांक - अचूक, कागद जास्त लागत नाही.
    if (typeof window.CSSMarginRule !== 'undefined') {
        var css = document.createElement('style');
        css.className = 'report-page-number-css';
        css.textContent = '@page { @bottom-center { content: "' + LABEL + '" counter(page) " / " counter(pages); ' +
            'font-size: 10px; font-family: Arial, sans-serif; color: #000; } }';
        (document.head || document.documentElement).appendChild(css);
        return;
    }

    function beforePrint() {
        undoAll(); // आधीचं प्रिंट अर्धवट राहिलं असेल तर
        try {
            number();
        } catch (e) {
            // पान क्रमांकामुळे प्रिंटच थांबू नये
            undoAll();
            if (window.console) console.error('page numbers:', e);
        }
    }

    window.addEventListener('beforeprint', beforePrint);
    window.addEventListener('afterprint', undoAll);
})();
