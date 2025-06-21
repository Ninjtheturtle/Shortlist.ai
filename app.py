import os
import csv
import io
import random
import uuid
import fitz
import requests
import numpy as np
from flask import Flask, request, render_template, jsonify
from supabase import create_client, Client
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
from colorama import init, Fore, Style
from flask import session  # make sure this is imported at the top


init(autoreset=True)  # For auto-resetting colors after each print

conversations = {}
# Ngrok URL - to be pasted in the CLI
NGROK_URL = input("Paste your ngrok HTTPS URL (e.g. https://1234.ngrok.io/): ").strip()

def log(message, level="info"):
    levels = {
        "info": Fore.CYAN,
        "success": Fore.GREEN,
        "warning": Fore.YELLOW,
        "error": Fore.RED
    }
    color = levels.get(level, Fore.WHITE)
    print(f"{color}[{level.upper()}]{Style.RESET_ALL} {message}")

load_dotenv()

app = Flask(__name__)
app.secret_key = 'your_secret_key'

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

vector_upload_done = False

def get_embedding(text: str) -> list:
    log("Generating embedding from OpenAI", "info")
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def extract_text_from_pdf_url(url):
    try:
        log(f"Fetching and parsing PDF from: {url}", "info")
        response = requests.get(url)
        if response.status_code != 200:
            log(f"Failed to fetch PDF: {response.status_code}", "warning")
            return ""
        pdf_data = io.BytesIO(response.content)
        doc = fitz.open(stream=pdf_data, filetype="pdf")
        return " ".join([page.get_text() for page in doc])
    except Exception as e:
        log(f"Error reading PDF: {e}", "error")
        return ""

@app.route('/csv', methods=['GET'])
def csv_page():
    return render_template('csv.html', show_progress=False)

@app.route('/upload', methods=['POST'])
def upload_csv():
    try:
        global vector_upload_done
        vector_upload_done = False

        file = request.files.get('csvfile')
        listing_name = request.form.get('listing_name')
        job_description = request.form.get('job_description')

        if not file or not listing_name or not job_description:
            log("Missing form data", "error")
            return "Missing form data", 400

        job_id = random.randint(1000000000, 9999999999)
        session['job_id'] = job_id
        log(f"Stored job_id {job_id} in session", "info")
        reference_text = f"{listing_name}. {job_description}"
        reference_vector = np.array(get_embedding(reference_text))

        log("Inserting job listing into Supabase", "info")
        supabase.table("listings").insert({
            "name": listing_name,
            "job_id": job_id,
            "description": job_description,
            "vector": reference_vector.tolist()
        }).execute()

        log("Parsing CSV for applicants", "info")
        stream = io.StringIO(file.stream.read().decode("utf-8"))
        reader = csv.DictReader(stream)
        raw_applicants = []
        for row in reader:
            raw_applicants.append({
                "name": row.get("Name"),
                "email": row.get("Email"),
                "linkedin": row.get("LinkedIn"),
                "phone": row.get("Phone Number"),
                "resume_link": row.get("Resume Link(PDF)"),
                "appliedTo": job_id
            })

        scored_applicants = []
        for i, applicant in enumerate(raw_applicants):
            resume_text = extract_text_from_pdf_url(applicant["resume_link"])
            if resume_text.strip() == "":
                log(f"Skipping empty resume: {applicant['name']}", "warning")
                continue

            resume_vector = np.array(get_embedding(resume_text))
            similarity = cosine_similarity([reference_vector], [resume_vector])[0][0]
            applicant["vector"] = resume_vector.tolist()
            applicant["resume"] = resume_text
            scored_applicants.append((similarity, applicant))

            log(f"Compared {i+1}/{len(raw_applicants)} — {applicant['name']} | Score: {similarity:.4f}", "info")

        scored_applicants.sort(reverse=True, key=lambda x: x[0])
        top_5 = [app for _, app in scored_applicants[:5]]

        if top_5:
            log(f"Inserting top {len(top_5)} candidates into Supabase", "success")
            supabase.table("applicants").insert(top_5).execute()

        vector_upload_done = True
        log("Vector upload completed!", "success")
        return '', 204

    except Exception as e:
        log(f"Error during upload: {str(e)}", "error")
        return f"An error occurred: {str(e)}", 500

