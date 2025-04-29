from fastapi import FastAPI, HTTPException, Response
from typing import List, Optional
import requests
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# v1.x SDK
from ibm_watsonx_ai.foundation_models import ModelInference  
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# ——— Setup ———
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

class EventOut(BaseModel):
    id: str
    subject: Optional[str] = None
    owner_id: Optional[str] = None
    owner_name: Optional[str] = None
    what_id: Optional[str] = None
    what_name: Optional[str] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    appointment_status_c: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None
    description: Optional[str] = None
    created_by_name: Optional[str] = None
    created_by_id: Optional[str] = None
    last_modified_by_name: Optional[str] = None
    last_modified_by_id: Optional[str] = None

app = FastAPI()

# Salesforce creds
SALESFORCE_CONSUMER_KEY    = os.getenv("SALESFORCE_CONSUMER_KEY")
SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
SALESFORCE_USERNAME        = os.getenv("SALESFORCE_USERNAME")
SALESFORCE_PASSWORD        = os.getenv("SALESFORCE_PASSWORD")

# Watsonx.ai v1.x creds & model
WATSONX_API_KEY    = os.getenv("WATSONX_API_KEY")
WATSONX_API_URL    = os.getenv("WATSONX_API_URL")
WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID")
WATSONX_MODEL_ID   = os.getenv("WATSONX_MODEL_ID")

# ——— Helpers ———

def get_salesforce_access_token():
    if not all([SALESFORCE_CONSUMER_KEY, SALESFORCE_CONSUMER_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD]):
        raise HTTPException(500, "Missing Salesforce credentials")
    resp = requests.post(
        "https://login.salesforce.com/services/oauth2/token",
        data={
            "grant_type":    "password",
            "client_id":     SALESFORCE_CONSUMER_KEY,
            "client_secret": SALESFORCE_CONSUMER_SECRET,
            "username":      SALESFORCE_USERNAME,
            "password":      SALESFORCE_PASSWORD
        }
    )
    if resp.status_code != 200:
        raise HTTPException(401, "Salesforce authentication failed")
    return resp.json()

def new_model_inference() -> ModelInference:
    creds = {
        "apikey": WATSONX_API_KEY,
        "url":    WATSONX_API_URL
    }
    return ModelInference(
        model_id    = WATSONX_MODEL_ID,
        credentials = creds,
        project_id  = WATSONX_PROJECT_ID,
        space_id    = None
    )

def build_markdown_local(events: List[EventOut]) -> str:
    """Pure-Python fallback Markdown builder."""
    headers = [
        "id","subject","owner_id","owner_name",
        "what_id","what_name","account_id","account_name",
        "appointment_status_c","start_datetime","end_datetime",
        "description","created_by_name","created_by_id",
        "last_modified_by_name","last_modified_by_id"
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"]*len(headers)) + " |"
    ]
    for e in events:
        row = []
        for h in headers:
            val = getattr(e, h) or ""
            cell = str(val).replace("|","\\|").replace("\n"," ")
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

def generate_markdown_with_watsonx(events: List[EventOut]) -> str:
    """LLM-generated table with fallback if instance inactive."""
    mi = new_model_inference()
    params = {
        GenParams.DECODING_METHOD: "greedy",
        GenParams.MAX_NEW_TOKENS: 4096,
        GenParams.MIN_NEW_TOKENS: 0,
        GenParams.TEMPERATURE: 0.7,
        GenParams.TOP_P: 1.0
    }
    batch_size = 50
    tables: List[str] = []

    for i in range(0, len(events), batch_size):
        batch = events[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size+1} ({len(batch)} events)")
        prompt = (
            "Given the following Salesforce event data in JSON, generate a Markdown table with columns:\n"
            + json.dumps([e.dict() for e in batch], indent=2)
        )
        try:
            result = mi.generate_text(prompt=prompt, params=params).strip()
            tables.append(result)
        except Exception as e:
            msg = str(e)
            if "invalid_instance_status_error" in msg:
                logger.warning("Watsonx.ai inactive—falling back to local builder")
                return build_markdown_local(events)
            logger.error(f"Watsonx.ai error: {msg}")
            raise HTTPException(500, f"Watsonx.ai failure: {msg}")

    if tables:
        # stitch first header+separator, then all rows
        first = tables[0].split("\n")
        combined = first[:2]
        for tbl in tables:
            combined.extend(tbl.split("\n")[2:])
        return "\n".join(combined)

    # if no tables at all
    return build_markdown_local(events)

# ——— Endpoint ———

@app.get("/events/")
async def get_events():
    auth = get_salesforce_access_token()
    token = auth["access_token"]
    inst  = auth["instance_url"]

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json"
    }

    soql = (
        "SELECT Id, Subject, OwnerId, WhatId, AccountId, "
        "Appointment_Status__c, StartDateTime, EndDateTime, Description, "
        "CreatedById, LastModifiedById, Owner.Name, What.Name, Account.Name, "
        "CreatedBy.Name, LastModifiedBy.Name FROM Event"
    )
    url = f"{inst}/services/data/v59.0/query?q={soql}"

    sess = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
    sess.mount("https://", HTTPAdapter(max_retries=retries))

    events: List[EventOut] = []
    while url:
        resp = sess.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        page = resp.json()

        for rec in page.get("records", []):
            owner         = rec.get("Owner")         or {}
            what          = rec.get("What")          or {}
            account       = rec.get("Account")       or {}
            created_by    = rec.get("CreatedBy")     or {}
            last_modified = rec.get("LastModifiedBy") or {}

            events.append(EventOut(
                id                     = rec["Id"],
                subject                = rec.get("Subject"),
                owner_id               = rec.get("OwnerId"),
                owner_name             = owner.get("Name"),
                what_id                = rec.get("WhatId"),
                what_name              = what.get("Name"),
                account_id             = rec.get("AccountId"),
                account_name           = account.get("Name"),
                appointment_status_c   = rec.get("Appointment_Status__c"),
                start_datetime         = rec.get("StartDateTime"),
                end_datetime           = rec.get("EndDateTime"),
                description            = rec.get("Description"),
                created_by_name        = created_by.get("Name"),
                created_by_id          = rec.get("CreatedById"),
                last_modified_by_name  = last_modified.get("Name"),
                last_modified_by_id    = rec.get("LastModifiedById"),
            ))

        nxt = page.get("nextRecordsUrl")
        url = f"{inst}{nxt}" if nxt else None

    logger.info(f"Fetched {len(events)} events total")
    markdown = generate_markdown_with_watsonx(events)
    return Response(content=markdown, media_type="text/plain")
