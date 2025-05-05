# from fastapi import FastAPI, HTTPException, Response
# from typing import List, Optional
# import requests
# from pydantic import BaseModel
# import os
# from dotenv import load_dotenv
# import logging
# import json
# from requests.adapters import HTTPAdapter
# from urllib3.util.retry import Retry

# # v1.x SDK
# from ibm_watsonx_ai.foundation_models import ModelInference
# from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

# # ——— Setup ———
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# load_dotenv()

# class EventOut(BaseModel):
#     id: str
#     subject: Optional[str] = None
#     owner_id: Optional[str] = None
#     owner_name: Optional[str] = None
#     what_id: Optional[str] = None
#     what_name: Optional[str] = None
#     account_id: Optional[str] = None
#     account_name: Optional[str] = None
#     appointment_status_c: Optional[str] = None
#     start_datetime: Optional[str] = None
#     end_datetime: Optional[str] = None
#     description: Optional[str] = None
#     created_by_name: Optional[str] = None
#     created_by_id: Optional[str] = None
#     last_modified_by_name: Optional[str] = None
#     last_modified_by_id: Optional[str] = None

# app = FastAPI()

# # Salesforce creds
# SALESFORCE_CONSUMER_KEY='3MVG9wt4IL4O5wvKmuWykzw13DGFOnjtd2q0MhKTvjQRdylQtrxmuTnEq4i2_.s6sQSQ5YJMl.1n_ScCpSDSP'
# SALESFORCE_CONSUMER_SECRET='B7143F5B5BEA70B22F037608F6FDCD818AFEFDC88CD1588FB0608720471E9369'
# SALESFORCE_USERNAME='impwatson@gadieltechnologies.com'
# SALESFORCE_PASSWORD='Wave@#123456'



# WATSONX_API_KEY="kEYC-iaRZRuEb0AIck5x1iCDB32Zdb8MkC_3j6AzpIz3"
# WATSONX_PROJECT_ID="4152f31e-6a49-40aa-9b62-0ecf629aae42"
# WATSONX_MODEL_ID="ibm/granite-13b-instruct-v2"
# WATSONX_API_URL="https://us-south.ml.cloud.ibm.com"
# # ——— Helpers ———

# def get_salesforce_access_token():
#     if not all([SALESFORCE_CONSUMER_KEY, SALESFORCE_CONSUMER_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD]):
#         raise HTTPException(500, "Missing Salesforce credentials")
#     resp = requests.post(
#         "https://login.salesforce.com/services/oauth2/token",
#         data={
#             "grant_type": "password",
#             "client_id": SALESFORCE_CONSUMER_KEY,
#             "client_secret": SALESFORCE_CONSUMER_SECRET,
#             "username": SALESFORCE_USERNAME,
#             "password": SALESFORCE_PASSWORD
#         }
#     )
#     if resp.status_code != 200:
        
#         raise HTTPException(401, "Salesforce authentication failed")
#     print(resp.json())
#     return resp.json()

# def new_model_inference() -> ModelInference:
#     creds = {
#         "apikey": WATSONX_API_KEY,
#         "url": WATSONX_API_URL
#     }
#     return ModelInference(
#         model_id=WATSONX_MODEL_ID,
#         credentials=creds,
#         project_id=WATSONX_PROJECT_ID,
#         space_id=None
#     )

# def estimate_tokens(text: str) -> int:
#     """Roughly estimate token count (1 token ~ 4 characters)."""
#     return len(text) // 4

# def build_markdown_local(events: List[EventOut]) -> str:
#     """Pure-Python fallback Markdown builder with specific columns."""
#     headers = ["id", "subject", "owner_id", "owner_name", "what_id", "what_name", "account_id", "account_name", "appointment_status_c"]
#     lines = [
#         "| " + " | ".join(headers) + " |",
#         "| " + " | ".join(["---"] * len(headers)) + " |"
#     ]
#     for e in events:
#         row = []
#         for h in headers:
#             val = getattr(e, h) or ""
#             cell = str(val).replace("|", "\\|").replace("\n", " ")
#             row.append(cell)
#         lines.append("| " + " | ".join(row) + " |")
#     logger.debug(f"Local builder output: {lines}")
#     return "\n".join(lines)

# def generate_markdown_with_watsonx(events: List[EventOut]) -> str:
#     """LLM-generated table with specific columns and fallback if token limit exceeded."""
#     mi = new_model_inference()
#     params = {
#         GenParams.DECODING_METHOD: "greedy",
#         GenParams.MAX_NEW_TOKENS: 4096,
#         GenParams.MIN_NEW_TOKENS: 0,
#         GenParams.TEMPERATURE: 0.7,
#         GenParams.TOP_P: 1.0
#     }
#     batch_size = 1000
#     tables: List[str] = []
#     max_tokens = 8192
#     headers = ["id", "subject", "owner_id", "owner_name", "what_id", "what_name", "account_id", "account_name", "appointment_status_c"]

#     for i in range(0, len(events), batch_size):
#         batch = events[i:i + batch_size]
#         logger.info(f"Processing batch {i // batch_size + 1} ({len(batch)} events)")
#         event_data = [{k: getattr(e, k) for k in headers} for e in batch]
#         prompt = (
#             "Generate a Markdown table with the following columns: id, subject, owner_id, owner_name, what_id, what_name, "
#             "account_id, account_name, appointment_status_c. Use the data below in JSON format:\n"
#             + json.dumps(event_data, separators=(",", ":"))
#         )
        
#         if estimate_tokens(prompt) > max_tokens:
#             logger.warning("Prompt exceeds token limit—falling back to local builder")
#             return build_markdown_local(events)
#         try:
#             result = mi.generate_text(prompt=prompt, params=params).strip()
#             logger.debug(f"Watsonx.ai result for batch {i // batch_size + 1}: {result}")
#             if not result.startswith("| id |"):
#                 result = "| " + " | ".join(headers) + " |\n| " + " | ".join(["---"] * len(headers)) + " |\n" + result
#             tables.append(result)
#         except Exception as e:
#             msg = str(e)
#             if any(x in msg for x in ["invalid_instance_status_error", "cannot exceed the total tokens limit"]):
#                 logger.warning("Watsonx.ai issue (inactive or token limit)—falling back to local builder")
#                 return build_markdown_local(events)
#             logger.error(f"Watsonx.ai error: {msg}")
#             raise HTTPException(500, f"Watsonx.ai failure: {msg}")

#     if tables:
#         first = tables[0].split("\n")
#         combined = first[:2]
#         for tbl in tables:
#             combined.extend(tbl.split("\n")[2:])
#         markdown = "\n".join(combined)
#         logger.debug(f"Final Markdown: {markdown}")
#         return markdown

#     return build_markdown_local(events)

# # ——— Endpoint ———

