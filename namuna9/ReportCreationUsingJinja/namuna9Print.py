from jinja2 import Environment, FileSystemLoader
import os
import requests
from fastapi import APIRouter , Request
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()
# Load templates from the 'templates' folder (adjust path as needed)
# Init environment
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(base_dir, 'templates')
template_dir = os.path.join(template_dir ,'Namuna9' )
namuna9_template_regualar_dir = os.path.join(template_dir ,'Regular' )
namuna9_template_sutsaha_dir = os.path.join(template_dir ,'Sut Saha' )
namuna9_template_viseshpani_dir = os.path.join(template_dir ,'Vishesh Pani' )
namuna9_template_viseshpaniSafai_dir = os.path.join(template_dir ,'VisheshPani with Safai Tax' )
home_path = os.path.expanduser("~")

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
regularEnv = Environment(loader=FileSystemLoader(namuna9_template_regualar_dir))
SutSahaEnv = Environment(loader=FileSystemLoader(namuna9_template_sutsaha_dir))
visheshPaniEnv = Environment(loader=FileSystemLoader(namuna9_template_viseshpani_dir))
visheshPaniSafaiEnv = Environment(loader=FileSystemLoader(namuna9_template_viseshpaniSafai_dir))

# --- Marathi number-to-words, for "रक्कम अक्षरी" on receipts ---
_MARATHI_ONES = ["शून्य", "एक", "दोन", "तीन", "चार", "पाच", "सहा", "सात", "आठ", "नऊ"]
_MARATHI_TWO_DIGIT = {
    0: "", 1: "एक", 2: "दोन", 3: "तीन", 4: "चार", 5: "पाच", 6: "सहा", 7: "सात", 8: "आठ", 9: "नऊ",
    10: "दहा", 11: "अकरा", 12: "बारा", 13: "तेरा", 14: "चौदा", 15: "पंधरा", 16: "सोळा", 17: "सतरा", 18: "अठरा", 19: "एकोणीस",
    20: "वीस", 21: "एकवीस", 22: "बावीस", 23: "तेवीस", 24: "चोवीस", 25: "पंचवीस", 26: "सव्वीस", 27: "सत्तावीस", 28: "अठ्ठावीस", 29: "एकोणतीस",
    30: "तीस", 31: "एकतीस", 32: "बत्तीस", 33: "तेहतीस", 34: "चौतीस", 35: "पस्तीस", 36: "छत्तीस", 37: "सदतीस", 38: "अडतीस", 39: "एकोणचाळीस",
    40: "चाळीस", 41: "एक्केचाळीस", 42: "बेचाळीस", 43: "त्रेचाळीस", 44: "चव्वेचाळीस", 45: "पंचेचाळीस", 46: "सेहेचाळीस", 47: "सत्तेचाळीस", 48: "अठ्ठेचाळीस", 49: "एकोणपन्नास",
    50: "पन्नास", 51: "एक्कावन्न", 52: "बावन्न", 53: "त्रेपन्न", 54: "चोपन्न", 55: "पंचावन्न", 56: "छप्पन्न", 57: "सत्तावन्न", 58: "अठ्ठावन्न", 59: "एकोणसाठ",
    60: "साठ", 61: "एकसष्ठ", 62: "बासष्ठ", 63: "त्रेसष्ठ", 64: "चौसष्ठ", 65: "पासष्ठ", 66: "सहासष्ठ", 67: "सदुसष्ठ", 68: "अडुसष्ठ", 69: "एकोणसत्तर",
    70: "सत्तर", 71: "एक्काहत्तर", 72: "बहात्तर", 73: "त्र्याहत्तर", 74: "चौर्‍याहत्तर", 75: "पंच्याहत्तर", 76: "शहात्तर", 77: "सत्याहत्तर", 78: "अठ्ठ्याहत्तर", 79: "एकोणऐंशी",
    80: "ऐंशी", 81: "एक्क्याऐंशी", 82: "ब्याऐंशी", 83: "त्र्याऐंशी", 84: "चौऱ्याऐंशी", 85: "पंच्याऐंशी", 86: "शहाऐंशी", 87: "सत्त्याऐंशी", 88: "अठ्ठ्याऐंशी", 89: "एकोणनव्वद",
    90: "नव्वद", 91: "एक्क्याण्णव", 92: "ब्याण्णव", 93: "त्र्याण्णव", 94: "चौऱ्याण्णव", 95: "पंच्याण्णव", 96: "शहाण्णव", 97: "सत्त्याण्णव", 98: "अठ्ठ्याण्णव", 99: "नव्याण्णव",
}

