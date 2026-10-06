from jinja2 import Environment, FileSystemLoader
import os
import csv
import io
import requests
from fastapi import APIRouter , Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
import httpx
import database
from namuna8 import namuna8_model as models
from Yadi.ReportCreationUsingJinja.yadi_xlsx_export import build_namuna8_register_workbook, workbook_to_bytes
router = APIRouter()
# Load templates from the 'templates' folder (adjust path as needed)
# Init environment
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(base_dir, 'templates')
namuna8_template_dir = os.path.join(template_dir ,'Yadi' )
home_path = os.path.expanduser("~")

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
env = Environment(loader=FileSystemLoader(namuna8_template_dir))

localhost = "http://127.0.0.1:8000"

@router.post('/verticalreport')
async def verticalreport(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('yadivertical.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_records_by_village/{villageId}',
            params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id},timeout=300.0)
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
            'totalCount': len(data),
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


@router.post('/verticalreport_csv')
async def verticalreport_csv(request: Request):
    """All Report data as a downloadable CSV (opens directly in Excel)."""
    try:
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")

        base_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}',
                params={"district_id": district_id, "taluka_id": taluka_id, "gram_panchayat_id": gram_panchayat_id},
                timeout=300.0,
            )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        if not isinstance(data, list):
            data = [data]

        columns = [
            ("srNo", "अ.क्र."),
            ("propertyNumber", "मालमत्ता क्रमांक"),
            ("ownerName", "मालमत्ता धारकाचे नाव"),
            ("occupantName", "भोगवटदाराचे नाव"),
            ("village", "गाव"),
            ("mobileNumber", "मोबाईल क्रमांक"),
            ("total_arearinfoot", "एकूण क्षेत्रफळ (चौ.फु.)"),
            ("totalareainmeters", "एकूण क्षेत्रफळ (चौ.मी.)"),
            ("totalCapitalValue", "भांडवली मूल्य"),
            ("totalHouseTax", "घरपट्टी"),
        ]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([label for _, label in columns])
        for row in data:
            writer.writerow([row.get(key, "") for key, _ in columns])

        # utf-8-sig BOM so Excel renders Marathi/Devanagari text correctly
        csv_bytes = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
        filename = f"all_report_{villageId}.csv"
        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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


@router.post('/verticalreport_xlsx')
async def verticalreport_xlsx(request: Request, db: Session = Depends(database.get_db)):
    """All Report data as a real .xlsx (2 sheets, formatted, optionally password-protected)."""
    try:
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")

        base_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}',
                params={"district_id": district_id, "taluka_id": taluka_id, "gram_panchayat_id": gram_panchayat_id},
                timeout=300.0,
            )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        if not isinstance(data, list):
            data = [data]

        # Master मध्ये सेट केलेला export पासवर्ड (गाव पंचायतीनुसार) - नसेल तर पासवर्डशिवाय export.
        password = None
        if gram_panchayat_id:
            checklist = db.query(models.Namuna8SettingChecklist).filter(
                models.Namuna8SettingChecklist.gram_panchayat_id == gram_panchayat_id
            ).first()
            if checklist and getattr(checklist, 'exportPassword', None):
                password = checklist.exportPassword

        wb = build_namuna8_register_workbook(data)
        xlsx_bytes = workbook_to_bytes(wb, password=password)

        filename = f"namuna8_register_{villageId}.xlsx"
        return StreamingResponse(
            io.BytesIO(xlsx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
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


@router.post('/horizontalReport')
async def verticalreport(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('yadihorizontal.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_records_by_village/{villageId}',
            params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id},timeout=300.0)
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
            'totalCount': len(data),
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
        
@router.post('/prakar1')
async def verticalreport(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('yadiprakar1.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_records_by_village/{villageId}',
        params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id},timeout=300.0)
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
            'totalCount': len(data),
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
        
@router.post('/prakar2')
async def verticalreport(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('yadiprakar2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_records_by_village/{villageId}',
        params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id},timeout=300.0)
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
            'totalCount': len(data),
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