# @app.get("/events/")
# async def get_events():
#     auth = get_salesforce_access_token()
#     token = auth["access_token"]
#     inst = auth["instance_url"]

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     soql = (
#         "SELECT Id, Subject, OwnerId, WhatId, AccountId, "
#         "Appointment_Status__c, StartDateTime, EndDateTime, Description, "
#         "CreatedById, LastModifiedById, Owner.Name, What.Name, Account.Name, "
#         "CreatedBy.Name, LastModifiedBy.Name FROM Event"
#     )
#     url = f"{inst}/services/data/v59.0/query?q={soql}"

#     sess = requests.Session()
#     retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
#     sess.mount("https://", HTTPAdapter(max_retries=retries))

#     events: List[EventOut] = []
#     while url:
#         resp = sess.get(url, headers=headers, timeout=30)
#         resp.raise_for_status()
#         page = resp.json()
#         logger.debug(f"Raw page data: {page}")  # Log raw response to check records
#         for rec in page.get("records", []):
#             owner = rec.get("Owner") or {}
#             what = rec.get("What") or {}
#             account = rec.get("Account") or {}
#             created_by = rec.get("CreatedBy") or {}
#             last_modified = rec.get("LastModifiedBy") or {}

#             event = EventOut(
#                 id=rec["Id"],
#                 subject=rec.get("Subject"),
#                 owner_id=rec.get("OwnerId"),
#                 owner_name=owner.get("Name"),
#                 what_id=rec.get("WhatId"),
#                 what_name=what.get("Name"),
#                 account_id=rec.get("AccountId"),
#                 account_name=account.get("Name"),
#                 appointment_status_c=rec.get("Appointment_Status__c"),
#                 start_datetime=rec.get("StartDateTime"),
#                 end_datetime=rec.get("EndDateTime"),
#                 description=rec.get("Description"),
#                 created_by_name=created_by.get("Name"),
#                 created_by_id=rec.get("CreatedById"),
#                 last_modified_by_name=last_modified.get("Name"),
#                 last_modified_by_id=rec.get("LastModifiedById"),
#             )
#             events.append(event)
#             logger.debug(f"Processed event: {event.dict()}")  # Log each event

#         nxt = page.get("nextRecordsUrl")
#         url = f"{inst}{nxt}" if nxt else None

#     logger.info(f"Fetched {len(events)} events total")
#     if not events:
#         logger.warning("No events fetched from Salesforce")
#         return Response(content="| id | subject | owner_id | owner_name | what_id | what_name | account_id | account_name | appointment_status_c |\n|---|---|---|---|---|---|---|---|---|", media_type="text/plain")
#     markdown = generate_markdown_with_watsonx(events)
#     return Response(content=markdown, media_type="text/plain")


#================================New Code Update watsnox add local markdown===========================
# from fastapi import FastAPI, HTTPException, Response
# from typing import List, Optional
# import requests
# from pydantic import BaseModel
# import os
# from dotenv import load_dotenv
# import logging
# from urllib3.util.retry import Retry
# from requests.adapters import HTTPAdapter

# # Setup
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)
# load_dotenv()

# class EventOut(BaseModel):
#     id: str
#     subject: Optional[str] = None
#     owner_id: Optional[str] = None
#     owner_name: Optional[str] = None
#     what_id: Optional[str] = None
#     what_name: Optional[str] = None
#     account_id: Optional[str] = None
#     account_name: Optional[str] = None
#     appointment_status_c: Optional[str] = None
#     start_datetime: Optional[str] = None
#     end_datetime: Optional[str] = None
#     description: Optional[str] = None
#     created_by_name: Optional[str] = None
#     created_by_id: Optional[str] = None
#     last_modified_by_name: Optional[str] = None
#     last_modified_by_id: Optional[str] = None

# app = FastAPI()

# # Salesforce creds
# SALESFORCE_CONSUMER_KEY = os.getenv("SALESFORCE_CONSUMER_KEY")
# SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
# SALESFORCE_USERNAME = os.getenv("SALESFORCE_USERNAME")
# SALESFORCE_PASSWORD = os.getenv("SALESFORCE_PASSWORD")

# # Helpers

# def get_salesforce_access_token():
#     if not all([SALESFORCE_CONSUMER_KEY, SALESFORCE_CONSUMER_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD]):
#         raise HTTPException(500, "Missing Salesforce credentials")
#     resp = requests.post(
#         "https://login.salesforce.com/services/oauth2/token",
#         data={
#             "grant_type": "password",
#             "client_id": SALESFORCE_CONSUMER_KEY,
#             "client_secret": SALESFORCE_CONSUMER_SECRET,
#             "username": SALESFORCE_USERNAME,
#             "password": SALESFORCE_PASSWORD
#         }
#     )
#     if resp.status_code != 200:
#         raise HTTPException(401, "Salesforce authentication failed")
#     return resp.json()