def number_to_marathi_words(value) -> str:
    """Best-effort Marathi number-to-words for whole rupee amounts. Some of the
    40s-90s two-digit words have regional spelling variants that may not exactly
    match what's expected - flag any mismatch and it can be corrected here."""
    try:
        n = int(round(float(value or 0)))
    except (TypeError, ValueError):
        return ""
    if n == 0:
        return "शून्य"
    if n == 100:
        return "शंभर"
    if n < 0:
        return "उणे " + number_to_marathi_words(-n)

    parts = []
    crore, n = divmod(n, 10000000)
    lakh, n = divmod(n, 100000)
    thousand, n = divmod(n, 1000)
    hundred, remainder = divmod(n, 100)

    if crore:
        parts.append(_MARATHI_TWO_DIGIT.get(crore, str(crore)) + " कोटी")
    if lakh:
        parts.append(_MARATHI_TWO_DIGIT.get(lakh, str(lakh)) + " लाख")
    if thousand:
        parts.append(_MARATHI_TWO_DIGIT.get(thousand, str(thousand)) + " हजार")
    if hundred:
        parts.append(_MARATHI_ONES[hundred] + "शे")
    if remainder:
        parts.append(_MARATHI_TWO_DIGIT[remainder])

    return " ".join(parts)

regularEnv.filters['marathi_words'] = number_to_marathi_words

# Shows a blank cell instead of "0" when the "0 असल्यास रिकामे दाखवा" print
# setting is on. Only blanks an actual zero value - leaves real amounts,
# including negative ones, untouched. Off (or any other value) shows the
# number exactly as before.
def blank_if_zero(value, enabled='false'):
    if enabled != 'true':
        return value
    try:
        if value is None:
            return ''
        if float(value) == 0:
            return ''
    except (TypeError, ValueError):
        pass
    return value

regularEnv.filters['blankzero'] = blank_if_zero

localhost = "http://127.0.0.1:8000"


async def _get_checklist_page_number(gram_panchayat_id):
    """पेज नंबर - Master Settings मधल्या "टिप" सारखाच कायमस्वरूपी checklist toggle
    (namuna8 प्रमाणेच), प्रत्येक प्रिंटच्या वेळी वेगळं टिक करायची गरज नाही."""
    if not gram_panchayat_id:
        return 'false'
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f'{localhost}/namuna8/settings/checklist/get/{gram_panchayat_id}')
        if resp.status_code == 200:
            return 'true' if resp.json().get('pageNumber') else 'false'
    except Exception:
        pass
    return 'false'


@router.api_route('/namuna10hishob/byVillageID', methods=['POST','GET'])
async def namuna10_hishob_by_village(request: Request):
    try:
        # Load template
        requestData = await (request.json() if request.method == 'POST' else request.query_params)
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        receipt_id = requestData.get("receipt_id")
        template = Environment(loader=FileSystemLoader(os.path.join(base_dir, 'templates','Namuna10'))).get_template('vasuliHishob.html')

        # Call API - use receipt-specific endpoint if receipt_id is provided
        async with httpx.AsyncClient() as client:
            # Fetch one or more receipts; if receipt_id provided use single-id endpoint, else use by-date village (expects dates in request)
            from_date = requestData.get('from_date') or requestData.get('startDate')
            to_date = requestData.get('to_date') or requestData.get('endDate')
            show_all = requestData.get('showAll') in (True, 'true', 'True', '1', 1)
            if receipt_id:
                response = await client.get(f'{localhost}/namuna9/receipt/{receipt_id}', params={"gram_panchayat_id": gram_panchayat_id})
            elif show_all or not villageId:
                # All villages within GP
                response = await client.get(
                    f'{localhost}/namuna9/receipts/by-date-all',
                    params={
                        "gram_panchayat_id": gram_panchayat_id,
                        "from_date": from_date,
                        "to_date": to_date,
                    },timeout=300.0
                )
            else:
                response = await client.get(
                    f'{localhost}/namuna9/receipts/by-date-village',
                    params={
                        "gram_panchayat_id": gram_panchayat_id,
                        "village_id": villageId,
                        "from_date": from_date,
                        "to_date": to_date,
                    }
                )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Normalize to list
        records = data if isinstance(data, list) else [data]
        # Prepare context for vasuliHishob.html
        context = {
            "village": requestData.get("villageName", ""),
            "stateDate": from_date or "",
            "endDate": to_date or "",
            "currentDate": requestData.get("currentDate", ""),
            "rows": records,
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Receipt output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )


@router.post('/namuna9receipt')
async def namuna9receipt(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        receipt_id = requestData.get("receipt_id")
        template = regularEnv.get_template('namuna9receipt.html')

        # Call API - use receipt-specific endpoint if receipt_id is provided
        async with httpx.AsyncClient() as client:
            if receipt_id:
                # Get specific receipt data
                response = await client.get(
                    f'{localhost}/namuna9/receipt/{receipt_id}',
                     params={
                        "villageId": villageId,
                        "yearslap": year,
                        "district_id": district_id,
                        "taluka_id": taluka_id,
                        "gram_panchayat_id": gram_panchayat_id,
                    }
                )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template with raw data - let template handle formatting
        if not isinstance(data, list):
            data = [data]
        
        # For receipt-specific data, we expect a single record
        if receipt_id and len(data) > 0:
            record = data[0]  # Get the first (and should be only) record
        else:
            record = data[0] if data else {}  # Fallback to first record or empty
        
        context = {
            'record': record,  # Pass single record to template
            'data': data,      # Keep original data array for compatibility
            'receipt_id': receipt_id,
            'noticeFee': requestData.get('noticeFee', 'true'),
            'warrantFee': requestData.get('warrantFee', 'true'),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Receipt output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/regular/namuna9All')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9All.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]

        # घर कर / पाणी कर Bank Scanner - only fetched/shown if the GP has
        # turned this on in Master settings.
        showBankScanner = False
        houseTaxQrUrl = None
        waterTaxQrUrl = None
        if gram_panchayat_id:
            try:
                gp_base_url = str(request.base_url).rstrip('/')
                async with httpx.AsyncClient() as client:
                    gp_resp = await client.get(f'{gp_base_url}/location/gram-panchayats/{gram_panchayat_id}')
                if gp_resp.status_code == 200:
                    gp_data = gp_resp.json()
                    showBankScanner = bool(gp_data.get('show_bank_scanner_in_reports'))
                    if gp_data.get('house_tax_qr_url'):
                        houseTaxQrUrl = f'{gp_base_url}/location/gram-panchayats/{gram_panchayat_id}/qr/house'
                    if gp_data.get('water_tax_qr_url'):
                        waterTaxQrUrl = f'{gp_base_url}/location/gram-panchayats/{gram_panchayat_id}/qr/water'
            except Exception:
                pass

        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
            'blankZero': requestData.get('blankZero', ''),
            'showBankScanner': showBankScanner,
            'houseTaxQrUrl': houseTaxQrUrl,
            'waterTaxQrUrl': waterTaxQrUrl,
        }
        rendered_html = template.render(**context)

        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/regular/namuna9AllPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9AllPG2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
            'blankZero': requestData.get('blankZero', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9Gen')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9Gen.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9GenPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9GenPG2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
    
@router.post('/regular/namuna9Pani')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9Pani.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9PaniPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9PaniPG2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9Vasuli1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9Vasuli1.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
            'blankZero': requestData.get('blankZero', ''),
        }
        rendered_html = template.render(**context)

        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/regular/namuna9Vasuli2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9Vasuli2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
            'blankZero': requestData.get('blankZero', ''),
        }
        rendered_html = template.render(**context)

        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/regular/namuna9Vasuli3')
async def prakar1(request: Request):
    try:
        requestData = await request.json()
        villageId = requestData.get('villageID')
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9Vasuli3.html')
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")
        data = response.json()
        if not isinstance(data, list):
            data = [data]
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
            'blankZero': requestData.get('blankZero', ''),
        }
        rendered_html = template.render(**context)
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        return JSONResponse(status_code=200, content={"success": True, "message": "Output file is created", "data": {}})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "message": f"Error: {str(e)}", "data": {}})
    
@router.post('/regular/namuna9k')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9k.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/regular/',params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9k2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9k2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/regular/' , params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/regular/namuna9lekh')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9lekh.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/regular/', params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]

        # Derive the notice's "from"/"to" dates from the selected financial
        # year (e.g. "2025-2026" -> 01/04/2025 to 31/03/2026).
        noticeYearFrom = ''
        noticeYearTo = ''
        try:
            yr_start, yr_end = (year or '').split('-')
            noticeYearFrom = f"01/04/{int(yr_start)}"
            noticeYearTo = f"31/03/{int(yr_end)}"
        except (ValueError, AttributeError):
            pass

        # लेखाबाद्दलची फी comes from the Namuna9 Master setting (नोटीस फी).
        lekhFee = ''
        try:
            async with httpx.AsyncClient() as settings_client:
                settings_response = await settings_client.get(
                    f'{localhost}/namuna9/settings/{gram_panchayat_id}', timeout=30.0
                )
            if settings_response.status_code == 200:
                lekhFee = settings_response.json().get('notice_fee', '')
        except Exception:
            pass

        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'noticeYearFrom': noticeYearFrom,
            'noticeYearTo': noticeYearTo,
            'lekhFee': lekhFee,
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)

        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/regular/namuna9lekh2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = regularEnv.get_template('namuna9lekh2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/regular/' , params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
    
@router.post('/sutsaha/namuna9All')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = SutSahaEnv.get_template('namuna9AllSutSaha.html')

        # Call API
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/sutsaha/namuna9Gen')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = SutSahaEnv.get_template('namuna9GenSutSaha.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9All')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9AllVisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9AllPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9AllPG2VisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9Gen')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9GenVisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9GenPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9GenPG2VisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9Pani')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9PaniVisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/visheshPani/namuna9PaniPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9PaniPG2VisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPani/namuna9Vasuli1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9Vasuli1VisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )

@router.post('/visheshPani/namuna9Vasuli2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9Vasuli2VisheshPain.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshpani/namuna9k')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9kVisheshPani.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/visheshpani/' , params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'tax_names' : ['घरकर', 'दिवाबत्ती कर', 'आरोग्य कर', 'सा.पाणीकर', 'वि.पाणीकर', 'नोटीस फी', 'वारंट फी'],
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshpani/namuna9k2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniEnv.get_template('namuna9k2VisheshPani.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village/visheshpani/' 
            , params={
            "villageId": villageId,
            "yearslap": year,
            "district_id": district_id,
            "taluka_id": taluka_id,
            "gram_panchayat_id": gram_panchayat_id
        },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'tax_names' : ['घरकर', 'दिवाबत्ती कर', 'आरोग्य कर', 'सा.पाणीकर', 'वि.पाणीकर', 'नोटीस फी', 'वारंट फी'],
            "warrantFee" : requestData.get('warrantFee', ''),
            "noticeFee" : requestData.get('noticeFee', ''),
            "dandLava" : requestData.get('dandLava', ''),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9All')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9AllVisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9AllPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9AllPG2VisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    } ,timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9Gen')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9GenVisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9GenPG2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9GenPG2VisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(
    f'{localhost}/namuna9/recordresponses/property_records_by_village',
    params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0
)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9Vasuli1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9Vasuli1VisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village' , params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        
        data = response.json()
        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
        
@router.post('/visheshPaniSafai/namuna9Vasuli2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        year = requestData.get("year")
        template = visheshPaniSafaiEnv.get_template('namuna9Vasuli2VisheshPaniSafai.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna9/recordresponses/property_records_by_village' , params={
        "villageId": villageId,
        "yearslap": year,
        "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
    },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            'removeDhakit': requestData.get('removeDhakit', ''),
            'removeChalu': requestData.get('removeChalu', ''),
            'removeYekun': requestData.get('removeYekun', ''),
            'removePurnaYekun': requestData.get('removePurnaYekun', ''),
            'removePaniZero': requestData.get('removePaniZero', ''),
            'removeZeroTax': requestData.get('removeZeroTax', ''),
            'totalPrint': requestData.get('totalPrint', ''),
            'namuna9Based': requestData.get('namuna9Based', ''),
            'selectedVillage': requestData.get('selectedVillage', ''),
            'selectedYear': requestData.get('selectedYear', ''),
            'villageID': requestData.get('villageID', ''),
            'year': requestData.get('year', ''),
            'pageNumber': await _get_checklist_page_number(gram_panchayat_id),
        }
        rendered_html = template.render(**context)
        
        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )