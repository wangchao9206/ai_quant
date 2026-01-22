from __future__ import annotations

import datetime as _dt
import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import quote_plus

try:
    from bson import ObjectId
    from pymongo import MongoClient
    from pymongo.collection import ReturnDocument
    from pymongo.collection import Collection
    from pymongo.database import Database
    from pymongo.errors import OperationFailure
    from pymongo.errors import PyMongoError
except Exception:  # pragma: no cover
    MongoClient = None
    ObjectId = None
    Collection = None
    Database = None
    ReturnDocument = None
    OperationFailure = None
    PyMongoError = Exception

try:
    from mongita import MongitaClientDisk
except Exception:  # pragma: no cover
    MongitaClientDisk = None


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "quant_v2.db")


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(tz=_dt.timezone.utc)


def _parse_dt(value: Any) -> _dt.datetime:
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_dt.timezone.utc)
    if isinstance(value, (int, float)):
        return _dt.datetime.fromtimestamp(float(value), tz=_dt.timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return _utcnow()
        try:
            dt = _dt.datetime.fromisoformat(s)
            return dt if dt.tzinfo else dt.replace(tzinfo=_dt.timezone.utc)
        except Exception:
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S.%f",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
        ):
            try:
                dt = _dt.datetime.strptime(s, fmt)
                return dt.replace(tzinfo=_dt.timezone.utc)
            except Exception:
                continue
    return _utcnow()


def _maybe_json_load(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return value
    return value


def _to_object_id(value: str) -> Optional["ObjectId"]:
    if ObjectId is None:
        return None
    try:
        return ObjectId(value)
    except Exception:
        return None


def _is_int_str(value: str) -> bool:
    return value.isdigit() or (value.startswith("-") and value[1:].isdigit())


@dataclass(frozen=True)
class MongoConfig:
    uri: str
    database: str
    collection: str
    migrate_from_sqlite: bool


def _build_mongo_uri() -> str:
    uri = os.getenv("MONGODB_URI")
    if uri:
        return uri

    host = os.getenv("MONGODB_HOST", "localhost")
    port = os.getenv("MONGODB_PORT", "27017")

    username = os.getenv("MONGODB_USERNAME") or os.getenv("MONGODB_USER")
    password = os.getenv("MONGODB_PASSWORD") or os.getenv("MONGODB_PASS")
    if username and password:
        auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/"
            f"?authSource={quote_plus(auth_source)}"
        )

    return f"mongodb://{host}:{port}"


def get_mongo_config() -> MongoConfig:
    uri = _build_mongo_uri()
    database = os.getenv("MONGODB_DB", "quant")
    collection = os.getenv("MONGODB_COLLECTION", "backtest_records")
    migrate_from_sqlite = os.getenv("MONGODB_MIGRATE_FROM_SQLITE", "1") not in {"0", "false", "False"}
    return MongoConfig(uri=uri, database=database, collection=collection, migrate_from_sqlite=migrate_from_sqlite)


_mongo_client: Optional["MongoClient"] = None
_mongo_db: Optional["Database"] = None
_backtest_col: Optional["Collection"] = None
_counters_col: Optional["Collection"] = None


