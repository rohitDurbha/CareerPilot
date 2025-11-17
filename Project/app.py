import base64
from flask import Flask, request, jsonify
import asyncio
import aiohttp
import motor.motor_asyncio
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes and origins

# MongoDB Configuration
MONGO_URI = 'mongodb+srv://username:password@cluster.mongodb.net/database_name?retryWrites=true&w=majority'
MONGO_DB = 'your_database'
MONGO_COLLECTION = 'workflow_results'

mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
mongo_collection = mongo_db[MONGO_COLLECTION]

# Your actual Activepieces workflow webhook URLs
ENDPOINT_1 = 'https://cloud.activepieces.com/api/v1/webhooks/fBxRSJDCR5u5vZ5ITnMHh'
ENDPOINT_2 = 'https://cloud.activepieces.com/projects/YpzM2RF9vJtLfo4RI7tPk/flows/qKGh21mfk4tKxK6QuE63e'

async def trigger_workflow(url, payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return {'status': resp.status, 'data': data}

async def save_to_mongo(result):
    insert_result = await mongo_collection.insert_one(result)
    return str(insert_result.inserted_id)

@app.route('/trigger', methods=['POST'])
def trigger():
    try:
        # Get form fields and file from request
        keyword = request.form.get('keyword', '')
        location = request.form.get('location', '')
        publishedAt = 'r86400'  # Constant

        # Get and encode resume PDF/DOC as base64 string
        resume_file = request.files.get('resume')
        resume_b64 = None
        if resume_file:
            resume_bytes = resume_file.read()
            resume_b64 = base64.b64encode(resume_bytes).decode('utf-8')
        else:
            return jsonify({'error': 'Resume file missing'}), 400
        
        # Build workflow payload
        payload1 = {
            "keyword": [keyword],
            "location": location,
            "publishedAt": publishedAt, 
        }
        payload2 = {
            "resume": resume_b64
        }

        async def process_both():
            # Kick off both workflow endpoints in parallel
            task1 = trigger_workflow(ENDPOINT_1, payload)
            task2 = trigger_workflow(ENDPOINT_2, payload)
            results = await asyncio.gather(task1, task2, return_exceptions=True)
            # Success/failure logic
            if all(isinstance(res, dict) and res['status'] == 200 for res in results):
                post_processing_output = {'message': 'Both workflows succeeded', 'results': results}
                mongo_id = await save_to_mongo(post_processing_output)
                post_processing_output['mongo_id'] = mongo_id
                return post_processing_output
            else:
                failure_output = {'message': 'One or both workflows failed', 'results': results}
                mongo_id = await save_to_mongo(failure_output)
                failure_output['mongo_id'] = mongo_id
                return failure_output

        # Run async logic in Flask (sync) context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(process_both())
        return jsonify(result)
    except Exception as e:
        # Log error for debugging
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': 'Server error', 'details': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
