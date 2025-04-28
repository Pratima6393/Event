
# #=================================================================================

# from fastapi import FastAPI, HTTPException
# from typing import List, Optional
# import requests
# from pydantic import BaseModel
# import os
# from dotenv import load_dotenv
# load_dotenv()
# # Define the EventOut model with the corrected fields
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
#     # Removed disposition_description_c as it doesn't exist
#     created_by_name: Optional[str] = None
#     created_by_id: Optional[str] = None
#     last_modified_by_name: Optional[str] = None
#     last_modified_by_id: Optional[str] = None

# app = FastAPI()

# # Salesforce credentials
# SALESFORCE_CONSUMER_KEY = os.getenv("SALESFORCE_CONSUMER_KEY")
# SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
# SALESFORCE_USERNAME = os.getenv("SALESFORCE_USERNAME")
# SALESFORCE_PASSWORD = os.getenv("SALESFORCE_PASSWORD")

# def get_salesforce_access_token():
#     auth_url = "https://login.salesforce.com/services/oauth2/token"
#     payload = {
#         "grant_type": "password",
#         "client_id": SALESFORCE_CONSUMER_KEY,
#         "client_secret": SALESFORCE_CONSUMER_SECRET,
#         "username": SALESFORCE_USERNAME,
#         "password": SALESFORCE_PASSWORD
#     }

#     response = requests.post(auth_url, data=payload)
#     if response.status_code != 200:
#         raise HTTPException(status_code=401, detail="Salesforce authentication failed")

#     auth_data = response.json()
#     return auth_data

# @app.get("/events/", response_model=List[EventOut])
# async def get_events():
#     try:
#         auth_data = get_salesforce_access_token()
#         access_token = auth_data["access_token"]
#         instance_url = auth_data["instance_url"]
#     except Exception as e:
#         raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

#     headers = {
#         "Authorization": f"Bearer {access_token}",
#         "Content-Type": "application/json"
#     }

#     query = (
#         "SELECT Id, Subject, OwnerId, WhatId, AccountId, "
#         "Appointment_Status__c, StartDateTime, EndDateTime, Description, "
#         "CreatedById, LastModifiedById, "
#         "Owner.Name, What.Name, Account.Name, CreatedBy.Name, LastModifiedBy.Name "
#         "FROM Event"
#     )

#     url = f"{instance_url}/services/data/v59.0/query?q={query}"
#     response = requests.get(url, headers=headers)
   
#     if response.status_code != 200:
#         raise HTTPException(
#             status_code=response.status_code, 
#             detail=f"Failed to fetch events from Salesforce: {response.text}"
#         )

#     records = response.json().get("records", [])
#     print(len(records))

#     events = []
#     for rec in records:
#         events.append(EventOut(
#             id=rec["Id"],
#             subject=rec.get("Subject"),
#             owner_id=rec.get("OwnerId"),
#             owner_name=rec.get("Owner", {}).get("Name") if rec.get("Owner") else None,
#             what_id=rec.get("WhatId"),
#             what_name=rec.get("What", {}).get("Name") if rec.get("What") else None,
#             account_id=rec.get("AccountId"),
#             account_name=rec.get("Account", {}).get("Name") if rec.get("Account") else None,
#             appointment_status_c=rec.get("Appointment_Status__c"),
#             start_datetime=rec.get("StartDateTime"),
#             end_datetime=rec.get("EndDateTime"),
#             description=rec.get("Description"),
#             created_by_name=rec.get("CreatedBy", {}).get("Name") if rec.get("CreatedBy") else None,
#             created_by_id=rec.get("CreatedById"),
#             last_modified_by_name=rec.get("LastModifiedBy", {}).get("Name") if rec.get("LastModifiedBy") else None,
#             last_modified_by_id=rec.get("LastModifiedById"),
#         ))

#     return events


from fastapi import FastAPI, HTTPException
from typing import List, Optional
import requests
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Define the EventOut model
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

