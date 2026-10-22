# High-Level Design — British Auction RFQ System

## 1. Overview

The British Auction RFQ System enables buyers to create Requests for Quotation (RFQs) and suppliers to submit competitive bids. Auctions can automatically extend their closing time when configured bidding activity occurs near the deadline.

## 2. Architecture

The application uses a three-layer architecture:

1. **Frontend:** React and TypeScript provide the RFQ dashboard and auction details interface.
2. **Backend API:** FastAPI handles RFQ creation, bid submission, ranking, auction status, and closing-time extensions.
3. **Database:** SQLite stores RFQs, auction configurations, supplier bids, and activity logs using SQLAlchemy.

### Request Flow

```text
User
 |
 v
React + TypeScript Frontend
 |
 | HTTP requests
 v
FastAPI Backend
 |
 | SQLAlchemy
 v
SQLite Database
```

## 3. Core Components

### RFQ Management

- Create RFQs with auction start and closing times.
- Configure the extension trigger, trigger window, extension duration, and forced-close time.
- Retrieve RFQ lists and individual RFQ details.

### Bid Management

- Accept bids only while the auction is active.
- Validate bid amounts and supplier bid history.
- Calculate supplier rankings using total bid price.
- Record bid activity.

### Auction Extension Engine

The backend evaluates the configured trigger when a bid is submitted.

Supported triggers:

- `BID_RECEIVED`: a new bid is submitted within the trigger window.
- `ANY_RANK_CHANGE`: supplier rankings change.
- `L1_CHANGE`: the lowest-ranked supplier changes.

When a configured trigger is satisfied, the closing time is extended by the configured duration, subject to the forced-close limit.

### Activity Logging

The system records bid submissions and auction extensions for traceability.

## 4. API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check |
| POST | `/rfqs` | Create an RFQ |
| GET | `/rfqs` | List RFQs |
| GET | `/rfqs/{rfq_id}` | Retrieve RFQ details and bids |
| POST | `/rfqs/{rfq_id}/bids` | Submit a supplier bid |

## 5. Validation and Error Handling

- Reject invalid auction time configurations.
- Reject bids before auction start or after closing.
- Require a supplier's new bid to be lower than their previous bid.
- Prevent extensions beyond the forced-close time.
- Return appropriate HTTP errors for invalid operations.

## 6. Testing

Backend tests cover health checks, RFQ creation, trigger validation, auction extensions, forced-close limits, closed-auction bid rejection, and supplier bid validation.

## 7. Technology Stack

- React
- TypeScript
- FastAPI
- SQLAlchemy
- SQLite
- Pytest
