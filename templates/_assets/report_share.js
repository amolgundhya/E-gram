/*
 * प्रत्येक रिपोर्ट viewer मध्ये "Share (PDF)" बटण - रिपोर्टची PDF Downloads मध्ये सेव्ह होते,
 * ती WhatsApp/ईमेल ने पाठवता येते. PDF backend वर (reportRoute/reportAPI.py -> /reports/share-pdf)
 * संगणकावरच्या Chrome/Edge ने बनते. viewer मध्ये एकच पान दिसत असलं तरी PDF मध्ये सगळी पानं येतात.
 *
 * फक्त ES5 + XMLHttpRequest - Windows 8 वरच्या Chrome/Edge 109 मध्ये चालावं म्हणून.
 */
(function () {
    'use strict';
    if (window.__reportShare) return;
    window.__reportShare = true;

    var LABEL = 'Share (PDF)';
    var BUSY_LABEL = 'PDF \u0924\u092f\u093e\u0930 \u0939\u094b\u0924 \u0906\u0939\u0947...';  // PDF तयार होत आहे...

    var style = document.createElement('style');
    style.textContent = '@media print { .report-share-btn { display: none !important; } }';
    (document.head || document.documentElement).appendChild(style);

    function pad(n) { return (n < 10 ? '0' : '') + n; }

    function fileName() {
        var d = new Date();
        var title = (document.title || 'report').replace(/[\\\/:*?"<>|]+/g, '_').trim() || 'report';
        return title + '_' + d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + '.pdf';
    }

    function download(blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = fileName();
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        setTimeout(function () { URL.revokeObjectURL(url); }, 10000);
    }

    function showError(xhr) {
        var reader = new FileReader();
        reader.onload = function () {
            var msg = 'PDF \u092c\u0928\u0935\u0924\u093e\u0928\u093e \u0924\u094d\u0930\u0941\u091f\u0940 \u0906\u0932\u0940.';  // PDF बनवताना त्रुटी आली.
            try { msg = JSON.parse(reader.result).detail || msg; } catch (e) { /* JSON नाही */ } 
            alert(msg);
        };
        if (xhr.response) reader.readAsText(xhr.response);
        else alert('PDF \u092c\u0928\u0935\u0924\u093e\u0928\u093e \u0924\u094d\u0930\u0941\u091f\u0940 \u0906\u0932\u0940 - backend \u091a\u093e\u0932\u0942 \u0906\u0939\u0947 \u0915\u093e \u0924\u0947 \u0924\u092a\u093e\u0938\u093e.');  // PDF बनवताना त्रुटी आली - backend चालू आहे का ते तपासा.
    }

    // नमुना ९ क / ९ क-2 / लेख वगैरे (report_pages.js असलेले viewer): PDF मध्ये फक्त From..To ची
    // पानं - आधी सगळी (उदा. 916) बिलं पाठवली जायची आणि PDF ला दोन मिनिटं लागायची. HTML ची
    // inert प्रत (DOMParser - images/scripts चालत नाहीत) बनवून बाकीची पानं काढतो; राहिलेल्या
    // पानांचे QR (data-src) src मध्ये. बाकीचे रिपोर्ट (report_pages.js नसलेले) पूर्वीसारखेच.
    //
    // नमुना ९ (सर्व, Gen, पाणी, Pg2, वसुली, सूट सह, विशेष पाणी...) - .print-page viewer (report_pages.js
    // नाही): आधी From..To दुर्लक्षित होऊन सगळी (उदा. 96-121) पानं PDF मध्ये जायची - 10 MB, 20-30 सेकंद
    // (मंद संगणकावर मिनिटं). आता हिरव्या Print सारखीच फक्त From..To ची पानं (टेम्प्लेटच्या printPage
    // सारखाच हिशोब: रिकामं From/To = 1).
    // (बहुतेक टेम्प्लेट fromPage/toPage वापरतात - तिथे रिकामं To = शेवटचं पान; 9 All/Gen/Pani
    // printFrom/printTo - तिथे रिकामं To = 1)
    function printPageRange() {
        var oldIds = !!document.getElementById('printFrom');
        var fromEl = document.getElementById(oldIds ? 'printFrom' : 'fromPage');
        var toEl = document.getElementById(oldIds ? 'printTo' : 'toPage');
        if (!fromEl || !toEl) return null;
        var total = document.querySelectorAll('.print-page').length;
        if (!total) return null;
        var from = parseInt(fromEl.value, 10) || 1;
        var to = parseInt(toEl.value, 10) || (oldIds ? 1 : total);
        from = Math.max(1, Math.min(from, total));
        to = Math.max(from, Math.min(to, total));
        return { from: from, to: to, total: total };
    }

    function selectedPagesHtml() {
        if (!window.DOMParser) return null;
        var rp = window.ReportPages;
        var unit, r;
        if (rp) { unit = rp.unit; r = rp.range(); }
        else { unit = '.print-page'; r = printPageRange(); }
        if (!r || !r.total) return null;
        var doc = new DOMParser().parseFromString(document.documentElement.outerHTML, 'text/html');
        var units = doc.querySelectorAll(unit);
        if (units.length !== r.total) return null;
        for (var i = units.length - 1; i >= 0; i--) {
            if (i + 1 < r.from || i + 1 > r.to) units[i].parentNode.removeChild(units[i]);
            else units[i].style.display = '';
        }
        // .print-page वर inline page-break-after: always (शेवटचं पान सोडून) - निवडलेलं शेवटचं पान
        // मूळ शेवटचं नसेल तर PDF मध्ये रिकामं पान येऊ नये
        if (!rp && r.to < r.total) {
            var kept = doc.querySelectorAll(unit);
            if (kept.length) kept[kept.length - 1].style.pageBreakAfter = 'auto';
        }
        var imgs = doc.querySelectorAll('img[data-src]');
        for (var j = 0; j < imgs.length; j++) {
            imgs[j].setAttribute('src', imgs[j].getAttribute('data-src'));
            imgs[j].removeAttribute('data-src');
        }
        return '<!DOCTYPE html>\n' + doc.documentElement.outerHTML;
    }

    function share(btn) {
        if (btn.disabled) return;
        btn.disabled = true;
        btn.textContent = BUSY_LABEL;
        btn.style.opacity = '0.7';
        function done() {
            btn.disabled = false;
            btn.textContent = LABEL;
            btn.style.opacity = '';
        }

        var html;
        try {
            html = selectedPagesHtml();
        } catch (e) {
            if (window.console) console.error('share: From..To', e);
            html = null;
        }
        if (!html) html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/reports/share-pdf');
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.responseType = 'blob';
        xhr.onload = function () {
            done();
            if (xhr.status === 200) download(xhr.response);
            else showError(xhr);
        };
        xhr.onerror = function () {
            done();
            alert('PDF \u092c\u0928\u0935\u0924\u093e\u0928\u093e \u0924\u094d\u0930\u0941\u091f\u0940 \u0906\u0932\u0940 - backend \u091a\u093e\u0932\u0942 \u0906\u0939\u0947 \u0915\u093e \u0924\u0947 \u0924\u092a\u093e\u0938\u093e.');  // PDF बनवताना त्रुटी आली - backend चालू आहे का ते तपासा.
        };
        xhr.send(JSON.stringify({ html: html, title: document.title }));
    }

    function findPrintButton(toolbar) {
        var buttons = toolbar.getElementsByTagName('button');
        for (var i = 0; i < buttons.length; i++) {
            var onclick = buttons[i].getAttribute('onclick') || '';
            if (/print/i.test(onclick) || /^\s*print\s*$/i.test(buttons[i].textContent)) return buttons[i];
        }
        return null;
    }

    function addButton() {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'report-share-btn';
        btn.textContent = LABEL;
        btn.title = '\u0930\u093f\u092a\u094b\u0930\u094d\u091f\u091a\u0940 PDF Downloads \u092e\u0927\u094d\u092f\u0947 \u0938\u0947\u0935\u094d\u0939 \u0915\u0930\u093e - WhatsApp/\u0908\u092e\u0947\u0932 \u0928\u0947 \u092a\u093e\u0920\u0935\u0923\u094d\u092f\u093e\u0938\u093e\u0920\u0940';  // रिपोर्टची PDF Downloads मध्ये सेव्ह करा - WhatsApp/ईमेल ने पाठवण्यासाठी
        btn.onclick = function () { share(btn); };

        var toolbar = document.getElementById('toolbar');
        var printBtn = toolbar ? findPrintButton(toolbar) : null;
        if (printBtn) {
            // Print बटणासारखाच दिसावा, फक्त रंग वेगळा
            btn.style.cssText = printBtn.style.cssText;
            btn.style.background = '#1565c0';
            btn.style.whiteSpace = 'nowrap';
            btn.style.marginLeft = '8px';
            printBtn.parentNode.insertBefore(btn, printBtn.nextSibling);
        } else {
            btn.style.cssText = 'position:fixed; top:8px; right:12px; z-index:9999; background:#1565c0; color:#fff;' +
                ' font-weight:bold; font-size:16px; border:none; border-radius:20px; padding:4px 20px; cursor:pointer;' +
                ' box-shadow:0 2px 6px rgba(0,0,0,0.3);';
            if (toolbar) toolbar.appendChild(btn);
            else document.body.appendChild(btn);
        }
    }

    if (document.body) addButton();
    else document.addEventListener('DOMContentLoaded', addButton);
})();
