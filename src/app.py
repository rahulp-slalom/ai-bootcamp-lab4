"""
Slalom Capabilities Management System API

A FastAPI application that enables Slalom consultants to register their
capabilities and manage consulting expertise across the organization.
"""

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="Slalom Capabilities Management API",
              description="API for managing consulting capabilities and consultant expertise")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-session-secret-change-me"),
    same_site="lax",
    https_only=False,
)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

CREDENTIALS_FILE = current_dir / "practice_leads.json"
SESSION_USER_KEY = "authenticated_user"

# In-memory capabilities database
capabilities = {
    "Cloud Architecture": {
        "description": "Design and implement scalable cloud solutions using AWS, Azure, and GCP",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["AWS Solutions Architect", "Azure Architect Expert"],
        "industry_verticals": ["Healthcare", "Financial Services", "Retail"],
        "capacity": 40,  # hours per week available across team
        "consultants": ["alice.smith@slalom.com", "bob.johnson@slalom.com"]
    },
    "Data Analytics": {
        "description": "Advanced data analysis, visualization, and machine learning solutions",
        "practice_area": "Technology", 
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Tableau Desktop Specialist", "Power BI Expert", "Google Analytics"],
        "industry_verticals": ["Retail", "Healthcare", "Manufacturing"],
        "capacity": 35,
        "consultants": ["emma.davis@slalom.com", "sophia.wilson@slalom.com"]
    },
    "DevOps Engineering": {
        "description": "CI/CD pipeline design, infrastructure automation, and containerization",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"], 
        "certifications": ["Docker Certified Associate", "Kubernetes Admin", "Jenkins Certified"],
        "industry_verticals": ["Technology", "Financial Services"],
        "capacity": 30,
        "consultants": ["john.brown@slalom.com", "olivia.taylor@slalom.com"]
    },
    "Digital Strategy": {
        "description": "Digital transformation planning and strategic technology roadmaps",
        "practice_area": "Strategy",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Digital Transformation Certificate", "Agile Certified Practitioner"],
        "industry_verticals": ["Healthcare", "Financial Services", "Government"],
        "capacity": 25,
        "consultants": ["liam.anderson@slalom.com", "noah.martinez@slalom.com"]
    },
    "Change Management": {
        "description": "Organizational change leadership and adoption strategies",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Prosci Certified", "Lean Six Sigma Black Belt"],
        "industry_verticals": ["Healthcare", "Manufacturing", "Government"],
        "capacity": 20,
        "consultants": ["ava.garcia@slalom.com", "mia.rodriguez@slalom.com"]
    },
    "UX/UI Design": {
        "description": "User experience design and digital product innovation",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Adobe Certified Expert", "Google UX Design Certificate"],
        "industry_verticals": ["Retail", "Healthcare", "Technology"],
        "capacity": 30,
        "consultants": ["amelia.lee@slalom.com", "harper.white@slalom.com"]
    },
    "Cybersecurity": {
        "description": "Information security strategy, risk assessment, and compliance",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["CISSP", "CISM", "CompTIA Security+"],
        "industry_verticals": ["Financial Services", "Healthcare", "Government"],
        "capacity": 25,
        "consultants": ["ella.clark@slalom.com", "scarlett.lewis@slalom.com"]
    },
    "Business Intelligence": {
        "description": "Enterprise reporting, data warehousing, and business analytics",
        "practice_area": "Technology",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Microsoft BI Certification", "Qlik Sense Certified"],
        "industry_verticals": ["Retail", "Manufacturing", "Financial Services"],
        "capacity": 35,
        "consultants": ["james.walker@slalom.com", "benjamin.hall@slalom.com"]
    },
    "Agile Coaching": {
        "description": "Agile transformation and team coaching for scaled delivery",
        "practice_area": "Operations",
        "skill_levels": ["Emerging", "Proficient", "Advanced", "Expert"],
        "certifications": ["Certified Scrum Master", "SAFe Agilist", "ICAgile Certified"],
        "industry_verticals": ["Technology", "Financial Services", "Healthcare"],
        "capacity": 20,
        "consultants": ["charlotte.young@slalom.com", "henry.king@slalom.com"]
    }
}

pending_registration_requests = []


class LoginRequest(BaseModel):
    username: str
    password: str


def load_user_credentials():
    if not CREDENTIALS_FILE.exists():
        return []

    with CREDENTIALS_FILE.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("users", [])


def verify_password(stored_hash: str, provided_password: str):
    try:
        algorithm, iterations, salt, digest = stored_hash.split("$", 3)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Invalid credential configuration") from exc

    if algorithm != "pbkdf2_sha256":
        raise HTTPException(status_code=500, detail="Unsupported password hash algorithm")

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        provided_password.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return hmac.compare_digest(candidate_digest, digest)


def get_user_by_username(username: str):
    users = load_user_credentials()
    for user in users:
        if user.get("username", "").lower() == username.lower():
            return user
    return None


def get_authenticated_user(request: Request):
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")
    return user


def require_practice_lead(request: Request):
    user = get_authenticated_user(request)
    if user.get("role") != "practice_lead":
        raise HTTPException(status_code=403, detail="Practice lead permissions are required")
    return user


def has_practice_area_permission(user, capability_name: str):
    capability = capabilities.get(capability_name)
    if not capability:
        return False

    if user.get("role") != "practice_lead":
        return False

    permitted_areas = user.get("practice_areas", [])
    if "*" in permitted_areas:
        return True

    return capability.get("practice_area") in permitted_areas


