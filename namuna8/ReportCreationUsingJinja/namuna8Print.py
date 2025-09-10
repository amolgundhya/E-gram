from jinja2 import Environment, FileSystemLoader
import os
import requests
from fastapi import APIRouter , Request
from fastapi.responses import JSONResponse
from Utility.QRcodeGeneration import QRCodeGeneration 
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
router = APIRouter()
# Load templates from the 'templates' folder (adjust path as needed)
# Init environment
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
template_dir = os.path.join(base_dir, 'templates')
namuna8_template_dir = os.path.join(template_dir ,'Namuna8' )
# static_dir = os.path.join(base_dir, 'reports')
env = Environment(loader=FileSystemLoader(namuna8_template_dir))

# # Get the user home directory
home_path = os.path.expanduser("~")
logs_path = os.path.expanduser("~")
logs_dir = os.path.join(logs_path, "logs")   # Create logs folder inside home
os.makedirs(logs_dir, exist_ok=True)

file_path = os.path.join(logs_dir, "logs.txt")  # Log file path

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')

# Create the full directory path if it doesn't exist
# os.makedirs(reports_path, exist_ok=True)  

# print("Reports folder created at:", reports_path)

# API base URL
localhost = "http://127.0.0.1:8000"


# @router.get("/reports/output.html")
# def serve_output_html():
#     home_path = os.path.expanduser("~")
#     file_path = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
#     print('file_path ---->' , file_path)
#     if os.path.exists(file_path):
#         return FileResponse(file_path, media_type="text/html")
#     return {"error": "File not found"}


@router.post('/prakar1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar1copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]    
        else:
            template = env.get_template('namuna8Prakar1.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar2copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]    
        else:
            template = env.get_template('namuna8Prakar2.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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

@router.post('/prakar3')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')

        if checkbox:
            template = env.get_template('namuna8Prakar3copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8Prakar3.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        
@router.post('/prakar4bhag1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        checkbox = requestData.get("checkbox")
        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar4bhag1copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  

        else:
            template = env.get_template('namuna8Prakar4bhag1.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        
@router.post('/prakar4bhag2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        
        checkbox = requestData.get("checkbox")
        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar4bhag2copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8Prakar4bhag2.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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

@router.post('/prakar5bhag1')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar5bhag1copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8Prakar5bhag1.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]                                                

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        
@router.post('/prakar5bhag2')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8Prakar5bhag2copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8Prakar5bhag2.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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

@router.post('/prakar1VisheshPani')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8VishehPaniPrakar1copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8VishehPaniPrakar1.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        
@router.post('/prakar2VisheshPani')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8VishehPaniPrakar2copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8VishehPaniPrakar2.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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
        
@router.post('/prakar3VisheshPani')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        checkbox = requestData.get("checkbox")

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        if checkbox:
            template = env.get_template('namuna8VishehPaniPrakar3copy.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_gram_panchayat/1' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id}
            )
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
            
            response = response.json()
            data = []

            for village_name , records in response.items():
                data.append({
                    "villageName" : village_name,
                    "records" : records
                })

            if not isinstance(data, list):
                data = [data]  
        else:
            template = env.get_template('namuna8VishehPaniPrakar3.html')
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
                params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")

            data = response.json()
            if not isinstance(data, list):
                data = [data]  

        if not data:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "message": "No records found for the given villageID.",
                    "data": {}
                }
            )

        # Render template
        if not isinstance(data, list):
            data = [data]
        # Extract top-level fields from the first record
        context = {
            'data': data,
            'gramPanchayat': data[0].get('gramPanchayat', ''),
            'village': data[0].get('village', ''),
            'taluka': data[0].get('taluka', ''),
            'jilha': data[0].get('jilha', ''),
            'yearFrom': data[0].get('yearFrom', ''),
            'yearTo': data[0].get('yearTo', ''),
            "tip" : data[0].get("tip" , "")
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

@router.post('/single_print')
async def singlePrint(request : Request):
    try:
        requestData = await request.json()
        anuKramank = requestData.get("anuKramank")
        villageID = requestData.get("villageID")
        
        # Load template
        template = env.get_template('singlePrint1.html')

        # Call API
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f'{localhost}/namuna8/recordresponses/property_record/{anuKramank}', params={
                    'district_id': requestData.get('district_id'),
                    'taluka_id': requestData.get('taluka_id'),
                    "village_id" : villageID,
                    'gram_panchayat_id': requestData.get('gram_panchayat_id')
                })
            if response.status_code != 200:
                raise Exception(f"API error {response.status_code}: {response.text}")
        except Exception as e:
           
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(str(e))

        data = response.json()
        QRdata = {
            "srNO" : data.get('srNo') or "",
            "TotalArea" : data.get('total_arearinfoot') or "",
            "Construction" : data.get('total_arearinfoot') or "",
            "OpenSpace" : data['khaliJaga'][0].get('totalkhalijagaareainfoot') if data.get('khaliJaga') and len(data['khaliJaga']) > 0 else "",
            "TotalTax" : data.get('totaltax') or ""
        }
        QRCodeGeneration.createQRcode(QRdata)
        

        # Render template
        rendered_html = template.render(data)

        # Save output.html
        os.makedirs(static_dir, exist_ok=True)
        output_path = os.path.join(static_dir, 'output.html')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(rendered_html)
            
        with open(file_path, "a", encoding="utf-8") as f:
            f.write("Reports are working well")

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Output file is created",
                "data": {}
            }
        )
        

    except Exception as e:
       
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(str(e))
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": f"Error: {str(e)}",
                "data": {}
            }
        )
    