# Salesforce credentials
SALESFORCE_CONSUMER_KEY = os.getenv("SALESFORCE_CONSUMER_KEY")
SALESFORCE_CONSUMER_SECRET = os.getenv("SALESFORCE_CONSUMER_SECRET")
SALESFORCE_USERNAME = os.getenv("SALESFORCE_USERNAME")
SALESFORCE_PASSWORD = os.getenv("SALESFORCE_PASSWORD")

def get_salesforce_access_token():
    auth_url = "https://login.salesforce.com/services/oauth2/token"
    payload = {
        "grant_type": "password",
        "client_id": SALESFORCE_CONSUMER_KEY,
        "client_secret": SALESFORCE_CONSUMER_SECRET,
        "username": SALESFORCE_USERNAME,
        "password": SALESFORCE_PASSWORD
    }

    response = requests.post(auth_url, data=payload)
    if response.status_code != 200:
        logger.error(f"Authentication failed: {response.text}")
        raise HTTPException(status_code=401, detail="Salesforce authentication failed")

    auth_data = response.json()
    return auth_data

@app.get("/events/", response_model=List[EventOut])
async def get_events():
    try:
        auth_data = get_salesforce_access_token()
        access_token = auth_data["access_token"]
        instance_url = auth_data["instance_url"]
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    query = (
        "SELECT Id, Subject, OwnerId, WhatId, AccountId, "
        "Appointment_Status__c, StartDateTime, EndDateTime, Description, "
        "CreatedById, LastModifiedById, "
        "Owner.Name, What.Name, Account.Name, CreatedBy.Name, LastModifiedBy.Name "
        "FROM Event"
    )

    events = []
    url = f"{instance_url}/services/data/v59.0/query?q={query}"
    max_retries = 3
    retry_delay = 2  # seconds

    while url:
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching URL: {url}")
                response = requests.get(url, headers=headers)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch events: Status {response.status_code}, Response: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Failed to fetch events from Salesforce: {response.text}"
                    )

                data = response.json()
                records = data.get("records", [])
                logger.info(f"Fetched {len(records)} records in this batch")

                for rec in records:
                    events.append(EventOut(
                        id=rec["Id"],
                        subject=rec.get("Subject"),
                        owner_id=rec.get("OwnerId"),
                        owner_name=rec.get("Owner", {}).get("Name") if rec.get("Owner") else None,
                        what_id=rec.get("WhatId"),
                        what_name=rec.get("What", {}).get("Name") if rec.get("What") else None,
                        account_id=rec.get("AccountId"),
                        account_name=rec.get("Account", {}).get("Name") if rec.get("Account") else None,
                        appointment_status_c=rec.get("Appointment_Status__c"),
                        start_datetime=rec.get("StartDateTime"),
                        end_datetime=rec.get("EndDateTime"),
                        description=rec.get("Description"),
                        created_by_name=rec.get("CreatedBy", {}).get("Name") if rec.get("CreatedBy") else None,
                        created_by_id=rec.get("CreatedById"),
                        last_modified_by_name=rec.get("LastModifiedBy", {}).get("Name") if rec.get("LastModifiedBy") else None,
                        last_modified_by_id=rec.get("LastModifiedById"),
                    ))

                # Check for next page
                next_url = data.get("nextRecordsUrl")
                if next_url:
                    # If nextRecordsUrl is relative, prepend instance_url
                    if next_url.startswith("/"):
                        url = f"{instance_url}{next_url}"
                    else:
                        url = next_url
                    logger.info(f"Next page URL: {url}")
                else:
                    url = None
                    logger.info("No more records to fetch")
                break  # Exit retry loop on success

            except requests.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt + 1 == max_retries:
                    raise HTTPException(status_code=500, detail=f"Failed after {max_retries} retries: {str(e)}")
                time.sleep(retry_delay)

    logger.info(f"Total events fetched: {len(events)}")
    return events