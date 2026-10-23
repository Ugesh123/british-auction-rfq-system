from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone, timedelta

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import RFQ, AuctionConfig, Bid, ActivityLog
from app.schemas import RFQCreate, BidCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="British Auction RFQ API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://frontend-ebon-psi-57.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def as_utc(value: datetime) -> datetime:
    """Normalize database and request datetimes to UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_status(rfq):
    now = datetime.now(timezone.utc)
    close = as_utc(rfq.bid_close)
    forced = as_utc(rfq.forced_close)

    if now < as_utc(rfq.bid_start):
        return "SCHEDULED"
    if now < close:
        return "ACTIVE"
    if close >= forced:
        return "FORCE_CLOSED"
    return "CLOSED"


def get_latest_bids(db: Session, rfq_id: int):
    bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq_id)
        .order_by(Bid.created_at.desc(), Bid.id.desc())
        .all()
    )

    latest_by_supplier = {}
    for bid in bids:
        if bid.supplier_id not in latest_by_supplier:
            latest_by_supplier[bid.supplier_id] = bid

    return list(latest_by_supplier.values())


def get_ranking(db: Session, rfq_id: int):
    latest_bids = get_latest_bids(db, rfq_id)
    return sorted(
        latest_bids,
        key=lambda bid: (bid.total_price, bid.created_at, bid.id),
    )


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "message": "British Auction API is running",
    }


@app.get("/")
def root():
    return {"message": "British Auction RFQ API"}


@app.post("/rfqs", status_code=201)
def create_rfq(payload: RFQCreate, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    start = payload.bid_start
    close = payload.bid_close
    forced = payload.forced_close

    if not all(
        value.tzinfo is not None
        for value in (start, close, forced)
    ):
        raise HTTPException(
            status_code=422,
            detail="Timestamps must include a timezone, such as Z",
        )

    if as_utc(start) <= now:
        raise HTTPException(422, "bid_start must be in the future")
    if as_utc(close) <= as_utc(start):
        raise HTTPException(422, "bid_close must be after bid_start")
    if as_utc(forced) <= as_utc(close):
        raise HTTPException(422, "forced_close must be after bid_close")

    rfq = RFQ(
        name=payload.name,
        bid_start=start,
        bid_close=close,
        forced_close=forced,
        pickup_date=payload.pickup_date,
        status="ACTIVE",
    )

    rfq.config = AuctionConfig(
        trigger_window_x=payload.config.trigger_window_x,
        extension_y=payload.config.extension_y,
        trigger_type=payload.config.trigger_type,
    )

    try:
        db.add(rfq)
        db.commit()
        db.refresh(rfq)

        return {
            "id": rfq.id,
            "name": rfq.name,
            "bid_start": rfq.bid_start,
            "bid_close": rfq.bid_close,
            "forced_close": rfq.forced_close,
            "status": get_status(rfq),
        }
    except Exception:
        db.rollback()
        raise HTTPException(500, "Could not create RFQ")


@app.get("/rfqs")
def list_rfqs(db: Session = Depends(get_db)):
    rfqs = db.query(RFQ).order_by(RFQ.id.desc()).all()
    results = []

    for rfq in rfqs:
        ranking = get_ranking(db, rfq.id)
        lowest = ranking[0].total_price if ranking else None

        results.append({
            "id": rfq.id,
            "name": rfq.name,
            "current_lowest_bid": lowest,
            "bid_close": rfq.bid_close,
            "forced_close": rfq.forced_close,
            "status": get_status(rfq),
        })

    return results


@app.get("/rfqs/{rfq_id}")
def get_rfq_details(rfq_id: int, db: Session = Depends(get_db)):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()

    if not rfq:
        raise HTTPException(404, "RFQ not found")

    all_bids = (
        db.query(Bid)
        .filter(Bid.rfq_id == rfq_id)
        .order_by(Bid.total_price.asc(), Bid.created_at.asc(), Bid.id.asc())
        .all()
    )

    ranking = get_ranking(db, rfq_id)

    return {
        "id": rfq.id,
        "name": rfq.name,
        "bid_start": rfq.bid_start,
        "bid_close": rfq.bid_close,
        "forced_close": rfq.forced_close,
        "pickup_date": rfq.pickup_date,
        "status": get_status(rfq),
        "config": {
            "trigger_window_x": rfq.config.trigger_window_x,
            "extension_y": rfq.config.extension_y,
            "trigger_type": rfq.config.trigger_type,
        },
        "bids": [
            {
                "id": bid.id,
                "supplier_id": bid.supplier_id,
                "carrier_name": bid.carrier_name,
                "freight": bid.freight,
                "origin_charges": bid.origin_charges,
                "destination_charges": bid.destination_charges,
                "total_price": bid.total_price,
                "transit_time": bid.transit_time,
                "quote_validity": bid.quote_validity,
                "created_at": bid.created_at,
            }
            for bid in all_bids
        ],
        "ranking": [
            {
                "rank": index + 1,
                "supplier_id": bid.supplier_id,
                "carrier_name": bid.carrier_name,
                "total_price": bid.total_price,
            }
            for index, bid in enumerate(ranking)
        ],
        "activity_log": [
            {
                "event_type": log.event_type,
                "message": log.message,
                "old_close": log.old_close,
                "new_close": log.new_close,
                "created_at": log.created_at,
            }
            for log in (
                db.query(ActivityLog)
                .filter(ActivityLog.rfq_id == rfq_id)
                .order_by(ActivityLog.created_at.asc(), ActivityLog.id.asc())
                .all()
            )
        ],
    }


@app.post("/rfqs/{rfq_id}/bids", status_code=201)
def submit_bid(
    rfq_id: int,
    payload: BidCreate,
    db: Session = Depends(get_db),
):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()

    if not rfq:
        raise HTTPException(404, "RFQ not found")

    now = datetime.now(timezone.utc)
    start = as_utc(rfq.bid_start)
    close = as_utc(rfq.bid_close)
    forced = as_utc(rfq.forced_close)

    if now < start:
        raise HTTPException(400, "Auction has not started yet")

    if now >= close or now >= forced:
        raise HTTPException(400, "Auction is closed; bids are not accepted")

    # Capture the ranking before saving the new bid.
    previous_ranking = get_ranking(db, rfq_id)
    previous_rank_by_supplier = {
        bid.supplier_id: rank
        for rank, bid in enumerate(previous_ranking, start=1)
    }
    previous_l1 = (
        previous_ranking[0].supplier_id if previous_ranking else None
    )

    total_price = (
        payload.freight
        + payload.origin_charges
        + payload.destination_charges
    )

    previous_supplier_bid = (
        db.query(Bid)
        .filter(
            Bid.rfq_id == rfq_id,
            Bid.supplier_id == payload.supplier_id,
        )
        .order_by(Bid.created_at.desc(), Bid.id.desc())
        .first()
    )

    if (
        previous_supplier_bid
        and total_price >= previous_supplier_bid.total_price
    ):
        raise HTTPException(
            400,
            "Your new total bid must be lower than your previous bid",
        )

    bid = Bid(
        rfq_id=rfq_id,
        supplier_id=payload.supplier_id,
        carrier_name=payload.carrier_name,
        freight=payload.freight,
        origin_charges=payload.origin_charges,
        destination_charges=payload.destination_charges,
        total_price=total_price,
        transit_time=payload.transit_time,
        quote_validity=payload.quote_validity,
        created_at=now,
    )

    try:
        db.add(bid)
        db.flush()

        db.add(ActivityLog(
            rfq_id=rfq_id,
            event_type="BID_RECEIVED",
            message=(
                f"{payload.carrier_name} submitted a bid "
                f"with total price {total_price:.2f}"
            ),
            created_at=now,
        ))

        # Calculate ranking after saving the bid.
        new_ranking = get_ranking(db, rfq_id)
        new_rank_by_supplier = {
            item.supplier_id: rank
            for rank, item in enumerate(new_ranking, start=1)
        }
        new_l1 = new_ranking[0].supplier_id if new_ranking else None

        rank_changed = any(
            previous_rank_by_supplier.get(supplier_id)
            != new_rank_by_supplier.get(supplier_id)
            for supplier_id in (
                set(previous_rank_by_supplier)
                | set(new_rank_by_supplier)
            )
        )
        l1_changed = previous_l1 != new_l1

        # The trigger condition must occur within X minutes of closing.
        remaining_seconds = (close - now).total_seconds()
        inside_trigger_window = (
            0 < remaining_seconds
            <= rfq.config.trigger_window_x * 60
        )

        trigger_type = rfq.config.trigger_type
        should_extend = False
        reason = ""

        if inside_trigger_window:
            if trigger_type == "BID_RECEIVED":
                should_extend = True
                reason = "Bid received within the trigger window"
            elif trigger_type == "ANY_RANK_CHANGE" and rank_changed:
                should_extend = True
                reason = "Supplier ranking changed within the trigger window"
            elif trigger_type == "L1_CHANGE" and l1_changed:
                should_extend = True
                reason = "L1 supplier changed within the trigger window"

        old_close = close
        new_close = close

        if should_extend:
            proposed_close = close + timedelta(
                minutes=rfq.config.extension_y
            )
            new_close = min(proposed_close, forced)

            if new_close > close:
                rfq.bid_close = new_close.replace(tzinfo=None)
                db.add(ActivityLog(
                    rfq_id=rfq_id,
                    event_type="AUCTION_EXTENDED",
                    message=(
                        f"{reason}. Auction extended by "
                        f"{(new_close - old_close).total_seconds() / 60:g} "
                        "minutes."
                    ),
                    old_close=old_close.replace(tzinfo=None),
                    new_close=new_close.replace(tzinfo=None),
                    created_at=now,
                ))

        db.commit()
        db.refresh(bid)
        db.refresh(rfq)

        return {
            "message": "Bid submitted successfully",
            "bid_id": bid.id,
            "rfq_id": rfq.id,
            "supplier_id": bid.supplier_id,
            "total_price": bid.total_price,
            "rank": next(
                (
                    index + 1
                    for index, item in enumerate(new_ranking)
                    if item.supplier_id == bid.supplier_id
                ),
                None,
            ),
            "trigger_window_active": inside_trigger_window,
            "extension_triggered": bool(
                should_extend and new_close > old_close
            ),
            "extension_reason": (
                reason if should_extend and new_close > old_close else None
            ),
            "bid_close": rfq.bid_close,
            "forced_close": rfq.forced_close,
            "status": get_status(rfq),
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Could not submit bid: {str(exc)}",
        )