@app.route('/check_vectors_uploaded')
def check_vectors_uploaded():
    global vector_upload_done
    return jsonify({"done": vector_upload_done})

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/phone_settings', methods=['GET', 'POST'])
def phone_settings():
    job_id = session.get('job_id')
    if not job_id:
        log("No job_id found in session", "error")
        return "Job ID not found in session", 400

    if request.method == 'POST':
        questions = request.json.get('questions', [])
        if questions:
            supabase.table("listings").update({
                "questions": questions
            }).eq("job_id", job_id).execute()
            log("Updated listing with questions", "success")
            return jsonify({"status": "ok"}), 200
        return jsonify({"error": "No questions provided"}), 400

    # GET request
    job_listing_response = supabase.table("listings").select("*").eq("job_id", job_id).execute()
    job_listing = job_listing_response.data[0] if job_listing_response.data else None
    job_desc = job_listing.get('description') if job_listing else "This is a software engineering role."

    applicants_response = supabase.table("applicants").select("*").eq("appliedTo", job_id).execute()
    applicants = applicants_response.data if applicants_response.data else []

    def call_gemini_ai(prompt):
        newprompt = prompt + " - Please provide a concise and relevant response. Do not include any markdown or formatting. Just text."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={os.getenv('GEMINI_API_KEY')}"
        payload = {"contents": [{"parts": [{"text": newprompt}]}]}
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            if 'candidates' in data and data['candidates']:
                parts = data['candidates'][0].get('content', {}).get('parts', [])
                return parts[0].get('text', '...') if parts else "..."
        except Exception as e:
            log(f"Gemini API error: {e}", "error")
            return "..."

    # Generate questions
    behavioral_q = call_gemini_ai(f"Write a behavioral interview question for this job: {job_desc}")
    technical_q = call_gemini_ai(f"Write a technical interview question for this job: {job_desc}")
    critical_q = call_gemini_ai(f"Write a critical thinking interview question for this job: {job_desc}")

    return render_template(
        'phone_settings.html',
        job=job_listing,
        applicants=applicants,
        behavioral_q=behavioral_q,
        technical_q=technical_q,
        critical_q=critical_q
    )

def retrieveApplicantDetails(listingID):
    jobDescription = (
        supabase.table("listings").select("*").eq("job_id", listingID).execute()
    ).data[0]["description"]

    applicant = (
        supabase.table("applicants").select("*").eq("appliedTo", listingID).eq("email", "vangara.anirudhbharadwaj@gmail.com").execute()
    ).data[0]

    resume = applicant["resume"]
    phone = applicant["phone"]

    return {
        "resume": resume,
        "phone": phone,
        "jobDescription": jobDescription
    }

@app.route('/initiate_fake_call', methods=['POST'])
def initiate_call():
    data = request.form
    required_fields = ['listingID']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400

    details = retrieveApplicantDetails(data['listingID'])

    conversation_id = str(uuid.uuid4())
    conversations[conversation_id] = {
        'history': [],
        'context': {
             'user_number': details['phone'],
            'customer_service_number': details['phone'],
            'issue_description': details['jobDescription'],
            'resume': details['resume'],
            'status': 'initiating',
            'call_sid': None
        }
    }

    client = Client(app.config['TWILIO_ACCOUNT_SID'], app.config['TWILIO_AUTH_TOKEN'])

    webhook_url = f"{NGROK_URL}/voice/{conversation_id}"
    status_callback_url = f"{NGROK_URL}/call_status/{conversation_id}"

    call = client.calls.create(
        url=webhook_url,
        to=data['customer_service_number'],
        from_=app.config['TWILIO_PHONE_NUMBER'],
        record=True,
        status_callback=status_callback_url,
        status_callback_event=['initiated', 'ringing', 'answered', 'completed'],
        timeout=30
    )

    conversations[conversation_id]['context']['call_sid'] = call.sid
    conversations[conversation_id]['context']['status'] = 'initiated'

    return jsonify({
        'status': 'call_initiated',
        'conversation_id': conversation_id,
        'call_sid': call.sid
    })


@app.route('/phone_list')
def phone_list():
    job_id = session.get('job_id')
    if not job_id:
        return "Missing job ID", 400

    applicants_response = supabase.table("applicants").select("*").eq("appliedTo", job_id).execute()
    applicants = applicants_response.data if applicants_response.data else []

    return render_template('phone_list.html', applicants=applicants, job_id=job_id)


@app.route('/shortlist')
def shortlist():
    return render_template('shortlist.html')

if __name__ == '__main__':
    app.run(debug=True)
