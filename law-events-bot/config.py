"""User-editable settings for the law events bot."""

APPLICATION_CYCLE = 2027  # Admissions cycle you are applying in
HOME_REGION = "Hayward, CA (East Bay, San Francisco Bay Area)"
INCLUDE_VIRTUAL = True
LOOKAHEAD_DAYS = 120  # How far ahead to search for events

# Locations (lowercase substrings) treated as local (within reach of Hayward)
LOCAL_KEYWORDS = [
    "bay area", "san francisco", "oakland", "berkeley", "palo alto", "stanford",
    "san jose", "santa clara", "mountain view", "menlo park", "redwood city",
    "san mateo", "fremont", "hayward", "walnut creek", "sunnyvale", "cupertino",
    "emeryville", "daly city", "south san francisco", "marin", "san rafael",
    "east bay", "peninsula", "san leandro", "castro valley", "union city", "newark, ca",
    "pleasanton", "livermore", "dublin, ca", "concord, ca", "richmond, ca", "milpitas", "davis",
]

TARGET_SCHOOLS = [
    "Stanford Law", "Berkeley Law", "UC Law San Francisco", "Santa Clara Law",
    "USC Gould", "UCLA Law", "UC Davis Law", "UC Irvine Law",
    "Harvard Law", "Yale Law", "NYU Law", "Columbia Law", "University of Chicago Law",
    "Penn Carey Law", "Michigan Law", "Duke Law", "Northwestern Pritzker Law",
    "Georgetown Law", "Virginia Law", "Cornell Law",
]

EVENT_TYPES = [
    "LSAC Law School Forums (in-person and virtual)",
    "law school fairs, including university pre-law fairs and Bay Area fairs",
    "law school admissions open houses, info sessions, and webinars",
    "diversity and pipeline programs and pre-law conferences (AccessLex, PLUS programs, CLEO, etc.)",
    "LSAT and admissions webinars featuring admissions deans",
    "networking events with law students or attorneys for prospective applicants",
]

MODEL = "claude-opus-5-5"
MAX_SEARCHES = 25
MAX_FETCHES = 15
