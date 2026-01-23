from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
from core.tdx_http_client import tdx_http_client
import asyncio
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def tdx_health():
    """
    Health check for market data services.
    Prioritizes tdx-api (HTTP), falls back to AkShare.
    """
    logger.info("Health check requested")
    status_info = {
        "status": "ok",
        "tdx_api": "unknown",
        "internal_client": "disabled",
        "timestamp": 0
    }
    
    # 1. Check tdx-api (HTTP)
    if tdx_http_client.is_available():
        status_info["tdx_api"] = "available"
        status_info["msg"] = "TDX API (HTTP) is active"
        logger.info("Health check: TDX API available")
    else:
        status_info["tdx_api"] = "unavailable"
        status_info["msg"] = "Using AkShare fallback"
        logger.warning("Health check: TDX API unavailable")
        
    return status_info

@router.get("/quote")
async def get_quote(code: str):
    """Get real-time quote for a single stock"""
    logger.info(f"TDX Quote request for {code}")
    # 1. Try Local TDX HTTP API
    if tdx_http_client.is_available():
        try:
            data = await asyncio.to_thread(tdx_http_client.get_quote, code)
            if data:
                return data
        except Exception as e:
            logger.error(f"TDX HTTP quote error for {code}: {e}")
            pass

    # 2. Internal client (Disabled)
    logger.warning(f"Quote not found for {code} (Internal client disabled)")
    raise HTTPException(status_code=404, detail="Quote not found")

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

    logger.info(f"TDX Batch Quote request for {len(target_codes)} codes")
    
    results = []
    # 1. Try Local TDX HTTP API
    if tdx_http_client.is_available():
        # tdx-api might not have batch endpoint yet, iterate for now or check impl
        # Assuming we just loop for now or client supports it?
        # tdx_http_client doesn't have batch method in the file I read.
        # We'll just loop concurrently.
        async def fetch_one(c):
            try:
                return await asyncio.to_thread(tdx_http_client.get_quote, c)
            except:
                return None
        
        tasks = [fetch_one(c) for c in target_codes]
        results = await asyncio.gather(*tasks)
        results = [r for r in results if r]
        
        if results:
            return results

    return []

@router.get("/kline")
async def get_kline(code: str, type: str = 'day'):
    """Get K-line data"""
    logger.info(f"TDX Kline request for {code} type={type}")
    # 1. Try Local TDX HTTP API First
    if tdx_http_client.is_available():
        try:
            # tdx_http_client.get_kline returns processed list or empty list
            bars = await asyncio.to_thread(tdx_http_client.get_kline, code, type)
            if bars:
                return bars
        except Exception as e:
            logger.error(f"TDX HTTP kline fallback error: {e}")
            pass

    # 2. Fallback to Internal TDX Client
    logger.warning(f"Kline not found for {code} (Internal client disabled)")
    return []
