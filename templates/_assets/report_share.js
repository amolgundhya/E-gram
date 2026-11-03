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

        var html = '<!DOCTYPE html>\n' + document.documentElement.outerHTML;
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
