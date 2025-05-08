from pydantic import BaseModel, Field


from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class InvoiceLineItem(BaseModel):
    item_description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    tax_rate: Optional[float] = None
    total_amount: Optional[float] = None
    line_number: Optional[int] = None


class InvoiceObject(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    invoice_amount: Optional[float] = None
    seller: Optional[str] = None
    seller_tax_id: Optional[str] = None
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    

class InvoiceWrapper(BaseModel):
    id: str
    filename: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)    
    comment: Optional[str] = None
    json_content: Optional[str] = None    
    structured: Optional[InvoiceObject] = None
    error: Optional[list] = Field(default_factory=list)

