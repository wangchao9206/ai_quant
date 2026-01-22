from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from core.tdx_client import tdx_client

router = APIRouter()

@router.get("/health")
async def tdx_health():
    """Check connection to TDX servers"""
    if tdx_client.connect():
        return {"status": "ok", "msg": "TDX Connected"}
    else:
        # Don't fail hard, just report status, but frontend expects 200 for 'health' usually?
        # Frontend code: await axios.get(..., { timeout: 1500 });
        # If it throws, tdxReady=false.
        # So we can return 503 or 500 if not connected.
        raise HTTPException(status_code=503, detail="TDX Connection Failed")

@router.get("/quote")
async def get_quote(code: str):
    """Get real-time quote for a single stock"""
    try:
        quotes = tdx_client.get_quotes([code])
        if not quotes:
            raise HTTPException(status_code=404, detail="Quote not found")
        return quotes[0]
    except Exception as e:
        print(f"Error fetching quote for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/batch-quote")
async def get_batch_quote(codes: Optional[str] = None, code: Optional[List[str]] = Query(None)):
    """Get real-time quotes for multiple stocks"""
    target_codes = []
    # Support ?codes=000001,600000
    if codes:
        target_codes.extend(codes.split(','))
    # Support ?code=000001&code=600000
    if code:
        target_codes.extend(code)
    
    target_codes = [c.strip() for c in target_codes if c.strip()]
    
    if not target_codes:
        return []

    try:
        return tdx_client.get_quotes(target_codes)
    except Exception as e:
        print(f"Batch quote error: {e}")
        # Return empty list on error for batch to allow partial UI rendering if possible, 
        # but usually empty list means no data.
        return []

@router.get("/kline")
async def get_kline(code: str, type: str = 'day'):
    """Get K-line data"""
    try:
        # Default to day if type is not provided or recognized by client
        bars = tdx_client.get_kline(code, type)
        return bars
    except Exception as e:
        print(f"Error fetching kline for {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
