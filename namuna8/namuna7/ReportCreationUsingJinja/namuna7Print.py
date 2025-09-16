from jinja2 import Environment, FileSystemLoader
import os
import requests
from fastapi import APIRouter , Request
from fastapi.responses import JSONResponse
import httpx

router = APIRouter()
# Load templates from the 'templates' folder (adjust path as needed)
# Init environment
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..' ,'..'))

template_dir = os.path.join(base_dir, 'templates')

namuna7_template_dir = os.path.join(template_dir ,'Namuna7' )


home_path = os.path.expanduser("~")

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
env = Environment(loader=FileSystemLoader(namuna7_template_dir))

# API base URL
localhost = "http://127.0.0.1:8000"


@router.post('/receipt')
async def receipt(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userId")
        template = env.get_template('namuna7Pavati.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna7/prints/get/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        # Debug print the response text
       

        # Check for empty or invalid JSON response
        if not response.text.strip():
            raise Exception("API returned empty response")
        try:
            data = response.json()
        except Exception as e:
            raise Exception(f"API did not return valid JSON: {response.text}")

        # Render template
        rendered_html = template.render(data)

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
        
@router.post('/register')
async def receipt(request : Request):
    try:
        # Load template
        requestDate = await request.json()
        stateDate = requestDate.get("startDate")
        endDate = requestDate.get("endDate")
        district_id = requestDate.get("district_id")
        taluka_id = requestDate.get("taluka_id")
        gram_panchayat_id = requestDate.get("gram_panchayat_id")
        template = env.get_template('namuna7pavatiRegister.html')

        # Call API
        async with httpx.AsyncClient() as client:    
            response = await client.get(f'{localhost}/namuna7/getall_receipts?startdate={stateDate}&enddate={endDate}',
            params={
                "startdate" : stateDate,
                "enddate" : endDate,
                "district_id": district_id,
        "taluka_id": taluka_id,
        "gram_panchayat_id": gram_panchayat_id
            }
            )
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', '') if data else '',
            'village': data[0].get('village', '') if data else '',
            'taluka': data[0].get('taluka', '') if data else '',
            'jilha': data[0].get('jilha', '') if data else '',
            'yearFrom': data[0].get('yearFrom', '') if data else '',
            'yearTo': data[0].get('yearTo', '') if data else '',
            "startDate" : stateDate,
            "endDate" : endDate,
            "currentDate" : data[0].get('currentDate', '') if data else '',
        }

        # Render template
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
        
@router.post('/logbook/print')
async def receipt(request : Request):
    try:
        # Load template
        requestDate = await request.json()
        stateDate = requestDate.get("startDate")
        endDate = requestDate.get("endDate")
        template = env.get_template('printTemplate.html')
        
        # Call APIf
        async with httpx.AsyncClient() as client:    
            response = await client.get(f'{localhost}/outward-entries/date-range/?from_date={stateDate}&to_date={endDate}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")


        data = response.json()

        # Extract currentDate from response if available, else use today's date
        currentDate = None
        if isinstance(data, dict) and 'currentDate' in data:
            currentDate = data['currentDate']
        elif isinstance(data, list) and data and 'currentDate' in data[0]:
            currentDate = data[0]['currentDate']
        else:
            from datetime import datetime
            currentDate = datetime.now().strftime('%Y-%m-%d')

        # Render template
        rendered_html = template.render(
            data=data,
            startDate=stateDate,
            endDate=endDate,
            currentDate=currentDate
        )

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