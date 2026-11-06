import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
router = APIRouter()

@router.get("/output.html")
def serve_output_html():
    home_path = os.path.expanduser("~")
    file_path = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports', 'output.html')
    print('file_path ---->' , file_path)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="text/html")
    return {"error": "File not found"}


# ---------- Share (PDF) - प्रत्येक रिपोर्ट viewer मधलं "Share (PDF)" बटण (templates/_assets/report_share.js) ----------
# viewer आपला HTML पाठवतो; तो संगणकावरच्या Chrome/Edge ने headless मोडमध्ये PDF करतो. मराठी अक्षरं
# ब्राउझरच छापतो म्हणून बरोबर येतात, आणि Windows 8 (Chrome/Edge 109) व Windows 10 दोन्हीवर चालतं.

# viewer मध्ये एका वेळी एकच पान दिसतं (बाकीचे display:none) - PDF मध्ये सगळी पानं हवीत.
_SHARE_PREP_SCRIPT = """<script>
(function () {
    window.print = function () {};  /* काही रिपोर्ट उघडताच print() करतात - PDF बनवताना dialog नको */
    var SEL = '.record-row, .print-page, .record-page, .outer-border, .record-table-wrapper';
    function revealAll() {
        var els = document.querySelectorAll(SEL);
        for (var i = 0; i < els.length; i++) els[i].style.display = '';
        var zoomed = document.querySelectorAll('#mainContent, .outer-border');
        for (var j = 0; j < zoomed.length; j++) zoomed[j].style.zoom = '';
    }
    window.addEventListener('beforeprint', revealAll);
    window.addEventListener('load', function () { setTimeout(revealAll, 0); });
})();
</script>"""

_BROWSER_PATHS = [
    (os.environ.get('ProgramFiles', r'C:\Program Files'), r'Google\Chrome\Application\chrome.exe'),
    (os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), r'Google\Chrome\Application\chrome.exe'),
    (os.environ.get('LOCALAPPDATA', ''), r'Google\Chrome\Application\chrome.exe'),
    (os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'), r'Microsoft\Edge\Application\msedge.exe'),
    (os.environ.get('ProgramFiles', r'C:\Program Files'), r'Microsoft\Edge\Application\msedge.exe'),
]


def _find_browser():
    override = os.environ.get('REPORT_PDF_BROWSER')
    if override and os.path.exists(override):
        return override
    for base, rel in _BROWSER_PATHS:
        if base and os.path.exists(os.path.join(base, rel)):
            return os.path.join(base, rel)
    return shutil.which('chrome') or shutil.which('msedge')


class SharePdfRequest(BaseModel):
    html: str
    title: Optional[str] = None


@router.post("/share-pdf")
def share_report_pdf(data: SharePdfRequest, request: Request):
    browser = _find_browser()
    if not browser:
        raise HTTPException(status_code=500, detail="PDF बनवण्यासाठी Google Chrome किंवा Microsoft Edge सापडला नाही.")

    # temp फाईल file:// वरून उघडते - /uploaded_images, /report_assets वगैरे localhost वरूनच यावेत
    head = '<base href="' + str(request.base_url) + '">' + _SHARE_PREP_SCRIPT
    html = data.html
    match = re.search(r'<head[^>]*>', html, re.IGNORECASE)
    html = html[:match.end()] + head + html[match.end():] if match else head + html

    work_dir = tempfile.mkdtemp(prefix='report_pdf_')
    try:
        html_path = os.path.join(work_dir, 'report.html')
        pdf_path = os.path.join(work_dir, 'report.pdf')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        cmd = [
            browser, '--headless', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
            # वापरकर्त्याचं Chrome उघडं असलं तरी वेगळा profile - नाहीतर तेच session वापरून PDF होत नाही
            '--user-data-dir=' + os.path.join(work_dir, 'profile'),
            '--no-pdf-header-footer', '--print-to-pdf-no-header',  # नवीन व जुन्या (109) Chrome साठी
            '--run-all-compositor-stages-before-draw', '--virtual-time-budget=20000',
            '--print-to-pdf=' + pdf_path,
            Path(html_path).as_uri(),
        ]
        creationflags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=600, creationflags=creationflags)
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=500, detail="PDF बनवायला खूप वेळ लागला - कमी पानं निवडून पुन्हा प्रयत्न करा.")
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise HTTPException(status_code=500, detail="PDF तयार झाली नाही.")
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
    finally:
        # Chrome फाईल लगेच सोडत नाही - थोडं थांबून काढतो, न निघाली तरी चालेल (temp फोल्डर)
        for _ in range(5):
            shutil.rmtree(work_dir, ignore_errors=True)
            if not os.path.exists(work_dir):
                break
            time.sleep(0.5)

    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="report.pdf"'})
