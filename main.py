
#=================================================================================

from fastapi import FastAPI, HTTPException
from typing import List, Optional
import requests
from pydantic import BaseModel

# Define the EventOut model with the corrected fields
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
    # Removed disposition_description_c as it doesn't exist
    created_by_name: Optional[str] = None
    created_by_id: Optional[str] = None
    last_modified_by_name: Optional[str] = None
    last_modified_by_id: Optional[str] = None

app = FastAPI()

# Salesforce credentials
SALESFORCE_CONSUMER_KEY = "3MVG9wt4IL4O5wvKmuWykzw13DGFOnjtd2q0MhKTvjQRdylQtrxmuTnEq4i2_.s6sQSQ5YJMl.1n_ScCpSDSP"
SALESFORCE_CONSUMER_SECRET = "B7143F5B5BEA70B22F037608F6FDCD818AFEFDC88CD1588FB0608720471E9369"
SALESFORCE_USERNAME = "impwatson@gadieltechnologies.com"
SALESFORCE_PASSWORD = "Wave@#123456"

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
        raise HTTPException(status_code=401, detail="Salesforce authentication failed")

    auth_data = response.json()
    return auth_data

@app.get("/events/", response_model=List[EventOut])
async def get_events():
    # Get fresh token every time to avoid token expiration issues
    try:
        auth_data = get_salesforce_access_token()
        access_token = auth_data["access_token"]
        instance_url = auth_data["instance_url"]
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    # Modified SOQL query - removed Disposition_Description__c field
    query = (
        "SELECT Id, Subject, OwnerId, WhatId, AccountId, "
        "Appointment_Status__c, StartDateTime, EndDateTime, Description, "
        "CreatedById, LastModifiedById, "
        "Owner.Name, What.Name, Account.Name, CreatedBy.Name, LastModifiedBy.Name "
        "FROM Event LIMIT 5"
    )

    url = f"{instance_url}/services/data/v59.0/query?q={query}"
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code, 
            detail=f"Failed to fetch events from Salesforce: {response.text}"
        )

    records = response.json().get("records", [])

    events = []
    for rec in records:
        # Access related objects correctly using relationship names
        events.append(EventOut(
            id=rec["Id"],
            subject=rec.get("Subject"),
            owner_id=rec.get("OwnerId"),
            owner_name=rec.get("Owner", {}).get("Name") if "Owner" in rec else None,
            what_id=rec.get("WhatId"),
            what_name=rec.get("What", {}).get("Name") if "What" in rec else None,
            account_id=rec.get("AccountId"),
            account_name=rec.get("Account", {}).get("Name") if "Account" in rec else None,
            appointment_status_c=rec.get("Appointment_Status__c"),
            start_datetime=rec.get("StartDateTime"),
            end_datetime=rec.get("EndDateTime"),
            description=rec.get("Description"),
            # Removed disposition_description_c field
            created_by_name=rec.get("CreatedBy", {}).get("Name") if "CreatedBy" in rec else None,
            created_by_id=rec.get("CreatedById"),
            last_modified_by_name=rec.get("LastModifiedBy", {}).get("Name") if "LastModifiedBy" in rec else None,
            last_modified_by_id=rec.get("LastModifiedById"),
        ))

    return events

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)