# def build_markdown_local(events: List[EventOut]) -> str:
#     """Pure-Python fallback Markdown builder with specific columns."""
#     last_modified_by_id: Optional[str] = None
#     last_modified_by_id: Optional[str] = None
#     headers = ["id", "subject", "owner_id", "owner_name", "what_id", "what_name", "account_id", "account_name", "appointment_status_c", "start_datetime", "end_datetime", "description", "created_by_name", "created_by_id", "last_modified_by_name", "last_modified_by_id"]
#     lines = [
#         "| " + " | ".join(headers) + " |",
#         "| " + " | ".join(["---"] * len(headers)) + " |"
#     ]
#     for e in events:
#         row = []
#         for h in headers:
#             val = getattr(e, h) or ""
#             cell = str(val).replace("|", "\\|").replace("\n", " ")
#             row.append(cell)
#         lines.append("| " + " | ".join(row) + " |")
#     logger.debug(f"Local builder output: {lines}")
#     return "\n".join(lines)

# # Endpoint

# @app.get("/events/")
# async def get_events():
#     auth = get_salesforce_access_token()
#     token = auth["access_token"]
#     inst = auth["instance_url"]

#     headers = {
#         "Authorization": f"Bearer {token}",
#         "Content-Type": "application/json"
#     }

#     soql = (
#         "SELECT Id, Subject, OwnerId, WhatId, AccountId, Appointment_Status__c, StartDateTime, EndDateTime, Description, CreatedById, LastModifiedById, Owner.Name, What.Name, Account.Name,CreatedBy.Name, LastModifiedBy.Name FROM Event"
#     )
#     url = f"{inst}/services/data/v59.0/query?q={soql}"

#     sess = requests.Session()
#     retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
#     sess.mount("https://", HTTPAdapter(max_retries=retries))

#     events: List[EventOut] = []
#     while url:
#         resp = sess.get(url, headers=headers, timeout=30)
#         resp.raise_for_status()
#         page = resp.json()
#         logger.debug(f"Raw page data: {page}")  # Log raw response to check records
#         for rec in page.get("records", []):
#             owner = rec.get("Owner") or {}
#             what = rec.get("What") or {}
#             account = rec.get("Account") or {}
#             created_by = rec.get("CreatedBy") or {}
#             last_modified = rec.get("LastModifiedBy") or {}

#             event = EventOut(
#                 id=rec["Id"],
#                 subject=rec.get("Subject"),
#                 owner_id=rec.get("OwnerId"),
#                 owner_name=owner.get("Name"),
#                 what_id=rec.get("WhatId"),
#                 what_name=what.get("Name"),
#                 account_id=rec.get("AccountId"),
#                 account_name=account.get("Name"),
#                 appointment_status_c=rec.get("Appointment_Status__c"),
#                 start_datetime=rec.get("StartDateTime"),
#                 end_datetime=rec.get("EndDateTime"),
#                 description=rec.get("Description"),
#                 created_by_name=created_by.get("Name"),
#                 created_by_id=rec.get("CreatedById"),
#                 last_modified_by_name=last_modified.get("Name"),
#                 last_modified_by_id=rec.get("LastModifiedById"),
#             )
#             events.append(event)
#             logger.debug(f"Processed event: {event.dict()}")  # Log each event

#         nxt = page.get("nextRecordsUrl")
#         url = f"{inst}{nxt}" if nxt else None

#     logger.info(f"Fetched {len(events)} events total")
#     if not events:
#         logger.warning("No events fetched from Salesforce")
#         return Response(content="| id | subject | owner_id | owner_name | what_id | what_name | account_id | account_name | appointment_status_c |\n|---|---|---|---|---|---|---|---|---|", media_type="text/plain")
#     markdown = build_markdown_local(events)
#     return Response(content=markdown, media_type="text/plain")


#======================Add code middile ware and upload new code===================

# import os
# import json
# import logging
# from pathlib import Path
# from typing import List, Optional
# import requests
# from fastapi import FastAPI, HTTPException, Response
# from fastapi.openapi.utils import get_openapi
# from pydantic import BaseModel
# from dotenv import load_dotenv
# from urllib3.util.retry import Retry
# from requests.adapters import HTTPAdapter
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware

