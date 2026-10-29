import re

from backend.app.services.discovery.geo import haversine_distance_km


def is_valid_venue_name(name: str | None) -> bool:
    """
    Filters out nameless, un-named, pure address/digits, raw ID fallbacks,
    or generic placeholder OSM results so only properly-named real celebration places reach the UI.
    """
    if not name or not isinstance(name, str):
        return False
    clean = name.strip()
    if len(clean) < 3:
        return False
    if not any(c.isalpha() for c in clean):
        return False
    lower = clean.lower()
    # Filter out raw OSM identifiers and fallbacks
    if lower.startswith(
        ("node/", "way/", "relation/", "osm node", "osm way", "osm relation", "osm/")
    ):
        return False
    # Filter out pure numbers or address numbers like '14/2', '101'
    if re.match(r"^[\d\s\/\-\.,#]+$", clean):
        return False
    # Filter out generic single-word placeholders with no distinct identity
    return lower not in {
        "unnamed",
        "unknown",
        "venue",
        "banquet",
        "hall",
        "marriage garden",
        "hotel",
        "resort",
        "palace",
    }


def extract_distinctive_tokens(name: str) -> set:
    """Extracts distinctive name tokens, removing common venue descriptor stop words."""
    stop_words = {
        "the",
        "hotel",
        "resort",
        "and",
        "&",
        "palace",
        "hall",
        "banquet",
        "garden",
        "gardens",
        "marriage",
        "jaipur",
        "pune",
        "bengaluru",
        "bangalore",
        "indore",
        "mangal",
        "karyalay",
        "karyalaya",
        "kalyana",
        "mandap",
        "mandapa",
        "mantap",
        "suites",
        "party",
        "plot",
    }
    tokens = set(re.findall(r"[a-z0-9]+", name.lower()))
    distinctive = tokens - stop_words
    return distinctive if distinctive else tokens


# Corporate hotel chains and qualifiers allowable as additions to the same physical venue
ALLOWABLE_CHAIN_QUALIFIERS = {
    "taj",
    "oberoi",
    "itc",
    "leela",
    "hyatt",
    "marriott",
    "radisson",
    "hilton",
    "novotel",
    "westin",
    "sheraton",
    "sofitel",
    "lalit",
    "clarks",
    "road",
    "main",
    "near",
    "opp",
    "opposite",
}

# Generic modifiers / honorifics that are ubiquitous across Indian businesses
# A shared token among these alone NEVER qualifies as a duplicate
GENERIC_NAME_MODIFIERS = {
    "grand",
    "royal",
    "new",
    "classic",
    "star",
    "city",
    "prime",
    "elite",
    "golden",
    "silver",
    "crown",
    "shree",
    "shri",
    "sri",
    "om",
    "sai",
    "jai",
    "best",
    "top",
    "central",
}


def _is_name_or_city_suffix_match(norm1: str, norm2: str) -> bool:
    if norm1 == norm2:
        return True
    if (norm1.startswith(norm2) or norm2.startswith(norm1)) and abs(len(norm1) - len(norm2)) <= 10:
        remainder = (
            norm1.replace(norm2, "") if len(norm1) > len(norm2) else norm2.replace(norm1, "")
        )
        if remainder in {"jaipur", "pune", "bengaluru", "indore", "delhi", "mumbai"}:
            return True
    return False


def _are_tokens_duplicate(toks1: set[str], toks2: set[str]) -> bool:
    if not toks1 or not toks2:
        return False
    if toks1 == toks2:
        return not toks1.issubset(GENERIC_NAME_MODIFIERS)

    shared = toks1 & toks2
    diff = toks1 ^ toks2
    if not shared or shared.issubset(GENERIC_NAME_MODIFIERS):
        return False

    has_substantial_proper_noun = any(
        len(t) >= 4 and t not in GENERIC_NAME_MODIFIERS for t in shared
    )
    if not has_substantial_proper_noun:
        return False
    return bool(diff.issubset(ALLOWABLE_CHAIN_QUALIFIERS))


def are_venues_duplicates(
    name1: str, lat1: float, lng1: float, name2: str, lat2: float, lng2: float
) -> bool:
    """
    Determines whether two venue profiles represent the exact same physical venue.
    Guards strictly against over-merging distinct businesses while ensuring true duplicates
    (e.g., 'Rambagh Palace' vs 'The Rambagh Palace, Jaipur') are cleanly collapsed.
    """
    norm1 = re.sub(r"[^a-z0-9]", "", name1.lower())
    norm2 = re.sub(r"[^a-z0-9]", "", name2.lower())
    if norm1 == norm2:
        return True

    if haversine_distance_km(lat1, lng1, lat2, lng2) > 0.35:
        return False

    if _is_name_or_city_suffix_match(norm1, norm2):
        return True

    toks1 = extract_distinctive_tokens(name1)
    toks2 = extract_distinctive_tokens(name2)
    return _are_tokens_duplicate(toks1, toks2)
