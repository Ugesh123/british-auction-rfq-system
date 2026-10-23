# British Auction RFQ System
Live demo: https://frontend-ebon-psi-57.vercel.app (the backend is on Render’s free tier, so the first load may take about a minute)
A full-stack application for managing Requests for Quotation (RFQs) using a British auction bidding mechanism.

## Features

- Create and view RFQs.
- Configure auction start and closing times.
- Support three extension triggers: `BID_RECEIVED`, `ANY_RANK_CHANGE`, and `L1_CHANGE`.
- Automatically extend auctions when configured trigger conditions are met.
- Enforce a maximum forced-close time.
- Track supplier bids, rankings, and auction activity.
- Reject bids after the auction closes.
- Require suppliers to lower their previous bid.

## Tech Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI
- **Database:** SQLite, SQLAlchemy
- **Testing:** Pytest

## Prerequisites

- Python 3.13+
- Node.js and npm

## Backend Setup

From the project root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000

API documentation: http://127.0.0.1:8000/docs

## Frontend Setup

Open a second terminal from the project root:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

## Run Tests

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest tests/test_auctions.py -v
```

## Auction Extension Logic

When the configured trigger occurs within the defined time window before closing, the auction closing time may be extended. The extension must not exceed the forced-close time.

The system validates auction status and ensures each supplier's new bid is lower than their previous bid.

## Project Structure

- `backend/app/` — API routes, database configuration, models, and schemas
- `backend/tests/` — automated backend tests
- `frontend/src/` — React application and styles
- `docs/` — system design and database documentation