def find_pending_request(capability_name: str, email: str):
    return next(
        (
            request
            for request in pending_registration_requests
            if request["capability_name"] == capability_name
            and request["email"].lower() == email.lower()
        ),
        None,
    )


def is_consultant_registered(capability, email: str):
    return any(consultant.lower() == email.lower() for consultant in capability["consultants"])


def remove_consultant(capability, email: str):
    for consultant in capability["consultants"]:
        if consultant.lower() == email.lower():
            capability["consultants"].remove(consultant)
            return
    raise HTTPException(status_code=400, detail="Consultant is not registered for this capability")


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(request: Request, payload: LoginRequest):
    user = get_user_by_username(payload.username)
    if not user or not verify_password(user.get("password_hash", ""), payload.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    session_user = {
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "practice_areas": user.get("practice_areas", []),
    }
    request.session[SESSION_USER_KEY] = session_user

    return {
        "message": "Login successful",
        "user": session_user,
    }


@app.post("/auth/logout")
def logout(request: Request):
    request.session.pop(SESSION_USER_KEY, None)
    return {"message": "Logged out"}


@app.get("/auth/me")
def who_am_i(request: Request):
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        return {"authenticated": False, "user": None}
    return {"authenticated": True, "user": user}


@app.get("/capabilities")
def get_capabilities():
    return capabilities


@app.post("/capabilities/{capability_name}/register")
def register_for_capability(request: Request, capability_name: str, email: str):
    """Register a consultant for a capability or submit consultant request for approval."""
    authenticated_user = get_authenticated_user(request)

    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    # Get the specific capability
    capability = capabilities[capability_name]

    if is_consultant_registered(capability, email):
        raise HTTPException(
            status_code=400,
            detail="Consultant is already registered for this capability"
        )

    if authenticated_user["role"] == "consultant":
        if authenticated_user["email"].lower() != email.lower():
            raise HTTPException(
                status_code=403,
                detail="Consultants can only request registration for themselves",
            )

        if find_pending_request(capability_name, email):
            raise HTTPException(
                status_code=400,
                detail="A pending registration request already exists",
            )

        pending_registration_requests.append(
            {
                "capability_name": capability_name,
                "email": email,
                "requested_by": authenticated_user["username"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return {
            "message": (
                f"Registration request submitted for {email} on {capability_name}. "
                "A practice lead must approve it."
            )
        }

    if authenticated_user["role"] == "practice_lead":
        if not has_practice_area_permission(authenticated_user, capability_name):
            raise HTTPException(
                status_code=403,
                detail="You do not have permissions for this capability's practice area",
            )

        capability["consultants"].append(email)
        return {"message": f"Registered {email} for {capability_name}"}

    raise HTTPException(status_code=403, detail="Unsupported user role")


@app.delete("/capabilities/{capability_name}/unregister")
def unregister_from_capability(request: Request, capability_name: str, email: str):
    """Unregister a consultant from a capability"""
    authenticated_user = require_practice_lead(request)

    # Validate capability exists
    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    if not has_practice_area_permission(authenticated_user, capability_name):
        raise HTTPException(
            status_code=403,
            detail="You do not have permissions for this capability's practice area",
        )

    # Get the specific capability
    capability = capabilities[capability_name]

    # Remove consultant
    remove_consultant(capability, email)
    return {"message": f"Unregistered {email} from {capability_name}"}


@app.get("/registration-requests")
def get_registration_requests(request: Request):
    authenticated_user = require_practice_lead(request)

    if "*" in authenticated_user.get("practice_areas", []):
        return {"requests": pending_registration_requests}

    filtered_requests = [
        req
        for req in pending_registration_requests
        if capabilities.get(req["capability_name"], {}).get("practice_area")
        in authenticated_user.get("practice_areas", [])
    ]
    return {"requests": filtered_requests}


@app.post("/registration-requests/{capability_name}/approve")
def approve_registration_request(request: Request, capability_name: str, email: str):
    authenticated_user = require_practice_lead(request)

    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    if not has_practice_area_permission(authenticated_user, capability_name):
        raise HTTPException(
            status_code=403,
            detail="You do not have permissions for this capability's practice area",
        )

    pending_request = find_pending_request(capability_name, email)
    if not pending_request:
        raise HTTPException(status_code=404, detail="Pending registration request not found")

    capability = capabilities[capability_name]
    if not is_consultant_registered(capability, email):
        capability["consultants"].append(email)

    pending_registration_requests.remove(pending_request)
    return {"message": f"Approved registration for {email} on {capability_name}"}


@app.post("/registration-requests/{capability_name}/reject")
def reject_registration_request(request: Request, capability_name: str, email: str):
    authenticated_user = require_practice_lead(request)

    if capability_name not in capabilities:
        raise HTTPException(status_code=404, detail="Capability not found")

    if not has_practice_area_permission(authenticated_user, capability_name):
        raise HTTPException(
            status_code=403,
            detail="You do not have permissions for this capability's practice area",
        )

    pending_request = find_pending_request(capability_name, email)
    if not pending_request:
        raise HTTPException(status_code=404, detail="Pending registration request not found")

    pending_registration_requests.remove(pending_request)
    return {"message": f"Rejected registration request for {email} on {capability_name}"}
