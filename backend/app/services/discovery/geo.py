import ipaddress
import math
import socket
from urllib.parse import urlparse

CITY_CENTERS = {
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "jaipur": (26.9124, 75.7873),
    "udaipur": (24.5854, 73.7125),
    "pune": (18.5204, 73.8567),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "chandigarh": (30.7333, 76.7794),
    "goa": (15.2993, 74.1240),
}


def _validate_safe_outbound_url(url: str) -> None:
    """SSRF guard: Validates URL uses HTTPS/HTTP and resolves to public IPs."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsafe URL scheme '{parsed.scheme}'; only http/https allowed.")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Missing hostname in outbound request URL.")
    if hostname in ("localhost", "127.0.0.1", "::1"):
        raise ValueError(f"SSRF blocked: Hostname '{hostname}' is loopback/private.")
    addr_info = socket.getaddrinfo(hostname, None)
    for res in addr_info:
        ip = res[4][0]
        ip_obj = ipaddress.ip_address(ip)
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
        ):
            raise ValueError(
                f"SSRF blocked: Hostname '{hostname}' resolved to prohibited IP '{ip}'."
            )


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance in kilometers using Haversine formula."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c
