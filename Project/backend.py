import base64
import uuid
import datetime
import asyncio
import aiohttp
import subprocess
import re
import traceback

from flask import Flask, request, jsonify
from flask_cors import CORS
from PyPDF2 import PdfReader
from supabase import create_client, Client
import motor.motor_asyncio
from pymongo import MongoClient

# --- Configuration and clients ---

MONGO_URI = 'mongodb+srv://cs156:cs156@careerpilot.thhqt84.mongodb.net/?retryWrites=true&w=majority&appName=CareerPilo'
MONGO_DB = 'scrapped_jobs'
MONGO_COLLECTION = 'Careerpilot'

# Async client (for your async workflows)
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB]
mongo_collection = mongo_db[MONGO_COLLECTION]

# Sync client (for synchronous endpoints like /latest_jobs)
pymongo_client = MongoClient(MONGO_URI)
pymongo_collection = pymongo_client[MONGO_DB][MONGO_COLLECTION]

AI_LOG_PATH = "/Users/sripathisaipranav/Desktop/Calhacks/python-agents-examples/basics/ai_interview_log.txt"
USER_LOG_PATH = "/Users/sripathisaipranav/Desktop/Calhacks/python-agents-examples/basics/user_transcribed_log.txt"

ACTIVEPIECES_ENDPOINT_1 = "https://cloud.activepieces.com/api/v1/webhooks/fBxRSJDCR5u5vZ5ITnMHh"
ACTIVEPIECES_ENDPOINT_2 = 'https://cloud.activepieces.com/api/v1/webhooks/8Qu1Dn3i1kQgMTufjucRa'

# --- Flask and CORS initialization ---

app = Flask(__name__)
CORS(app)

# --- Globals for subprocess management ---
agent_procs = {"agent1": None, "agent2": None}

# --- Helper async functions ---

async def send_resume_to_activepieces(request, resume_text):
    job_id = request.form.get("job_id", "")
    job_description = request.form.get("job_description", "")
    email = request.form.get("email", "")

    payload = {
        "job_id": job_id,
        "job_description": job_description,
        "email": email,
        "resume_text": resume_text
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(ACTIVEPIECES_ENDPOINT_1, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return {"status": resp.status, "data": data}

async def trigger_workflow(url, payload):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = await resp.text()
            return {"status": resp.status, "data": data}

async def save_to_mongo(result):
    insert_result = await mongo_collection.insert_one(result)
    return str(insert_result.inserted_id)

# --- Flask Routes ---

@app.route("/", methods=["GET"])
def home():
    return "Backend is running."

@app.route("/upload_resume", methods=["POST"])
def upload_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No resume uploaded"}), 400
        resume_file = request.files["resume"]
        pdf_reader = PdfReader(resume_file)
        resume_text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
        if not resume_text.strip():
            return jsonify({"error": "Resume seems empty or could not be read."}), 400

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_resume_to_activepieces(request, resume_text))
        print(result["data"])
        return jsonify(result)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": "Server error", "details": str(e)}), 500

@app.route("/run_agents", methods=["POST"])
def run_agents():
    global agent_procs
    try:
        data = request.get_json(force=True)  # Parse JSON from POST body
        job_title = data.get("job_title", "")
        job_description = data.get("job_description", "")

        agent_procs["agent1"] = subprocess.Popen(
            [
                "python",
                "/Users/sripathisaipranav/Desktop/Calhacks/python-agents-examples/basics/listen_and_respond.py",
                "connect",
                "--room",
                "test-room",
            ]
        )
        agent_procs["agent2"] = subprocess.Popen(
            [
                "python",
                "/Users/sripathisaipranav/Desktop/Calhacks/python-agents-examples/basics/agent.py",
                "connect",
                "--room",
                "test-room",
            ]
        )
        return jsonify(
            {
                "status": "started",
                "message": "Both agents launched successfully",
                "pids": {
                    "agent1": agent_procs["agent1"].pid,
                    "agent2": agent_procs["agent2"].pid,
                },
                "received": {
                    "job_title": job_title,
                    "job_description": job_description,
                }
            }
        ), 200

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/cancel_file1", methods=["GET"])
def cancel_scripts():
    global agent_procs
    status_report = {}

    for key, proc in agent_procs.items():
        if proc is not None and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
                status_report[key] = "terminated"
            except Exception as e:
                status_report[key] = f"error terminating: {e}"
        else:
            status_report[key] = "not running"
        agent_procs[key] = None

    return jsonify(
        {
            "status": "completed",
            "message": "All scripts handled and logs uploaded",
            "details": status_report,
        }
    ), 200

@app.route("/trigger", methods=["POST"])
def trigger():
    try:
        keyword = request.form.get("keyword", "")
        location = request.form.get("location", "")
        publishedAt = "r86400"  # Constant

        if "resume" not in request.files:
            return jsonify({"error": "Resume file missing"}), 400

        resume_file = request.files["resume"]
        pdf_reader = PdfReader(resume_file)
        resume_text = "\n".join([page.extract_text() or "" for page in pdf_reader.pages])
        if not resume_text.strip():
            return jsonify({"error": "Resume seems empty or could not be read."}), 400

        async def run_workflows_sequentially():
            payload1 = {
                "keyword": [keyword],
                "location": location,
                "publishedAt": publishedAt,
            }
            result1 = await trigger_workflow(ACTIVEPIECES_ENDPOINT_1, payload1)

            if result1["status"] != 200:
                return {
                    "message": "First workflow failed",
                    "result": result1,
                }

            payload2 = {"resume_text": resume_text}
            result2 = await trigger_workflow(ACTIVEPIECES_ENDPOINT_2, payload2)

            if result2["status"] != 200:
                return {
                    "message": "Second workflow failed",
                    "result": result2,
                }

            success_output = {"message": "Both workflows succeeded", "results": [result1, result2]}
            # mongo_id = await save_to_mongo(success_output)
            # success_output["mongo_id"] = mongo_id
            return True

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_workflows_sequentially())
        return {"response": result}

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": "Server error", "details": str(e)}), 500

# --- Synchronous /latest_jobs endpoint using PyMongo ---
@app.route("/latest_jobs", methods=["GET"])
def latest_jobs():
    try:
        limit = int(request.args.get("limit", 20))
        cursor = pymongo_collection.find().sort([
            ("lastUpdatedTime", -1),
            ("resumeScore", -1)
        ]).limit(limit)
        jobs = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            jobs.append(doc)
        return jsonify({"count": len(jobs), "jobs": jobs})

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": "Failed to fetch latest jobs", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
