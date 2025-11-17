# app.py
import os
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Any

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    jsonify,
)

# Optional: OpenAI (or another LLM provider) for message generation & sentiment
# pip install openai
# from openai import OpenAI
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")


# -----------------------
# Data models (in-memory)
# -----------------------

@dataclass
class ICP:
    job_title: str
    company: str
    location: str
    size_min: int
    size_max: int
    industry: str
    value_prop: str


@dataclass
class Lead:
    id: str
    first_name: str
    last_name: str
    job_title: str
    company_name: str
    location: str
    email: str = ""
    linkedin_url: str = ""
    website: str = ""
    enrichment: Dict[str, Any] = field(default_factory=dict)
    qualification_score: float = 0.0
    channel_sequences: Dict[str, Any] = field(default_factory=dict)
    status: str = "new"  # new, enriched, qualified, messaged, replied
    sentiment: str = ""  # positive, neutral, negative


# In-memory “DB” for demo purposes
CURRENT_ICP: ICP | None = None
LEADS: Dict[str, Lead] = {}


# -----------------------
# Pipeline functions
# -----------------------

def run_pipeline(icp: ICP, limit: int = 20) -> List[Lead]:
    """
    Full pipeline:
    1. Find leads
    2. Enrich leads
    3. Qualify
    4. Generate hyper-personalized sequences
    5. (Optionally) send via Unipile / APIs
    """
    leads = find_leads(icp, limit=limit)
    enriched = [enrich_lead(lead) for lead in leads]
    qualified = [qualify_lead(lead, icp) for lead in enriched]
    messaged = [generate_sequences_for_lead(lead, icp) for lead in qualified]
    # Sending step would call Unipile / email API etc.
    # for lead in messaged:
    #     send_sequences(lead)

    # Persist in-memory
    for lead in messaged:
        LEADS[lead.id] = lead

    return messaged


def find_leads(icp: ICP, limit: int = 20) -> List[Lead]:
    """
    Stub: Replace with Apollo API + Google Search API calls.
    For now, returns fake leads that match the ICP-ish fields.
    """
    sample_companies = [
        "PixelGrowth Agency",
        "NYC Performance Media",
        "Brooklyn Digital Studio",
        "Manhattan Funnels Co.",
        "Queens Creative Labs",
    ]

    leads: List[Lead] = []
    for idx, company in enumerate(sample_companies[:limit]):
        lead_id = str(uuid.uuid4())
        lead = Lead(
            id=lead_id,
            first_name=f"Founder{idx+1}",
            last_name="Example",
            job_title=icp.job_title,
            company_name=company,
            location=icp.location,
        )
        leads.append(lead)
    return leads


def enrich_lead(lead: Lead) -> Lead:
    """
    Stub: Replace with enrichment provider (Apollo, Clearbit, People Data Labs, etc).
    """
    # Fake enrichment for demo
    lead.email = f"{lead.first_name.lower()}.{lead.last_name.lower()}@{lead.company_name.replace(' ', '').lower()}.com"
    lead.linkedin_url = f"https://www.linkedin.com/in/{lead.first_name.lower()}-{lead.last_name.lower()}"
    lead.website = f"https://{lead.company_name.replace(' ', '').lower()}.com"
    lead.enrichment = {
        "company_size": "10-25",
        "tech_stack": ["HubSpot", "Meta Ads", "Google Ads"],
        "recent_activity": "Recently hired a paid media specialist.",
    }
    lead.status = "enriched"
    return lead


def qualify_lead(lead: Lead, icp: ICP) -> Lead:
    """
    Simple rules-based qualification.
    In production, an LLM can read the profile + website and output a 0–10 score.
    """
    score = 0

    # Job title match
    if icp.job_title.lower() in lead.job_title.lower():
        score += 3

    # Company match
    if icp.company.lower() in "digital marketing agency":
        score += 2

    # Location match
    if icp.location.lower() in lead.location.lower():
        score += 2

    # Fake size & industry match
    company_size_str = lead.enrichment.get("company_size", "1-50")
    if "1-50" in company_size_str or "10-25" in company_size_str:
        score += 3

    # Cap at 10
    lead.qualification_score = min(score, 10)
    lead.status = "qualified"
    return lead


