import logging
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import PyMongoError
from .config import settings

logger = logging.getLogger("climate_analyzer.db")

_client = None
_db = None
_db_initialized = False
_db_status = "uninitialized"

_memory_weather = {}    # key: (location_key, date) -> dict
_memory_analysis = {}   # key: analysis_key -> dict

def get_db():
    global _client, _db, _db_initialized, _db_status
    if not settings.mongodb_uri:
        _db_status = "memory-cache-dev-mode"
        return None

    if _db_initialized:
        return _db

    try:
        # Connect with short timeout so failing remote Atlas strings don't hang requests
        _client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2500)
        _client.admin.command("ping")
        _db = _client[settings.mongodb_database]
        _db.weather_records.create_index(
            [("locationKey", ASCENDING), ("date", ASCENDING)], unique=True
        )
        _db.analysis_results.create_index([("analysisKey", ASCENDING)], unique=True)
        _db.cache_metadata.create_index([("cacheKey", ASCENDING)], unique=True)
        _db_status = "connected"
        _db_initialized = True
        logger.info("Successfully connected to MongoDB.")
        return _db
    except Exception as exc:
        logger.warning(f"MongoDB connection failed: {exc}. Falling back to in-memory caching.")
        _db = None
        _db_status = "memory-cache-fallback"
        _db_initialized = True
        return None

def get_db_status() -> str:
    get_db()
    return _db_status

def get_cache_stats() -> dict:
    return {
        "weather_records_count": len(_memory_weather),
        "cached_analyses_count": len(_memory_analysis),
        "db_mode": get_db_status()
    }

def get_weather_records(location_key: str, start_date: str, end_date: str) -> list[dict]:
    db = get_db()
    if db is not None:
        try:
            records = list(db.weather_records.find(
                {"locationKey": location_key, "date": {"$gte": start_date, "$lte": end_date}},
                {"_id": 0}
            ).sort("date", ASCENDING))
            if records:
                return records
        except PyMongoError as err:
            logger.warning(f"MongoDB query failed, checking memory fallback: {err}")

    # Fallback / dev in-memory store
    return sorted(
        [v for (loc, day), v in _memory_weather.items()
         if loc == location_key and start_date <= day <= end_date],
        key=lambda r: r["date"]
    )

def save_weather_records(location_key: str, records: list[dict], source: str = "open-meteo"):
    db = get_db()
    docs = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for record in records:
        doc = {
            "locationKey": location_key,
            "date": record["date"],
            "tmax_c": record.get("tmax_c"),
            "prcp_mm": record.get("prcp_mm"),
            "source": source,
            "updatedAt": now_iso,
        }
        docs.append(doc)
        # Always mirror in memory for fast fallback
        _memory_weather[(location_key, record["date"])] = doc

    if db is not None and docs:
        try:
            from pymongo import UpdateOne
            db.weather_records.bulk_write([
                UpdateOne(
                    {"locationKey": d["locationKey"], "date": d["date"]},
                    {"$set": d},
                    upsert=True
                ) for d in docs
            ], ordered=False)
            db.cache_metadata.update_one(
                {"cacheKey": f"weather:{location_key}"},
                {"$set": {
                    "cacheKey": f"weather:{location_key}",
                    "fetchedAt": now_iso,
                    "source": source,
                    "recordsCount": len(docs),
                }},
                upsert=True
            )
        except PyMongoError as err:
            logger.warning(f"MongoDB bulk save error: {err}. Kept in memory cache.")

def get_cached_analysis(analysis_key: str) -> dict | None:
    db = get_db()
    if db is not None:
        try:
            cached = db.analysis_results.find_one({"analysisKey": analysis_key}, {"_id": 0})
            if cached:
                return cached
        except PyMongoError as err:
            logger.warning(f"MongoDB analysis cache read error: {err}")
    return _memory_analysis.get(analysis_key)

def save_analysis(analysis_key: str, result: dict):
    doc = {"analysisKey": analysis_key, **result}
    _memory_analysis[analysis_key] = doc

    db = get_db()
    if db is not None:
        try:
            db.analysis_results.update_one(
                {"analysisKey": analysis_key},
                {"$set": doc},
                upsert=True
            )
        except PyMongoError as err:
            logger.warning(f"MongoDB analysis cache write error: {err}")
