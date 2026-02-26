import logging
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)

# Country name in Thai for the API query parameter
CT_TN = "ราชอาณาจักรไทย"

# Satellite name mapping based on "satellite" property
SATELLITE_MAP = {
    "N": "Suomi NPP",
    "N20": "NOAA-20",
    "N21": "NOAA-21",
}


def _get_satellite_name(satellite: str) -> str:
    """Derive satellite name from satellite property."""
    return SATELLITE_MAP.get(satellite, "unknown")


def fetch_hotspots(
    api_key: str,
    base_url: str,
    province_idn: int,
    limit: int = 1000,
) -> list[dict]:
    """
    Fetch VIIRS hotspot data from the GISTDA API for a given province.

    Args:
        api_key: GISTDA API key.
        base_url: GISTDA API base URL.
        province_idn: Province identifier (e.g. 51 for ลำพูน).
        limit: Maximum number of records to fetch.

    Returns:
        List of hotspot dicts with extracted fields.
    """
    params = {
        "limit": limit,
        "offset": 0,
        "ct_tn": CT_TN,
        "pv_idn": province_idn,
    }
    headers = {
        "accept": "application/json",
        "API-Key": api_key,
    }

    try:
        logger.info(
            "Fetching hotspots for province %s (limit=%d)...", province_idn, limit
        )
        response = requests.get(base_url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error("Failed to fetch hotspots: %s", e)
        raise

    features = data.get("features", [])
    number_matched = data.get("numberMatched", 0)
    logger.info(
        "Fetched %d hotspots (total matched: %d)", len(features), number_matched
    )

    hotspots = []
    for feature in features:
        props = feature.get("properties", {})
        hotspot = {
            "id": props.get("hotspotid", ""),
            "province_th": props.get("pv_tn", ""),
            "province_en": props.get("pv_en", ""),
            "district_th": props.get("ap_tn", ""),
            "district_en": props.get("ap_en", ""),
            "sub_district_th": props.get("tb_tn", ""),
            "sub_district_en": props.get("tb_en", ""),
            "village": props.get("village", ""),
            "land_use": props.get("lu_name", ""),
            "latitude": props.get("latitude", 0),
            "longitude": props.get("longitude", 0),
            "brightness_ti4": props.get("bright_ti4", 0),
            "brightness_ti5": props.get("bright_ti5", 0),
            "confidence": props.get("confidence", ""),
            "frp": props.get("frp", 0),
            "acq_date": props.get("acq_date", ""),
            "acq_time": props.get("acq_time", ""),
            "th_time": props.get("th_time", ""),
            "th_date": props.get("th_date", ""),
            "satellite": props.get("satellite", ""),
            "instrument": props.get("instrument", ""),
            "satellite_name": _get_satellite_name(props.get("satellite", "")),
            "google_maps_link": props.get("linkgmap", ""),
        }
        hotspots.append(hotspot)

    return hotspots
