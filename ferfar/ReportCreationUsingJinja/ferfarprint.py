from jinja2 import Environment, FileSystemLoader
import os
import csv
import io
import requests
from fastapi import APIRouter , Request
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

router = APIRouter()
# Load templates from the 'templates' folder (adjust path as needed)
# Init environment
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(base_dir, 'templates')
ferfar_template_dir = os.path.join(template_dir ,'ferfar' )
home_path = os.path.expanduser("~")

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
env = Environment(loader=FileSystemLoader(ferfar_template_dir))

localhost = "http://127.0.0.1:8000"


@router.post('/prakar1')
async def prakar1(request : Request):
    try:
        template = env.get_template('registerPrakar1.html')
        requestData = await request.json()
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        print(district_id , taluka_id , gram_panchayat_id)

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/ferfar/recordresponses' , params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id},timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # data = {
        #     "village": 'nanded',
        #     "gramPanchayat": 'vadi',
        #     "jilha": 'nanded',
        #     "taluk": 'nanded',
        #     "2": [
        #         {
        #             "entry_number": "",
        #             "village": "गट नं 1",
        #             "transaction_date": "30/07/2025",
        #             "roadName": "",
        #             "propertyNumber": "2",
        #             "propertyDescription": "क्षेत्र: 10000.0 चौ.फूट",
        #             "previousOwnerName": "Aditya hhjhfjhfj",
        #             "currentOwnerName": "Kalyan",
        #             "modification_reference_remarks": "sample ",
        #             "assessment_register_entry_details": "sample"
        #         }
        #     ],
        #     "1": [
        #         {
        #             "entry_number": "",
        #             "village": "गट नं 1",
        #             "transaction_date": "30/07/2025",
        #             "roadName": "",
        #             "propertyNumber": "1",
        #             "propertyDescription": "क्षेत्र: 10000.0 चौ.फूट",
        #             "previousOwnerName": "sdsadasdsadsad",
        #             "currentOwnerName": "Aditya",
        #             "modification_reference_remarks": "sample",
        #             "assessment_register_entry_details": "normally"
        #         }
        #     ]
        # }

        # Render template
        context = {
            'data': data
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
async def prakar1(request : Request):
    try:
        template = env.get_template('registerPrakar2.html')
        requestData = await request.json()
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/ferfar/recordresponses', params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id },timeout=300.0)
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # data = {
        #     "village": 'nanded',
        #     "gramPanchayat": 'vadi',
        #     "jilha": 'nanded',
        #     "taluk": 'nanded',
        #     "2": [
        #         {
        #             "entry_number": "",
        #             "village": "गट नं 1",
        #             "transaction_date": "30/07/2025",
        #             "roadName": "",
        #             "propertyNumber": "2",
        #             "propertyDescription": "क्षेत्र: 10000.0 चौ.फूट",
        #             "previousOwnerName": "Aditya hhjhfjhfj",
        #             "currentOwnerName": "Kalyan",
        #             "modification_reference_remarks": "sample ",
        #             "assessment_register_entry_details": "sample"
        #         }
        #     ],
        #     "1": [
        #         {
        #             "entry_number": "",
        #             "village": "गट नं 1",
        #             "transaction_date": "30/07/2025",
        #             "roadName": "",
        #             "propertyNumber": "1",
        #             "propertyDescription": "क्षेत्र: 10000.0 चौ.फूट",
        #             "previousOwnerName": "sdsadasdsadsad",
        #             "currentOwnerName": "Aditya",
        #             "modification_reference_remarks": "sample",
        #             "assessment_register_entry_details": "normally"
        #         }
        #     ]
        # }

        # Render template
        context = {
            'data': data
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

@router.post('/prakar1_csv')
async def prakar1_csv(request: Request):
    """फेरफार रजिस्टर (Property Transfer Register) data as a downloadable CSV."""
    try:
        requestData = await request.json()
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")

        base_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'{base_url}/ferfar/recordresponses',
                params={"district_id": district_id, "taluka_id": taluka_id, "gram_panchayat_id": gram_panchayat_id},
                timeout=300.0,
            )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Response is a dict: metadata keys (village/gramPanchayat/jilha/taluk) plus
        # one list of transfer entries per property number - flatten into one table.
        meta_keys = {"village", "gramPanchayat", "jilha", "taluk"}
        rows = []
        for key, value in data.items():
            if key in meta_keys or not isinstance(value, list):
                continue
            rows.extend(value)

        columns = [
            ("entry_number", "नोंद क्रमांक"),
            ("transaction_date", "व्यवहार दिनांक"),
            ("propertyNumber", "मालमत्ता क्रमांक"),
            ("propertyDescription", "मालमत्तेचे वर्णन"),
            ("previousOwnerName", "मागील मालकाचे नाव"),
            ("currentOwnerName", "सध्याच्या मालकाचे नाव"),
            ("modification_reference_remarks", "फेरफार संदर्भ शेरा"),
            ("assessment_register_entry_details", "आकारणी नोंद तपशील"),
        ]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow([label for _, label in columns])
        for row in rows:
            writer.writerow([row.get(key, "") for key, _ in columns])

        csv_bytes = io.BytesIO(buffer.getvalue().encode("utf-8-sig"))
        return StreamingResponse(
            csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="ferfar_register.csv"'},
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