def init_mongo() -> None:
    global _mongo_client, _mongo_db, _backtest_col, _counters_col

    if MongoClient is None:
        raise RuntimeError("pymongo is not installed")

    cfg = get_mongo_config()

    use_fallback = os.getenv("MONGODB_FALLBACK_MONGITA", "1") not in {"0", "false", "False"}
    timeout_ms = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2000"))

    def _switch_to_mongita() -> None:
        nonlocal cfg
        if MongitaClientDisk is None:
            raise RuntimeError("mongita is not installed")
        base_dir = os.getenv(
            "MONGITA_PATH",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "mongita"),
        )
        os.makedirs(base_dir, exist_ok=True)
        client = MongitaClientDisk(base_dir)
        globals()["_mongo_client"] = client
        globals()["_mongo_db"] = client[cfg.database]
        globals()["_backtest_col"] = globals()["_mongo_db"][cfg.collection]
        globals()["_counters_col"] = globals()["_mongo_db"]["counters"]
    try:
        _mongo_client = MongoClient(cfg.uri, serverSelectionTimeoutMS=timeout_ms)
        _mongo_client.admin.command("ping")
        # Verify we can access the target database (catch auth errors early)
        # We use find_one because dbStats might be allowed for some users while read is not
        try:
             _mongo_client[cfg.database][cfg.collection].find_one({}, projection={"_id": 1})
        except OperationFailure:
             raise
        except Exception:
             # Ignore other errors here, they might be handled later or not critical for auth check
             pass

    except Exception as e:
        # Check if user explicitly provided credentials
        has_credentials = os.getenv("MONGODB_URI") or (os.getenv("MONGODB_USERNAME") and os.getenv("MONGODB_PASSWORD"))
        
        if OperationFailure is not None and isinstance(e, OperationFailure):
            # If credentials were explicitly provided but failed, raise error
            if has_credentials:
                raise RuntimeError(
                    "Mongo authentication failed with provided credentials. Please check MONGODB_USERNAME/MONGODB_PASSWORD."
                ) from e
            # If no credentials provided but auth required, we will try fallback below
            # (unless fallback is disabled)
            print(f"Warning: Local MongoDB requires authentication but none provided. Falling back to Mongita if enabled. Error: {e}")

        if not use_fallback or MongitaClientDisk is None:
            # If we can't fall back, and it was an auth error (or other error), re-raise
            if OperationFailure is not None and isinstance(e, OperationFailure) and not has_credentials:
                 raise RuntimeError(
                    "Mongo authentication failed and fallback is disabled/unavailable. "
                    "Set MONGODB_USERNAME/MONGODB_PASSWORD or enable Mongita."
                ) from e
            raise
            
        _switch_to_mongita()
        

    _mongo_db = _mongo_client[cfg.database]
    _backtest_col = _mongo_db[cfg.collection]
    _counters_col = _mongo_db["counters"]

    for args, kwargs in (
        (("legacy_id",), {"unique": True, "sparse": True}),
        (("timestamp",), {}),
        (("symbol",), {}),
        (([("return_rate", -1)],), {}),
        (([("total_trades", -1)],), {}),
    ):
        try:
            _backtest_col.create_index(*args, **kwargs)
        except Exception:
            pass

    if cfg.migrate_from_sqlite:
        try:
            migrate_sqlite_to_mongo_if_needed(DB_PATH)
        except Exception as e:
            # Check if it is an auth error (directly or wrapped)
            is_auth_error = False
            if OperationFailure is not None:
                if isinstance(e, OperationFailure):
                    is_auth_error = True
                elif isinstance(e, RuntimeError) and isinstance(e.__cause__, OperationFailure):
                    is_auth_error = True

            if (
                use_fallback
                and MongitaClientDisk is not None
                and is_auth_error
            ):
                _switch_to_mongita()
                migrate_sqlite_to_mongo_if_needed(DB_PATH)
                return
            raise


def get_backtest_collection() -> "Collection":
    if _backtest_col is None:
        init_mongo()
    if _backtest_col is None:
        raise RuntimeError("Mongo backtest collection is not initialized")
    return _backtest_col


def get_counters_collection() -> "Collection":
    if _counters_col is None:
        init_mongo()
    if _counters_col is None:
        raise RuntimeError("Mongo counters collection is not initialized")
    return _counters_col