# # Load environment and configure logging
# load_dotenv()
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Pydantic model for event output
# class EventOut(BaseModel):
#     id: str
#     subject: Optional[str] = None
#     owner_id: Optional[str] = None
#     owner_name: Optional[str] = None
#     what_id: Optional[str] = None
#     what_name: Optional[str] = None
#     account_id: Optional[str] = None
#     account_name: Optional[str] = None
#     appointment_status_c: Optional[str] = None
#     start_datetime: Optional[str] = None
#     end_datetime: Optional[str] = None
#     description: Optional[str] = None
#     created_by_name: Optional[str] = None
#     created_by_id: Optional[str] = None
#     last_modified_by_name: Optional[str] = None
#     last_modified_by_id: Optional[str] = None

# # Configure FastAPI app
# app = FastAPI()

# # Add CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # or restrict to IBM's API Connect domains
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Salesforce credentials from environment
# SALESFORCE_CONSUMER_KEY = os.getenv("SALESFORCE_CONSUMER_KEY")
# SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
# SALESFORCE_USERNAME = os.getenv("SALESFORCE_USERNAME")
# SALESFORCE_PASSWORD = os.getenv("SALESFORCE_PASSWORD")

# # Helper to get Salesforce access token
# def get_salesforce_access_token():
#     if not all([SALESFORCE_CONSUMER_KEY, SALESFORCE_CONSUMER_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD]):
#         logger.error("Missing Salesforce credentials")
#         raise HTTPException(status_code=500, detail="Missing Salesforce credentials")
#     resp = requests.post(
#         "https://login.salesforce.com/services/oauth2/token",
#         data={
#             "grant_type": "password",
#             "client_id": SALESFORCE_CONSUMER_KEY,
#             "client_secret": SALESFORCE_CONSUMER_SECRET,
#             "username": SALESFORCE_USERNAME,
#             "password": SALESFORCE_PASSWORD
#         }
#     )
#     if resp.status_code != 200:
#         raise HTTPException(status_code=401, detail="Salesforce authentication failed")
#     return resp.json()

# # Build Markdown table for events
# def build_markdown_local(events: List[EventOut]) -> str:
#     headers = [
#         "id", "subject", "owner_id", "owner_name", "what_id", "what_name",
#         "account_id", "account_name", "appointment_status_c", "start_datetime",
#         "end_datetime", "description", "created_by_name", "created_by_id",
#         "last_modified_by_name", "last_modified_by_id"
#     ]
#     lines = [
#         "| " + " | ".join(headers) + " |",
#         "| " + " | ".join(["---"] * len(headers)) + " |"
#     ]
#     for e in events:
#         row = []
#         for h in headers:
#             val = getattr(e, h) or ""
#             cell = str(val).replace("|", "\\|").replace("\n", " ")
#             row.append(cell)
#         lines.append("| " + " | ".join(row) + " |")
#     return "\n".join(lines)

# # GET /events endpoint with logging and error handling
# @app.get("/events", response_class=Response, responses={200: {"content": {"text/plain": {}}}})
# async def get_events():
#     logger.info("Received request for /events")
#     try:
#         auth = get_salesforce_access_token()
#         token = auth["access_token"]
#         inst = auth["instance_url"]
#         headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

#         soql = (
#             "SELECT Id, Subject, OwnerId, WhatId, AccountId, Appointment_Status__c, StartDateTime,"
#             " EndDateTime, Description, CreatedById, LastModifiedById, Owner.Name, What.Name,"
#             " Account.Name, CreatedBy.Name, LastModifiedBy.Name FROM Event"
#         )
#         url = f"{inst}/services/data/v59.0/query?q={soql}"

#         sess = requests.Session()
#         retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
#         sess.mount("https://", HTTPAdapter(max_retries=retries))