@router.post('/single_printP1')
async def singlePrint(request : Request):
    try:
        requestData = await request.json()
        anuKramank = requestData.get("anuKramank")
        villageID = requestData.get("villageID")
        # Load template
        template = env.get_template('singlePrintP1.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_record/{anuKramank}', params={
                'district_id': requestData.get('district_id'),
                'taluka_id': requestData.get('taluka_id'),
                "village_id" : villageID,
                'gram_panchayat_id': requestData.get('gram_panchayat_id')
            })
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        QRdata = {
            "srNO" : data.get('srNo') or "",
            "TotalArea" : data.get('total_arearinfoot') or "",
            "Construction" : data.get('total_arearinfoot') or "",
            "OpenSpace" : data['khaliJaga'][0].get('totalkhalijagaareainfoot') if data.get('khaliJaga') and len(data['khaliJaga']) > 0 else "",
            "TotalTax" : data.get('totaltax') or ""
            
        }
        QRCodeGeneration.createQRcode(QRdata)

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
    
@router.post('/single_printP2')
async def singlePrint(request : Request):
    try:
        # Load template
        requestData = await request.json()
        anuKramank = requestData.get("anuKramank")
        villageID = requestData.get("villageID")
        template = env.get_template('singlePrintP2.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_record/{anuKramank}', params={
                'district_id': requestData.get('district_id'),
                'taluka_id': requestData.get('taluka_id'),
                "village_id" : villageID,
                'gram_panchayat_id': requestData.get('gram_panchayat_id')
            })
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        QRdata = {
            "srNO" : data.get('srNo') or "",
            "TotalArea" : data.get('total_arearinfoot') or "",
            "Construction" : data.get('total_arearinfoot') or "",
            "OpenSpace" : data['khaliJaga'][0].get('totalkhalijagaareainfoot') if data.get('khaliJaga') and len(data['khaliJaga']) > 0 else "",
            "TotalTax" : data.get('totaltax') or ""
            
        }
        QRCodeGeneration.createQRcode(QRdata)

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
    
