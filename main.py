import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Calendar, CalendarPage

app = FastAPI(title="Personalized Calendar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join("uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

class CalendarCreate(BaseModel):
    title: str
    year: int
    start_month: int = 1
    style: str = "classic"
    owner: Optional[str] = None

@app.get("/")
def root():
    return {"message": "Calendar backend running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            response["database_name"] = getattr(db, 'name', '✅ Connected')
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response

# ------- Uploads -------
@app.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    ext = os.path.splitext(file.filename)[1]
    safe_name = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}{ext}"
    path = os.path.join(UPLOAD_DIR, safe_name)
    with open(path, 'wb') as f:
        f.write(await file.read())
    return {"url": f"/uploads/{safe_name}"}

@app.get("/uploads/{filename}")
async def get_uploaded_file(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path)

# ------- Calendars -------
@app.post("/calendars")
async def create_calendar(payload: CalendarCreate):
    # initialize pages for 12 months starting at start_month
    pages: List[CalendarPage] = []
    for i in range(12):
        month = ((payload.start_month - 1 + i) % 12) + 1
        pages.append(CalendarPage(month=month))
    cal = Calendar(
        title=payload.title,
        year=payload.year,
        start_month=payload.start_month,
        style=payload.style,
        pages=pages,
        owner=payload.owner
    )
    inserted_id = create_document("calendar", cal)
    return {"id": inserted_id}

@app.get("/calendars")
async def list_calendars(limit: int = 50):
    docs = get_documents("calendar", {}, limit)
    # Convert ObjectId to string
    for d in docs:
        if "_id" in d:
            d["id"] = str(d.pop("_id"))
    return docs

class PageUpdate(BaseModel):
    image_url: Optional[str] = None
    note: Optional[str] = None

@app.put("/calendars/{calendar_id}/pages/{month}")
async def update_calendar_page(calendar_id: str, month: int, payload: PageUpdate):
    from bson import ObjectId
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be 1..12")
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        oid = ObjectId(calendar_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid calendar id")

    doc = db["calendar"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Calendar not found")

    pages = doc.get("pages", [])
    # find page index
    idx = next((i for i, p in enumerate(pages) if p.get("month") == month), None)
    if idx is None:
        pages.append({"month": month})
        idx = len(pages) - 1
    # update fields
    if payload.image_url is not None:
        pages[idx]["image_url"] = payload.image_url
    if payload.note is not None:
        pages[idx]["note"] = payload.note

    db["calendar"].update_one({"_id": oid}, {"$set": {"pages": pages, "updated_at": datetime.utcnow()}})

    return {"status": "ok"}

# Simple print-to-PDF placeholder route (frontend will handle printable view)
@app.get("/calendars/{calendar_id}")
async def get_calendar(calendar_id: str):
    from bson import ObjectId
    if db is None:
        raise HTTPException(status_code=500, detail="Database not available")
    try:
        oid = ObjectId(calendar_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid calendar id")

    doc = db["calendar"].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Calendar not found")
    doc["id"] = str(doc.pop("_id"))
    return doc

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
