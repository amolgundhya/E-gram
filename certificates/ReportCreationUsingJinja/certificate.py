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
certificate_template_dir = os.path.join(template_dir ,'Certificates' )
home_path = os.path.expanduser("~")

# Path to: C:\Users\<User>\AppData\Local\grampanchayat\reports
static_dir = os.path.join(home_path, 'Documents', 'grampanchayat', 'reports')
env = Environment(loader=FileSystemLoader(certificate_template_dir))

localhost = "http://127.0.0.1:8000"

@router.post('/birth')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('janma.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/birth/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/death')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('death.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/death/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/birthdeath')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('janmndeath.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/birthdeath-unavailability/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/resident')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('RahivashiDakhla.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/resident/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/family')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('BelowPovertyLine.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/family/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/toilet')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('toilet.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/toilet/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/no-objection')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('noObjection.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/no-objection/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/no-benefit')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('nonBeneficiary.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/no-benefit/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/life')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('living.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/life/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/good-conduct')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('character.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/good-conduct/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/niradhar')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('unfounded.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/niradhar/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/marriage')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('marriage.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/marriage/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/no_arrears')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('noDues.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/no_arrears/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/no_arrears')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('noDues.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/no_arrears/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
            
@router.post('/widow')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('widow.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/widow/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/unemployment')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('unemployed.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/unemployment/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
        
@router.post('/receipt')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        userID = requestData.get("userID")
        template = env.get_template('receiptOfCertificate.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/receipt/{userID}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Render template
        if not isinstance(data, list):
            data = [data]
        rendered_html = template.render(**data[0])
        
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
            
@router.post('/all')
async def prakar1(request : Request):
    try:
        # Load template
        requestData = await request.json()
        fromDate = requestData.get("fromDate")
        toDate = requestData.get("toDate")
        template = env.get_template('certificateRegister.html')

        # Call API
        async with httpx.AsyncClient() as client:
            response = await client.get(f'{localhost}/certificates/all?from_date={fromDate}&to_date={toDate}')
        if response.status_code != 200:
            raise Exception(f"API error {response.status_code}: {response.text}")

        data = response.json()

        # Adapt to new /certificates/all response shape
        records = []
        jilha = ''
        taluka = ''
        gramPanchayat = ''
        if isinstance(data, dict):
            records = data.get('records', []) or []
            jilha = data.get('jilha') or ''
            taluka = data.get('taluka') or ''
            gramPanchayat = data.get('gramPanchayat') or ''
        else:
            # Backwards compatibility if API returns a list
            records = data if isinstance(data, list) else []
        
        # Get current date
        from datetime import datetime
        currentDate = datetime.now().strftime("%Y-%m-%d")

        context = {
            "data": records,
            "gramPanchayat": gramPanchayat,
            "taluka": taluka,
            "jilha": jilha,
            "startDate": fromDate,
            "toDate": toDate,
            "currentDate": currentDate
        }
        
        rendered_html = template.render(context)
        
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