@router.post('/single_print_range')
async def singlePrint(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('singlePrintRange.html')

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
            params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # data = [
        #             {
        #     "id": "1",
        #     "srNo": 1,
        #     "propertyNumber": "जरीचेवखडकाचे",
        #     "propertyDescription": "दगड सिमेंट चुना अर्ध पक्के घर, आर सी सी",
        #     "gramPanchayat": "गट नं 6",
        #     "village": "गट नं 6",
        #     "taluka": "null",
        #     "jilha": "null",
        #     "yearFrom": 2024,
        #     "yearTo": 2027,
        #     "photoURL": "null",
        #     "QRcodeURL": "null",
        #     "total_arearinfoot": 9879.0,
        #     "totalareainmeters": 917.79,
        #     "occupantName": "स्वत:",
        #     "aadharNumber": "",
        #     "ownerName": "श्री रामराव पि.तत्तवराव पावडे",
        #     "roadName": "",
        #     "cityWardGatNumber": "",
        #     "areaEast": 133.5,
        #     "areaWest": 133.5,
        #     "areaNorth": 74.5,
        #     "areaSouth": 73.5,
        #     "totalArea": 9879.0,
        #     "boundaryEast": "पांडुरंग बाबाराव",
        #     "boundaryWest": "रस्ता वि. द. शाळा",
        #     "boundaryNorth": "बाजरीचे व खडकाचे",
        #     "boundarySouth": " खडकाचे",
        #     "removeLightHealthTax": "true",
        #     "applyCleaningTax": "true",
        #     "applyToiletTax": "false",
        #     "taxNotApplicable": "false",
        #     "khaliJaga": [
        #         {
        #             "constructiontype": "खाली जागा",
        #             "length": 8538.0,
        #             "width": 1,
        #             "year": 2025,
        #             "rate": "null",
        #             "floor": "null",
        #             "usage": "null",
        #             "capitalValue": 541133,
        #             "houseTax": 0,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": "null",
        #             "totalkhalijagaareainfoot": 8538.0,
        #             "totalkhalijagaareainmeters": 793.21
        #         }
        #     ],
        #     "constructionType": [
        #         {
        #             "type": "दगड सिमेंट चुना अर्ध पक्के घर",
        #             "length": 494.0,
        #             "width": 1.0,
        #             "year": "1999",
        #             "rate": 14137.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 406,
        #             "depreciation_rate": 70,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 0.75
        #         },
        #         {
        #             "type": "आर सी सी",
        #             "length": 847.0,
        #             "width": 1.0,
        #             "year": "2005",
        #             "rate": 17424.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 541,
        #             "depreciation_rate": 75,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 1.0
        #         }
        #     ],
        #     "waterFacility1": "सामान्य पाणीकर",
        #     "waterFacility2": "सामान्य पाणीकर",
        #     "toilet": "आहे",
        #     "house": "आहे",
        #     "totalCapitalValue": 0,
        #     "totalHouseTax": 0,
        #     "housingUnit": "sqft",
        #     "lightingTax": 300,
        #     "healthTax": 300,
        #     "waterTax": 0,
        #     "cleaningTax": 300,
        #     "toiletTax": 0,
        #     "totaltax": 0,
        #     "userId": [
        #         2
        #     ],
        #     "villageId": "3",
        #     "creationAt": "2025-07-03T11:16:50.572730",
        #     "updationAt": "2025-07-03T11:16:50.572730"
        # },
        #             {
        #     "id": "1",
        #     "srNo": 1,
        #     "propertyNumber": "जरीचेवखडकाचे",
        #     "propertyDescription": "दगड सिमेंट चुना अर्ध पक्के घर, आर सी सी",
        #     "gramPanchayat": "गट नं 6",
        #     "village": "गट नं 6",
        #     "taluka": "null",
        #     "jilha": "null",
        #     "yearFrom": 2024,
        #     "yearTo": 2027,
        #     "photoURL": "null",
        #     "QRcodeURL": "null",
        #     "total_arearinfoot": 9879.0,
        #     "totalareainmeters": 917.79,
        #     "occupantName": "श्री रामराव पि.तत्तवराव पावडे"  ,
        #     "aadharNumber": "",
        #     "ownerName": "श्री रामराव पि.तत्तवराव पावडे",
        #     "roadName": "",
        #     "cityWardGatNumber": "",
        #     "areaEast": 133.5,
        #     "areaWest": 133.5,
        #     "areaNorth": 74.5,
        #     "areaSouth": 73.5,
        #     "totalArea": 9879.0,
        #     "boundaryEast": "पांडुरंग बाबाराव",
        #     "boundaryWest": "रस्ता वि. द. शाळा",
        #     "boundaryNorth": "बाजरीचे व खडकाचे",
        #     "boundarySouth": " खडकाचे",
        #     "removeLightHealthTax": "true",
        #     "applyCleaningTax": "true",
        #     "applyToiletTax": "false",
        #     "taxNotApplicable": "false",
        #     "khaliJaga": [
        #         {
        #             "constructiontype": "खाली जागा",
        #             "length": 8538.0,
        #             "width": 1,
        #             "year": 2025,
        #             "rate": "null",
        #             "floor": "null",
        #             "usage": "null",
        #             "capitalValue": 541133,
        #             "houseTax": 0,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": "null",
        #             "totalkhalijagaareainfoot": 8538.0,
        #             "totalkhalijagaareainmeters": 793.21
        #         }
        #     ],
        #     "constructionType": [
        #         {
        #             "type": "दगड सिमेंट चुना अर्ध पक्के घर",
        #             "length": 494.0,
        #             "width": 1.0,
        #             "year": "1999",
        #             "rate": 14137.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 406,
        #             "depreciation_rate": 70,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 0.75
        #         },
        #         {
        #             "type": "आर सी सी",
        #             "length": 847.0,
        #             "width": 1.0,
        #             "year": "2005",
        #             "rate": 17424.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 541,
        #             "depreciation_rate": 75,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 1.0
        #         }
        #     ],
        #     "waterFacility1": "सामान्य पाणीकर",
        #     "waterFacility2": "सामान्य पाणीकर",
        #     "toilet": "आहे",
        #     "house": "आहे",
        #     "totalCapitalValue": 0,
        #     "totalHouseTax": 0,
        #     "housingUnit": "sqft",
        #     "lightingTax": 300,
        #     "healthTax": 300,
        #     "waterTax": 0,
        #     "cleaningTax": 300,
        #     "toiletTax": 0,
        #     "totaltax": 0,
        #     "userId": [
        #         2
        #     ],
        #     "villageId": "3",
        #     "creationAt": "2025-07-03T11:16:50.572730",
        #     "updationAt": "2025-07-03T11:16:50.572730"
        # }
        # ]
        
        # data = data * 100

        # Render template
        if not isinstance(data, list):
            data = [data]
            
        context = {
                
        }
        rendered_html = template.render(data=data)


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
    
@router.post('/single_print_form')
async def singlePrint(request : Request):
    try:
        # Load template
        requestData = await request.json()
        anuKramank = requestData.get("anuKramank")
        villageID = requestData.get("villageID")
        template = env.get_template('singlePrintForm.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_record/{anuKramank}', params={
                'district_id': requestData.get('district_id'),
                'taluka_id': requestData.get('taluka_id'),
                "village_id" : villageID,
                'gram_panchayat_id': requestData.get('gram_panchayat_id')
            })
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

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
    
@router.post('/single_print_vishesh_pani')
async def singlePrint(request : Request):
    try:
        # Load template
        requestData = await request.json()
        anuKramank = requestData.get("anuKramank")
        villageID = requestData.get("villageID")
        template = env.get_template('singlePrintVishehPani.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/namuna8/recordresponses/property_record/{anuKramank}', params={
                'district_id': requestData.get('district_id'),
                "village_id" : villageID,
                'taluka_id': requestData.get('taluka_id'),
                'gram_panchayat_id': requestData.get('gram_panchayat_id')
            })
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        QRdata = {
            "srNO" : data.get('srNo') or "",
            "TotalArea" : data.get('total_arearinfoot') or "",
            "Construction" : data.get('total_arearinfoot') or "",
            "OpenSpace" : data['khaliJaga'][0].get('totalkhalijagaareainfoot') if data.get('khaliJaga') and len(data['khaliJaga']) > 0 else "",
            "TotalTax" : data.get('totaltax') or ""
            
        }
        QRCodeGeneration.createQRcode(QRdata)

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
    
@router.post('/single_print_vishesh_pani_range')
async def singlePrint(request : Request):
    try:
        # Load template
        requestData = await request.json()
        villageId = requestData.get("villageID")
        district_id = requestData.get("district_id")
        taluka_id = requestData.get("taluka_id")
        gram_panchayat_id = requestData.get("gram_panchayat_id")
        template = env.get_template('singlePrintVishehPaniRange.html')

        # Call API - use base URL from request to avoid localhost issues in installer
        base_url = str(request.base_url).rstrip('/')
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{base_url}/namuna8/recordresponses/property_records_by_village/{villageId}' ,
            params={"district_id" : district_id , "taluka_id" : taluka_id , "gram_panchayat_id" : gram_panchayat_id})

        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()
        # data = [
        #             {
        #     "id": "1",
        #     "srNo": 1,
        #     "propertyNumber": "जरीचेवखडकाचे",
        #     "propertyDescription": "दगड सिमेंट चुना अर्ध पक्के घर, आर सी सी",
        #     "gramPanchayat": "गट नं 6",
        #     "village": "गट नं 6",
        #     "taluka": "null",
        #     "jilha": "null",
        #     "yearFrom": 2024,
        #     "yearTo": 2027,
        #     "photoURL": "null",
        #     "QRcodeURL": "null",
        #     "total_arearinfoot": 9879.0,
        #     "totalareainmeters": 917.79,
        #     "occupantName": "स्वत:",
        #     "aadharNumber": "",
        #     "ownerName": "श्री रामराव पि.तत्तवराव पावडे",
        #     "roadName": "",
        #     "cityWardGatNumber": "",
        #     "areaEast": 133.5,
        #     "areaWest": 133.5,
        #     "areaNorth": 74.5,
        #     "areaSouth": 73.5,
        #     "totalArea": 9879.0,
        #     "boundaryEast": "पांडुरंग बाबाराव",
        #     "boundaryWest": "रस्ता वि. द. शाळा",
        #     "boundaryNorth": "बाजरीचे व खडकाचे",
        #     "boundarySouth": " खडकाचे",
        #     "removeLightHealthTax": "true",
        #     "applyCleaningTax": "true",
        #     "applyToiletTax": "false",
        #     "taxNotApplicable": "false",
        #     "khaliJaga": [
        #         {
        #             "constructiontype": "खाली जागा",
        #             "length": 8538.0,
        #             "width": 1,
        #             "year": 2025,
        #             "rate": "null",
        #             "floor": "null",
        #             "usage": "null",
        #             "capitalValue": 541133,
        #             "houseTax": 0,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": "null",
        #             "totalkhalijagaareainfoot": 8538.0,
        #             "totalkhalijagaareainmeters": 793.21
        #         }
        #     ],
        #     "constructionType": [
        #         {
        #             "type": "दगड सिमेंट चुना अर्ध पक्के घर",
        #             "length": 494.0,
        #             "width": 1.0,
        #             "year": "1999",
        #             "rate": 14137.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 406,
        #             "depreciation_rate": 70,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 0.75
        #         },
        #         {
        #             "type": "आर सी सी",
        #             "length": 847.0,
        #             "width": 1.0,
        #             "year": "2005",
        #             "rate": 17424.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 541,
        #             "depreciation_rate": 75,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 1.0
        #         }
        #     ],
        #     "waterFacility1": "सामान्य पाणीकर",
        #     "waterFacility2": "सामान्य पाणीकर",
        #     "toilet": "आहे",
        #     "house": "आहे",
        #     "totalCapitalValue": 0,
        #     "totalHouseTax": 0,
        #     "housingUnit": "sqft",
        #     "lightingTax": 300,
        #     "healthTax": 300,
        #     "waterTax": 0,
        #     "cleaningTax": 300,
        #     "toiletTax": 0,
        #     "totaltax": 0,
        #     "userId": [
        #         2
        #     ],
        #     "villageId": "3",
        #     "creationAt": "2025-07-03T11:16:50.572730",
        #     "updationAt": "2025-07-03T11:16:50.572730"
        # },
        #             {
        #     "id": "1",
        #     "srNo": 1,
        #     "propertyNumber": "जरीचेवखडकाचे",
        #     "propertyDescription": "दगड सिमेंट चुना अर्ध पक्के घर, आर सी सी",
        #     "gramPanchayat": "गट नं 6",
        #     "village": "गट नं 6",
        #     "taluka": "null",
        #     "jilha": "null",
        #     "yearFrom": 2024,
        #     "yearTo": 2027,
        #     "photoURL": "null",
        #     "QRcodeURL": "null",
        #     "total_arearinfoot": 9879.0,
        #     "totalareainmeters": 917.79,
        #     "occupantName": "श्री रामराव पि.तत्तवराव पावडे"  ,
        #     "aadharNumber": "",
        #     "ownerName": "श्री रामराव पि.तत्तवराव पावडे",
        #     "roadName": "",
        #     "cityWardGatNumber": "",
        #     "areaEast": 133.5,
        #     "areaWest": 133.5,
        #     "areaNorth": 74.5,
        #     "areaSouth": 73.5,
        #     "totalArea": 9879.0,
        #     "boundaryEast": "पांडुरंग बाबाराव",
        #     "boundaryWest": "रस्ता वि. द. शाळा",
        #     "boundaryNorth": "बाजरीचे व खडकाचे",
        #     "boundarySouth": " खडकाचे",
        #     "removeLightHealthTax": "true",
        #     "applyCleaningTax": "true",
        #     "applyToiletTax": "false",
        #     "taxNotApplicable": "false",
        #     "khaliJaga": [
        #         {
        #             "constructiontype": "खाली जागा",
        #             "length": 8538.0,
        #             "width": 1,
        #             "year": 2025,
        #             "rate": "null",
        #             "floor": "null",
        #             "usage": "null",
        #             "capitalValue": 541133,
        #             "houseTax": 0,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": "null",
        #             "totalkhalijagaareainfoot": 8538.0,
        #             "totalkhalijagaareainmeters": 793.21
        #         }
        #     ],
        #     "constructionType": [
        #         {
        #             "type": "दगड सिमेंट चुना अर्ध पक्के घर",
        #             "length": 494.0,
        #             "width": 1.0,
        #             "year": "1999",
        #             "rate": 14137.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 406,
        #             "depreciation_rate": 70,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 0.75
        #         },
        #         {
        #             "type": "आर सी सी",
        #             "length": 847.0,
        #             "width": 1.0,
        #             "year": "2005",
        #             "rate": 17424.0,
        #             "floor": "तळमजला",
        #             "usage": "निवासी",
        #             "capitalValue": 541133,
        #             "houseTax": 541,
        #             "depreciation_rate": 75,
        #             "usageBasedBuildingWeightageFactor": 1,
        #             "taxRates": 1.0
        #         }
        #     ],
        #     "waterFacility1": "सामान्य पाणीकर",
        #     "waterFacility2": "सामान्य पाणीकर",
        #     "toilet": "आहे",
        #     "house": "आहे",
        #     "totalCapitalValue": 0,
        #     "totalHouseTax": 0,
        #     "housingUnit": "sqft",
        #     "lightingTax": 300,
        #     "healthTax": 300,
        #     "waterTax": 0,
        #     "cleaningTax": 300,
        #     "toiletTax": 0,
        #     "totaltax": 0,
        #     "userId": [
        #         2
        #     ],
        #     "villageId": "3",
        #     "creationAt": "2025-07-03T11:16:50.572730",
        #     "updationAt": "2025-07-03T11:16:50.572730"
        # }
        # ]
        
        # data = data * 100

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(data=data)

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
    
