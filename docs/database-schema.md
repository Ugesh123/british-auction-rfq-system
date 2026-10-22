# Database Schema — British Auction RFQ System

## 1. RFQ

Stores the buyer's Request for Quotation and auction schedule.

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `name` | RFQ name |
| `bid_start` | Auction start time |
| `bid_close` | Current auction closing time |
| `forced_close` | Maximum permitted closing time |
| `pickup_date` | Pickup date |
| `status` | Auction status |

## 2. AuctionConfig

Stores the rules used to trigger auction extensions.

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `rfq_id` | Associated RFQ |
| `trigger_window_x` | Trigger window in minutes |
| `extension_y` | Extension duration in minutes |
| `trigger_type` | Configured extension trigger |

Supported trigger types are `BID_RECEIVED`, `ANY_RANK_CHANGE`, and `L1_CHANGE`.

## 3. Bid

Stores supplier bids submitted against an RFQ.

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `rfq_id` | Associated RFQ |
| `supplier_id` | Supplier identifier |
| `carrier_name` | Supplier or carrier name |
| `freight` | Freight charge |
| `origin_charges` | Origin charges |
| `destination_charges` | Destination charges |
| `total_price` | Total bid price |
| `transit_time` | Transit time |
| `quote_validity` | Quote validity |
| `created_at` | Bid submission timestamp |

## 4. ActivityLog

Records important auction events.

| Column | Purpose |
|---|---|
| `id` | Primary key |
| `rfq_id` | Associated RFQ |
| `event_type` | Type of event |
| `message` | Event description |
| `old_close` | Previous closing time, when applicable |
| `new_close` | Updated closing time, when applicable |
| `created_at` | Event timestamp |

## 5. Relationships

- One RFQ can have one auction configuration.
- One RFQ can have multiple bids.
- One RFQ can have multiple activity-log entries.
- Each bid and activity-log entry belongs to an RFQ.