def generate_sequences_for_lead(lead: Lead, icp: ICP) -> Lead:
    """
    Stub: Generate email + LinkedIn sequences.
    Here, templated copy is used; in production, call an LLM to generate from full context.
    """

    # Example of what an LLM call might look like:
    # prompt = f"""
    # You are an expert B2B SDR. Write a 3-step email and 3-step LinkedIn sequence
    # for this ICP and prospect.
    # ICP: {icp}
    # Lead: {lead}
    # Company value prop: {icp.value_prop}
    # Make it short, specific, and conversational.
    # """
    # completion = client.chat.completions.create(
    #     model="gpt-4.1-mini",
    #     messages=[{"role": "user", "content": prompt}],
    # )
    # sequences = completion.choices[0].message.content

    # For demo purposes, define simple static sequences:
    email_sequence = [
        {
            "step": 1,
            "subject": f"{lead.company_name} → quick idea for more high-intent leads",
            "body": (
                f"Hey {lead.first_name},\n\n"
                f"Working with {icp.industry.lower()} teams in {icp.location}, "
                f"one pattern keeps showing up: they’re leaving a lot of warm traffic "
                f"on the table.\n\n"
                f"{icp.value_prop}\n\n"
                f"Open to a 10-minute teardown for {lead.company_name}?\n\n"
                f"Best,\nSales Team"
            ),
        },
        {
            "step": 2,
            "subject": "Re: quick idea for {company}".format(company=lead.company_name),
            "body": (
                f"Hey {lead.first_name},\n\n"
                "Quick bump on this—happy to send a Loom walking through "
                "3 concrete improvements just for your funnel.\n\n"
                "Worth a look?\n\n"
                "Best,\nSales Team"
            ),
        },
    ]

    linkedin_sequence = [
        {
            "step": 1,
            "type": "connection_request",
            "message": (
                f"Hey {lead.first_name}, saw you’re leading growth at {lead.company_name}. "
                f"Working with similar {icp.industry.lower()} teams in {icp.location}. "
                "Would love to connect and swap notes."
            ),
        },
        {
            "step": 2,
            "type": "follow_up",
            "message": (
                f"Thanks for connecting, {lead.first_name}! "
                f"Had a quick idea on how {lead.company_name} could turn more ad spend into "
                "booked revenue—want a quick loom or 10-min chat?"
            ),
        },
    ]

    lead.channel_sequences = {
        "email": email_sequence,
        "linkedin": linkedin_sequence,
    }
    lead.status = "messaged"
    return lead


def detect_reply_and_sentiment(message_text: str) -> Dict[str, str]:
    """
    Stub: Called from webhook when Unipile / email provider posts a reply.
    Should do sentiment analysis and return structured info.
    """
    # Example of LLM sentiment call:
    # completion = client.chat.completions.create(
    #     model="gpt-4.1-mini",
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": f"Classify this reply as positive, neutral, or negative:\n\n{message_text}",
    #         }
    #     ],
    # )
    # sentiment = completion.choices[0].message.content.strip().lower()

    # Basic placeholder logic:
    lowered = message_text.lower()
    if any(word in lowered for word in ["yes", "sure", "interested", "let's talk", "call"]):
        sentiment = "positive"
    elif any(word in lowered for word in ["not interested", "stop", "unsubscribe", "no"]):
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {"sentiment": sentiment}


# -----------------------
# Routes
# -----------------------

@app.route("/", methods=["GET"])
def index():
    global CURRENT_ICP, LEADS
    leads_sorted = sorted(
        LEADS.values(),
        key=lambda l: l.qualification_score,
        reverse=True,
    )
    return render_template(
        "index.html",
        icp=CURRENT_ICP,
        leads=leads_sorted,
    )


@app.route("/run", methods=["POST"])
def run():
    global CURRENT_ICP

    job_title = request.form.get("job_title", "CEO")
    company = request.form.get("company", "Digital Marketing Agency")
    location = request.form.get("location", "New York")
    size_min = int(request.form.get("size_min", 1))
    size_max = int(request.form.get("size_max", 50))
    industry = request.form.get("industry", "Marketing")
    value_prop = request.form.get(
        "value_prop",
        "We build AI-powered outbound machines that create a consistent flow of qualified demos.",
    )
    lead_limit = int(request.form.get("lead_limit", 10))

    CURRENT_ICP = ICP(
        job_title=job_title,
        company=company,
        location=location,
        size_min=size_min,
        size_max=size_max,
        industry=industry,
        value_prop=value_prop,
    )

    leads = run_pipeline(CURRENT_ICP, limit=lead_limit)

    flash(f"Pipeline completed. {len(leads)} leads sourced & processed.", "success")
    return redirect(url_for("index"))


@app.route("/lead/<lead_id>", methods=["GET"])
def lead_detail(lead_id: str):
    lead = LEADS.get(lead_id)
    if not lead:
        flash("Lead not found.", "danger")
        return redirect(url_for("index"))
    return jsonify(
        {
            "id": lead.id,
            "first_name": lead.first_name,
            "last_name": lead.last_name,
            "job_title": lead.job_title,
            "company_name": lead.company_name,
            "location": lead.location,
            "email": lead.email,
            "linkedin_url": lead.linkedin_url,
            "website": lead.website,
            "enrichment": lead.enrichment,
            "qualification_score": lead.qualification_score,
            "status": lead.status,
            "sentiment": lead.sentiment,
            "channel_sequences": lead.channel_sequences,
        }
    )


@app.route("/webhook/reply", methods=["POST"])
def webhook_reply():
    """
    Example webhook endpoint Unipile / email provider can call
    when a prospect replies. Payload needs to contain:
    - lead_id (or email/linkedIn identifier you map to a lead)
    - message_text
    """
    data = request.get_json(force=True, silent=True) or {}
    lead_id = data.get("lead_id")
    message_text = data.get("message_text", "")

    if not lead_id or lead_id not in LEADS:
        return jsonify({"error": "Lead not found"}), 404

    lead = LEADS[lead_id]
    sentiment_info = detect_reply_and_sentiment(message_text)
    lead.sentiment = sentiment_info["sentiment"]
    lead.status = "replied"  # Sequence should be paused at this point

    # Here, update external tools / CRM as needed.
    return jsonify({"ok": True, "sentiment": lead.sentiment})


@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv("PORT", 5050)))