def _next_sequence(name: str) -> int:
    col = get_counters_collection()
    try:
        doc = col.find_one_and_update(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        seq = doc.get("seq") if isinstance(doc, dict) else None
        return int(seq or 0)
    except Exception:
        col.update_one(
            {"_id": name},
            {"$inc": {"seq": 1}},
            upsert=True,
        )
        doc = col.find_one({"_id": name}) or {}
        return int(doc.get("seq") or 0)


def _set_sequence_min(name: str, minimum: int) -> None:
    col = get_counters_collection()
    col.update_one(
        {"_id": name, "seq": {"$lt": int(minimum)}},
        {"$set": {"seq": int(minimum)}},
        upsert=True,
    )


def _mongo_id_filter(record_id: Union[int, str]) -> Dict[str, Any]:
    if isinstance(record_id, int):
        return {"legacy_id": record_id}

    s = str(record_id).strip()
    if not s:
        return {"_id": None}

    if _is_int_str(s):
        return {"legacy_id": int(s)}

    oid = _to_object_id(s)
    if oid is not None:
        return {"_id": oid}
    return {"_id": None}


def _serialize_doc(doc: Dict[str, Any], *, include_big_fields: bool = True) -> Dict[str, Any]:
    out = dict(doc)
    out.pop("_id", None)
    legacy_id = out.get("legacy_id")
    if legacy_id is not None:
        out["id"] = legacy_id
    out.pop("legacy_id", None)
    if not include_big_fields:
        out.pop("logs", None)
        out.pop("equity_curve", None)
    return out


class BacktestStore:
    def __init__(self, collection: "Collection") -> None:
        self._col = collection

    def insert_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(record)
        payload.setdefault("timestamp", _utcnow())
        legacy_id = payload.get("legacy_id")
        if legacy_id is None:
            legacy_id = _next_sequence("backtest_records")
            payload["legacy_id"] = legacy_id
        payload["timestamp"] = _parse_dt(payload.get("timestamp"))
        payload["strategy_params"] = _maybe_json_load(payload.get("strategy_params"))
        payload["equity_curve"] = _maybe_json_load(payload.get("equity_curve")) or []
        payload["logs"] = _maybe_json_load(payload.get("logs")) or []

        try:
            self._col.insert_one(payload)
        except PyMongoError as e:
            raise RuntimeError(f"Mongo insert failed: {e}") from e

        doc = self._col.find_one({"legacy_id": legacy_id})
        if not doc:
            raise RuntimeError("Mongo insert failed: missing inserted document")
        return _serialize_doc(doc, include_big_fields=True)

    def get_record(self, record_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        doc = self._col.find_one(_mongo_id_filter(record_id))
        return _serialize_doc(doc, include_big_fields=True) if doc else None

    def delete_record(self, record_id: Union[int, str]) -> bool:
        res = self._col.delete_one(_mongo_id_filter(record_id))
        return bool(getattr(res, "deleted_count", 0))

    def list_history(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_return: Optional[float] = None,
        sort_by: str = "timestamp",
        order: str = "desc",
        include_big_fields: bool = False,
    ) -> Dict[str, Any]:
        flt: Dict[str, Any] = {}
        if symbol:
            flt["symbol"] = symbol
        if start_date or end_date:
            ts: Dict[str, Any] = {}
            if start_date:
                ts["$gte"] = _parse_dt(start_date)
            if end_date:
                ts["$lte"] = _parse_dt(end_date) + _dt.timedelta(days=1)
            flt["timestamp"] = ts
        if min_return is not None:
            flt["return_rate"] = {"$gte": float(min_return)}

        sort_field = "timestamp"
        if sort_by in {"return_rate", "sharpe_ratio", "max_drawdown"}:
            sort_field = sort_by
        direction = 1 if order == "asc" else -1

        projection = None
        if not include_big_fields:
            projection = {"logs": 0, "equity_curve": 0}

        total = int(self._col.count_documents(flt))
        cursor = self._col.find(flt, projection=projection).sort(sort_field, direction).skip(int(skip)).limit(int(limit))
        items = [_serialize_doc(doc, include_big_fields=include_big_fields) for doc in cursor]
        return {"total": total, "items": items}

    def export_records(
        self,
        *,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        min_return: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        flt: Dict[str, Any] = {}
        if symbol:
            flt["symbol"] = symbol
        if start_date or end_date:
            ts: Dict[str, Any] = {}
            if start_date:
                ts["$gte"] = _parse_dt(start_date)
            if end_date:
                ts["$lte"] = _parse_dt(end_date) + _dt.timedelta(days=1)
            flt["timestamp"] = ts
        if min_return is not None:
            flt["return_rate"] = {"$gte": float(min_return)}

        cursor = self._col.find(flt).sort("timestamp", -1)
        return [_serialize_doc(doc, include_big_fields=False) for doc in cursor]

    def top_records(self, *, min_return: float, min_trades: int, limit: int) -> List[Dict[str, Any]]:
        flt = {"return_rate": {"$gt": float(min_return)}, "total_trades": {"$gt": int(min_trades)}}
        cursor = self._col.find(flt, projection={"logs": 0, "equity_curve": 0}).sort("return_rate", -1).limit(int(limit))
        return [_serialize_doc(doc, include_big_fields=False) for doc in cursor]

    def get_records_by_ids(self, ids: List[int]) -> List[Dict[str, Any]]:
        cursor = self._col.find({"legacy_id": {"$in": [int(x) for x in ids]}})
        return [_serialize_doc(doc, include_big_fields=True) for doc in cursor]

    def stats(self) -> Dict[str, Any]:
        total_count = int(self._col.count_documents({}))
        if total_count == 0:
            return {
                "total_count": 0,
                "avg_return": 0,
                "avg_sharpe": 0,
                "avg_drawdown": 0,
                "positive_count": 0,
                "win_rate_avg": 0,
                "return_distribution": {"<-10%": 0, "-10%~0%": 0, "0%~10%": 0, "10%~30%": 0, ">30%": 0},
            }

        def _f(x: Any) -> float:
            try:
                return float(x or 0)
            except Exception:
                return 0.0

        try:
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "avg_return": {"$avg": "$return_rate"},
                        "avg_sharpe": {"$avg": "$sharpe_ratio"},
                        "avg_drawdown": {"$avg": "$max_drawdown"},
                        "win_rate_avg": {"$avg": "$win_rate"},
                        "positive_count": {"$sum": {"$cond": [{"$gt": ["$net_profit", 0]}, 1, 0]}},
                    }
                }
            ]
            agg = list(self._col.aggregate(pipeline))
            row = agg[0] if agg else {}

            def _count(flt: Dict[str, Any]) -> int:
                return int(self._col.count_documents(flt))

            return_dist = {
                "<-10%": _count({"return_rate": {"$lt": -10}}),
                "-10%~0%": _count({"return_rate": {"$gte": -10, "$lt": 0}}),
                "0%~10%": _count({"return_rate": {"$gte": 0, "$lt": 10}}),
                "10%~30%": _count({"return_rate": {"$gte": 10, "$lt": 30}}),
                ">30%": _count({"return_rate": {"$gte": 30}}),
            }

            return {
                "total_count": total_count,
                "avg_return": _f(row.get("avg_return")),
                "avg_sharpe": _f(row.get("avg_sharpe")),
                "avg_drawdown": _f(row.get("avg_drawdown")),
                "positive_count": int(row.get("positive_count") or 0),
                "win_rate_avg": _f(row.get("win_rate_avg")),
                "return_distribution": return_dist,
            }
        except Exception:
            sum_return = 0.0
            sum_sharpe = 0.0
            sum_drawdown = 0.0
            sum_win_rate = 0.0
            positive_count = 0

            dist = {"<-10%": 0, "-10%~0%": 0, "0%~10%": 0, "10%~30%": 0, ">30%": 0}
            cursor = self._col.find(
                {},
                projection={
                    "return_rate": 1,
                    "sharpe_ratio": 1,
                    "max_drawdown": 1,
                    "net_profit": 1,
                    "win_rate": 1,
                },
            )

            n = 0
            for doc in cursor:
                n += 1
                rr = _f(doc.get("return_rate"))
                sr = _f(doc.get("sharpe_ratio"))
                dd = _f(doc.get("max_drawdown"))
                wr = _f(doc.get("win_rate"))
                npf = _f(doc.get("net_profit"))

                sum_return += rr
                sum_sharpe += sr
                sum_drawdown += dd
                sum_win_rate += wr
                if npf > 0:
                    positive_count += 1

                if rr < -10:
                    dist["<-10%"] += 1
                elif rr < 0:
                    dist["-10%~0%"] += 1
                elif rr < 10:
                    dist["0%~10%"] += 1
                elif rr < 30:
                    dist["10%~30%"] += 1
                else:
                    dist[">30%"] += 1

            denom = float(n or 1)
            return {
                "total_count": int(n),
                "avg_return": sum_return / denom,
                "avg_sharpe": sum_sharpe / denom,
                "avg_drawdown": sum_drawdown / denom,
                "positive_count": positive_count,
                "win_rate_avg": sum_win_rate / denom,
                "return_distribution": dist,
            }


