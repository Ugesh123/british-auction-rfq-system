
from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator


ALLOWED_TRIGGERS = {
    "BID_RECEIVED",
    "ANY_RANK_CHANGE",
    "L1_CHANGE",
}


class AuctionConfigCreate(BaseModel):
    trigger_window_x: int = Field(gt=0)
    extension_y: int = Field(gt=0)
    trigger_type: str

    @model_validator(mode="after")
    def validate_trigger(self):
        if self.trigger_type not in ALLOWED_TRIGGERS:
            raise ValueError(
                f"trigger_type must be one of {sorted(ALLOWED_TRIGGERS)}"
            )
        return self


class RFQCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    bid_start: datetime
    bid_close: datetime
    forced_close: datetime
    pickup_date: date
    config: AuctionConfigCreate

    @model_validator(mode="after")
    def validate_times(self):
        if self.bid_close <= self.bid_start:
            raise ValueError("bid_close must be after bid_start")
        if self.forced_close <= self.bid_close:
            raise ValueError("forced_close must be after bid_close")
        return self


class BidCreate(BaseModel):
    supplier_id: str = Field(min_length=1, max_length=100)
    carrier_name: str = Field(min_length=1, max_length=150)
    freight: float = Field(ge=0)
    origin_charges: float = Field(default=0, ge=0)
    destination_charges: float = Field(default=0, ge=0)
    transit_time: str = Field(min_length=1, max_length=100)
    quote_validity: date

    @model_validator(mode="after")
    def validate_total(self):
        total = self.freight + self.origin_charges + self.destination_charges
        if total < 0:
            raise ValueError("Total price cannot be negative")
        return self
