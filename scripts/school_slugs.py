"""
school_slugs.py — 247Sports URL slug utilities for CFB school names.
"""

SLUG_OVERRIDES = {
    "Mississippi": "ole-miss",
    "Nevada, Las Vegas": "unlv",
    "Louisiana State": "lsu",
    "Texas Christian": "tcu",
    "Southern California": "usc",
    "Connecticut": "uconn",
    "Massachusetts": "umass",
    "Florida International": "fiu",
    "Texas-San Antonio": "utsa",
    "Texas-El Paso": "utep",
    "North Carolina State": "nc-state",
    "Southern Mississippi": "southern-miss",
    "UAB": "uab",
    "Hawaii": "hawaii",
    "Miami (OH)": "miami-oh",
    "Louisiana": "louisiana",
    "Sam Houston": "sam-houston",
    "Hawai'i": "hawaii",
    "Southern": "southern-u",
    "Texas A&M": "texas-am",
    "Prairie View A&M": "prairie-view",
    "Grambling": "grambling",
    "Jackson State": "jackson-state",
    "Florida A&M": "florida-am",
    "Alabama A&M": "alabama-am",
    "Bethune-Cookman": "bethune-cookman",
    "Howard": "howard",
    "Morgan State": "morgan-state",
    "North Carolina A&T": "north-carolina-at",
    "South Carolina State": "south-carolina-state",
    "Tennessee State": "tennessee-state",
    "Texas Southern": "texas-southern",
}


def make_slug(school_name: str) -> str:
    """Generate a 247Sports slug from a CFBD school name."""
    if school_name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[school_name]

    slug = school_name.lower()
    # Pad & with spaces so "A&M" becomes "A and M" → "a-and-m"
    slug = slug.replace("&", " and ")
    slug = slug.replace("'", "")
    slug = slug.replace(".", "")
    slug = slug.replace(" ", "-")
    # Collapse any double-hyphens produced by padding
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug
