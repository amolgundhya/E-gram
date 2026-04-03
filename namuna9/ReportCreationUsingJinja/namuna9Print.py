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

localhost = "http://127.0.0.1:8000"


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
                    }
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
    },timeout=30.0
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
    }, timeout=300.0
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
    },timeout=30.0
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
    }, timeout=300.0
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
    },timeout= 30.0
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
    },timeout = 300.0
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
    }
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