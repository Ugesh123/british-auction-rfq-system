
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Date, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    bid_start = Column(DateTime(timezone=True), nullable=False)
    bid_close = Column(DateTime(timezone=True), nullable=False)
    forced_close = Column(DateTime(timezone=True), nullable=False)
    pickup_date = Column(Date, nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)

    config = relationship(
        "AuctionConfig", back_populates="rfq",
        uselist=False, cascade="all, delete-orphan"
    )
    bids = relationship(
        "Bid", back_populates="rfq",
        cascade="all, delete-orphan"
    )
    activity_logs = relationship(
        "ActivityLog", back_populates="rfq",
        cascade="all, delete-orphan"
    )


class AuctionConfig(Base):
    __tablename__ = "auction_configs"

    id = Column(Integer, primary_key=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), unique=True, nullable=False)
    trigger_window_x = Column(Integer, nullable=False)
    extension_y = Column(Integer, nullable=False)
    trigger_type = Column(String(30), nullable=False)

    rfq = relationship("RFQ", back_populates="config")


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=False)
    supplier_id = Column(String(100), nullable=False)
    carrier_name = Column(String(150), nullable=False)
    freight = Column(Float, nullable=False)
    origin_charges = Column(Float, default=0, nullable=False)
    destination_charges = Column(Float, default=0, nullable=False)
    total_price = Column(Float, nullable=False)
    transit_time = Column(String(100), nullable=False)
    quote_validity = Column(Date, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    rfq = relationship("RFQ", back_populates="bids")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True)
    rfq_id = Column(Integer, ForeignKey("rfqs.id"), nullable=False)
    event_type = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    old_close = Column(DateTime(timezone=True), nullable=True)
    new_close = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    rfq = relationship("RFQ", back_populates="activity_logs")