#         events: List[EventOut] = []
#         while url:
#             resp = sess.get(url, headers=headers, timeout=30)
#             resp.raise_for_status()
#             page = resp.json()
#             for rec in page.get("records", []):
#                 owner = rec.get("Owner") or {}
#                 what = rec.get("What") or {}
#                 account = rec.get("Account") or {}
#                 created_by = rec.get("CreatedBy") or {}
#                 last_modified = rec.get("LastModifiedBy") or {}
#                 events.append(EventOut(
#                     id=rec["Id"],
#                     subject=rec.get("Subject"),
#                     owner_id=rec.get("OwnerId"),
#                     owner_name=owner.get("Name"),
#                     what_id=rec.get("WhatId"),
#                     what_name=what.get("Name"),
#                     account_id=rec.get("AccountId"),
#                     account_name=account.get("Name"),
#                     appointment_status_c=rec.get("Appointment_Status__c"),
#                     start_datetime=rec.get("StartDateTime"),
#                     end_datetime=rec.get("EndDateTime"),
#                     description=rec.get("Description"),
#                     created_by_name=created_by.get("Name"),
#                     created_by_id=rec.get("CreatedById"),
#                     last_modified_by_name=last_modified.get("Name"),
#                     last_modified_by_id=rec.get("LastModifiedById"),
#                 ))
#             nxt = page.get("nextRecordsUrl")
#             url = f"{inst}{nxt}" if nxt else None

#         if not events:
#             return Response(content="| id | subject | ... |\n|---|---|...|", media_type="text/plain")
#         return Response(content=build_markdown_local(events), media_type="text/plain")
#     except Exception as e:
#         logger.error(f"Error in /events: {str(e)}")
#         raise HTTPException(status_code=500, detail="Failed to fetch events")

# # Override OpenAPI schema for Watsonx Orchestrate skill
# def custom_openapi():
#     if app.openapi_schema:
#         return app.openapi_schema
#     schema = get_openapi(
#         title="Salesforce Events Skill",
#         version="1.0.0",
#         description="Fetch Salesforce events for Watsonx Orchestrate skill",
#         routes=app.routes,
#     )
#     # Ensure OpenAPI version supported by Orchestrate
#     schema["openapi"] = "3.0.3"
#     # IBM-specific metadata for skill
#     schema.setdefault("info", {})
#     schema["info"].update({
#         "x-ibm-application-name": "SalesforceEventsSkill",
#         "x-ibm-application-id": "salesforce_events_skill",
#         "x-ibm-skill-type": "rest",
#         "x-ibm-skill-subtype": "invoke",
#     })
#     # Configure server URL for Orchestrate to invoke your API
#     schema["servers"] = [{"url": "https://verbose-waffle-975gqpr9wvr927pqv-8000.app.github.dev"}]  # Replace with your actual URL
#     app.openapi_schema = schema
#     return schema

# # Apply custom OpenAPI
# app.openapi = custom_openapi

# if __name__ == "__main__":
#     # Generate OpenAPI file
#     schema = app.openapi()
#     Path("openapi.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
#     print("OpenAPI schema written to openapi.json")

# #=================================================================================


import os
import json
import logging
from pathlib import Path
from typing import List, Optional
import requests
from fastapi import FastAPI, HTTPException, Response
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from dotenv import load_dotenv
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from fastapi.middleware.cors import CORSMiddleware

# Load environment and configure logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic model for event output
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

# Configure FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Optionally restrict to trusted domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Salesforce credentials from environment
SALESFORCE_CONSUMER_KEY = os.getenv("SALESFORCE_CONSUMER_KEY")
SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
SALESFORCE_USERNAME = os.getenv("SALESFORCE_USERNAME")
SALESFORCE_PASSWORD = os.getenv("SALESFORCE_PASSWORD")