_store: Optional[BacktestStore] = None


def get_backtest_store() -> BacktestStore:
    global _store
    if _store is None:
        _store = BacktestStore(get_backtest_collection())
    return _store


def migrate_sqlite_to_mongo_if_needed(sqlite_path: str) -> None:
    if not os.path.exists(sqlite_path):
        return

    store = get_backtest_store()
    col = get_backtest_collection()

    try:
        existing = int(col.count_documents({}))
    except Exception:
        existing = 0
    if existing > 0:
        return

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_records'")
        if cur.fetchone() is None:
            return

        rows = conn.execute("SELECT * FROM backtest_records ORDER BY id ASC").fetchall()
        max_id = 0
        for r in rows:
            row = dict(r)
            legacy_id = int(row.get("id") or 0)
            max_id = max(max_id, legacy_id)
            doc = {
                "legacy_id": legacy_id,
                "timestamp": _parse_dt(row.get("timestamp")),
                "symbol": row.get("symbol"),
                "period": row.get("period"),
                "strategy_params": _maybe_json_load(row.get("strategy_params")),
                "initial_cash": row.get("initial_cash"),
                "final_value": row.get("final_value"),
                "net_profit": row.get("net_profit"),
                "return_rate": row.get("return_rate"),
                "sharpe_ratio": row.get("sharpe_ratio"),
                "max_drawdown": row.get("max_drawdown"),
                "total_trades": row.get("total_trades"),
                "win_rate": row.get("win_rate"),
                "is_optimized": row.get("is_optimized"),
                "equity_curve": _maybe_json_load(row.get("equity_curve")) or [],
                "logs": _maybe_json_load(row.get("logs")) or [],
            }
            try:
                store.insert_record(doc)
            except Exception:
                continue

        if max_id > 0:
            _set_sequence_min("backtest_records", max_id)
    finally:
        conn.close()