# Helper to get Salesforce access token
def get_salesforce_access_token():
    if not all([SALESFORCE_CONSUMER_KEY, SALESFORCE_CONSUMER_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD]):
        logger.error("Missing Salesforce credentials")
        raise HTTPException(status_code=500, detail="Missing Salesforce credentials")
    resp = requests.post(
        "https://login.salesforce.com/services/oauth2/token",
        data={
            "grant_type": "password",
            "client_id": SALESFORCE_CONSUMER_KEY,
            "client_secret": SALESFORCE_CONSUMER_SECRET,
            "username": SALESFORCE_USERNAME,
            "password": SALESFORCE_PASSWORD
        }
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Salesforce authentication failed")
    return resp.json()

# Build Markdown table for events
def build_markdown_local(events: List[EventOut]) -> str:
    headers = [
        "id", "subject", "owner_id", "owner_name", "what_id", "what_name",
        "account_id", "account_name", "appointment_status_c", "start_datetime",
        "end_datetime", "description", "created_by_name", "created_by_id",
        "last_modified_by_name", "last_modified_by_id"
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]
    for e in events:
        row = []
        for h in headers:
            val = getattr(e, h) or ""
            cell = str(val).replace("|", "\\|").replace("\n", " ")
            row.append(cell)
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)

# GET /events/ endpoint with logging and error handling
@app.get("/events", response_class=Response, responses={200: {"content": {"text/plain": {}}}})
async def get_events():
    logger.info("Received request for /events")
    try:
        auth = get_salesforce_access_token()
        token = auth["access_token"]
        inst = auth["instance_url"]
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        soql = (
            "SELECT Id, Subject, OwnerId, WhatId, AccountId, Appointment_Status__c, StartDateTime,"
            " EndDateTime, Description, CreatedById, LastModifiedById, Owner.Name, What.Name,"
            " Account.Name, CreatedBy.Name, LastModifiedBy.Name FROM Event"
        )
        url = f"{inst}/services/data/v59.0/query?q={soql}"

        sess = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        sess.mount("https://", HTTPAdapter(max_retries=retries))

        events: List[EventOut] = []
        while url:
            resp = sess.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            page = resp.json()
            for rec in page.get("records", []):
                owner = rec.get("Owner") or {}
                what = rec.get("What") or {}
                account = rec.get("Account") or {}
                created_by = rec.get("CreatedBy") or {}
                last_modified = rec.get("LastModifiedBy") or {}
                events.append(EventOut(
                    id=rec["Id"],
                    subject=rec.get("Subject"),
                    owner_id=rec.get("OwnerId"),
                    owner_name=owner.get("Name"),
                    what_id=rec.get("WhatId"),
                    what_name=what.get("Name"),
                    account_id=rec.get("AccountId"),
                    account_name=account.get("Name"),
                    appointment_status_c=rec.get("Appointment_Status__c"),
                    start_datetime=rec.get("StartDateTime"),
                    end_datetime=rec.get("EndDateTime"),
                    description=rec.get("Description"),
                    created_by_name=created_by.get("Name"),
                    created_by_id=rec.get("CreatedById"),
                    last_modified_by_name=last_modified.get("Name"),
                    last_modified_by_id=rec.get("LastModifiedById"),
                ))
            nxt = page.get("nextRecordsUrl")
            url = f"{inst}{nxt}" if nxt else None

        if not events:
            return Response(content="| id | subject | ... |\n|---|---|...|", media_type="text/plain")
        return Response(content=build_markdown_local(events), media_type="text/plain")
    except Exception as e:
        logger.error(f"Error in /events: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch events")

# Override OpenAPI schema for Watsonx Orchestrate skill
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="Salesforce Events Skill",
        version="1.0.0",
        description="Fetch Salesforce events for Watsonx Orchestrate skill",
        routes=app.routes,
    )
    schema["openapi"] = "3.0.3"
    schema.setdefault("info", {})
    schema["info"].update({
        "x-ibm-application-name": "SalesforceEventsSkill",
        "x-ibm-application-id": "salesforce_events_skill",
        "x-ibm-skill-type": "rest",
        "x-ibm-skill-subtype": "invoke",
    })
    # ✅ Corrected server URL
    schema["servers"] = [
        {"url": "https://didactic-disco-jj9vgv695wjg25wq-8000.app.github.dev"}
    ]
    app.openapi_schema = schema
    return schema

# Apply custom OpenAPI
app.openapi = custom_openapi

if __name__ == "__main__":
    # Generate OpenAPI file locally if needed
    schema = app.openapi()
    Path("openapi.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    print("OpenAPI schema written to openapi.json")
