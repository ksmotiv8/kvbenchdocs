"""Controlled noise injection for generated documents.

Applies realistic text perturbations that simulate the variability found in
real-world clinical (and other domain) documents. Noise is applied per-line
at a configurable rate (~10-15% of lines by default).

Perturbation types:
  - Abbreviation variation: expand or contract common terms
  - Case variation: occasional all-caps or lowercase for headers/terms
  - Punctuation variation: colon, space, equals, dash between label and value
  - Section heading variation: swap between full and abbreviated headings
  - Whitespace variation: extra blank lines, leading spaces, tab/space mixing
"""

import random
import re
from typing import Optional


# --- Abbreviation mappings (bidirectional) ---

ABBREVIATIONS = {
    "Blood Pressure": "BP",
    "Heart Rate": "HR",
    "Respiratory Rate": "RR",
    "Temperature": "Temp",
    "Oxygen Saturation": "SpO2",
    "White Blood Cell": "WBC",
    "Red Blood Cell": "RBC",
    "Hemoglobin": "Hgb",
    "Hematocrit": "Hct",
    "Platelets": "Plt",
    "Blood Urea Nitrogen": "BUN",
    "Creatinine": "Cr",
    "Sodium": "Na",
    "Potassium": "K",
    "Chloride": "Cl",
    "Bicarbonate": "HCO3",
    "Glucose": "Glu",
    "Calcium": "Ca",
    "Magnesium": "Mg",
    "Phosphorus": "Phos",
    "International Normalized Ratio": "INR",
    "Partial Thromboplastin Time": "PTT",
    "Prothrombin Time": "PT",
    "Chest X-Ray": "CXR",
    "Computed Tomography": "CT",
    "Magnetic Resonance Imaging": "MRI",
    "Electrocardiogram": "EKG",
    "Emergency Department": "ED",
    "Intensive Care Unit": "ICU",
    "Operating Room": "OR",
    "Chief Complaint": "CC",
    "History of Present Illness": "HPI",
    "Review of Systems": "ROS",
    "Physical Examination": "PE",
    "Assessment and Plan": "A/P",
    "Past Medical History": "PMH",
    "Past Surgical History": "PSH",
    "Family History": "FH",
    "Social History": "SH",
    "Discharge": "D/C",
    "diagnosis": "dx",
    "treatment": "tx",
    "prescription": "Rx",
    "symptoms": "sx",
    "examination": "exam",
    "patient": "pt",
    "history": "hx",
    "medication": "med",
    "medications": "meds",
}

# Build reverse map for expanding abbreviations back to full form
_REVERSE_ABBREV = {v: k for k, v in ABBREVIATIONS.items()}

# Section heading variants
HEADING_VARIANTS = {
    "Chief Complaint": ["CC", "Chief Complaint", "CHIEF COMPLAINT", "Reason for Visit"],
    "History of Present Illness": ["HPI", "History of Present Illness", "HISTORY OF PRESENT ILLNESS"],
    "Review of Systems": ["ROS", "Review of Systems", "REVIEW OF SYSTEMS"],
    "Physical Examination": ["PE", "Physical Examination", "PHYSICAL EXAMINATION", "Physical Exam"],
    "Assessment and Plan": ["A/P", "Assessment and Plan", "ASSESSMENT AND PLAN", "Assessment & Plan"],
    "Past Medical History": ["PMH", "Past Medical History", "PAST MEDICAL HISTORY"],
    "Past Surgical History": ["PSH", "Past Surgical History", "PAST SURGICAL HISTORY"],
    "Family History": ["FH", "Family History", "FAMILY HISTORY"],
    "Social History": ["SH", "Social History", "SOCIAL HISTORY"],
    "Vital Signs": ["Vitals", "Vital Signs", "VITAL SIGNS", "VS"],
    "Medications": ["Meds", "Medications", "MEDICATIONS", "Current Medications"],
    "Allergies": ["Allergies", "ALLERGIES", "Allergy List"],
    "Laboratory Results": ["Labs", "Laboratory Results", "LABORATORY RESULTS", "Lab Results"],
    "Imaging": ["Imaging", "IMAGING", "Radiology", "Imaging Studies"],
    "Discharge Instructions": ["D/C Instructions", "Discharge Instructions", "DISCHARGE INSTRUCTIONS"],
}

# Punctuation separators between labels and values (e.g., "BP: 120/80")
_SEPARATORS = [": ", " ", "= ", " - ", "  "]


_rng = random.Random()  # module-level instance, reseeded per call


def inject_noise(text: str, rate: float = 0.12, seed: Optional[int] = None) -> str:
    """Apply controlled noise to document text.

    Args:
        text: The document text to perturb.
        rate: Fraction of lines to perturb (0.0 to 1.0). Default ~12%.
        seed: Optional random seed for reproducibility.

    Returns:
        Perturbed text with realistic variations.
    """
    if seed is not None:
        _rng.seed(seed)

    lines = text.split("\n")
    result = []

    for line in lines:
        if _rng.random() < rate and line.strip():
            # Pick a random perturbation type
            perturb = _rng.choice([
                _perturb_abbreviation,
                _perturb_case,
                _perturb_punctuation,
                _perturb_heading,
                _perturb_whitespace,
            ])
            line = perturb(line)
        result.append(line)

    # Occasional extra blank line insertion (~3% chance between lines)
    if rate > 0:
        final = []
        for line in result:
            final.append(line)
            if _rng.random() < 0.03 and line.strip():
                final.append("")
        return "\n".join(final)

    return "\n".join(result)


# Minimum abbreviation length for expansion (avoids false-matching "K", "Ca", etc.)
_MIN_ABBREV_LEN = 3


def _perturb_abbreviation(line: str) -> str:
    """Randomly expand or contract one abbreviation in the line."""
    # Try contracting a full term to abbreviation
    for full, abbrev in ABBREVIATIONS.items():
        if full in line and _rng.random() < 0.5:
            return line.replace(full, abbrev, 1)
    # Try expanding an abbreviation to full term (skip short ones)
    for abbrev, full in _REVERSE_ABBREV.items():
        if len(abbrev) < _MIN_ABBREV_LEN:
            continue
        pattern = r"\b" + re.escape(abbrev) + r"\b"
        if re.search(pattern, line) and _rng.random() < 0.3:
            return re.sub(pattern, full, line, count=1)
    return line


def _perturb_case(line: str) -> str:
    """Occasionally change case of a term or the whole line."""
    stripped = line.strip()
    # If it looks like a heading (short, ends with colon or is all caps)
    if len(stripped) < 60 and (stripped.endswith(":") or stripped.isupper()):
        choice = _rng.choice(["upper", "title", "original"])
        if choice == "upper":
            return line.upper()
        elif choice == "title":
            return line.title()
    return line


def _perturb_punctuation(line: str) -> str:
    """Vary the separator between a label and its value."""
    # Match patterns like "BP: 120/80" or "HR: 88"
    match = re.match(r"^(\s*)([\w\s/]+?):\s+(.+)$", line)
    if match:
        indent, label, value = match.groups()
        sep = _rng.choice(_SEPARATORS)
        return f"{indent}{label}{sep}{value}"
    return line


def _perturb_heading(line: str) -> str:
    """Swap a section heading with an alternate form."""
    stripped = line.strip()
    # Check if line is a markdown heading or standalone heading
    md_prefix = ""
    heading_text = stripped
    if stripped.startswith("#"):
        parts = stripped.split(" ", 1)
        if len(parts) == 2:
            md_prefix = parts[0] + " "
            heading_text = parts[1]

    # Remove trailing colon for matching
    has_colon = heading_text.endswith(":")
    match_text = heading_text.rstrip(":")

    for canonical, variants in HEADING_VARIANTS.items():
        if match_text in variants or match_text == canonical:
            new_heading = _rng.choice(variants)
            if has_colon:
                new_heading += ":"
            indent = line[: len(line) - len(line.lstrip())]
            return f"{indent}{md_prefix}{new_heading}"
    return line


def _perturb_whitespace(line: str) -> str:
    """Add minor whitespace variations."""
    choice = _rng.choice(["leading", "trailing", "double_space"])
    if choice == "leading":
        # Add 1-3 extra leading spaces
        return " " * _rng.randint(1, 3) + line
    elif choice == "trailing":
        return line + " " * _rng.randint(1, 4)
    else:
        # Double a random space in the line
        spaces = [m.start() for m in re.finditer(r" ", line)]
        if spaces:
            pos = _rng.choice(spaces)
            return line[:pos] + "  " + line[pos + 1 :]
    return line


# =========================================================================
# Legal-specific noise
# =========================================================================

# Defined terms that get capitalized in legal documents
_LEGAL_DEFINED_TERMS = [
    ("agreement", "Agreement"),
    ("company", "Company"),
    ("employer", "Employer"),
    ("employee", "Employee"),
    ("licensee", "Licensee"),
    ("licensor", "Licensor"),
    ("party", "Party"),
    ("parties", "Parties"),
    ("contractor", "Contractor"),
    ("client", "Client"),
    ("seller", "Seller"),
    ("buyer", "Buyer"),
    ("landlord", "Landlord"),
    ("tenant", "Tenant"),
    ("plaintiff", "Plaintiff"),
    ("defendant", "Defendant"),
    ("court", "Court"),
    ("effective date", "Effective Date"),
    ("confidential information", "Confidential Information"),
    ("intellectual property", "Intellectual Property"),
    ("term", "Term"),
    ("territory", "Territory"),
]

# Section heading variants for legal documents
_LEGAL_HEADING_VARIANTS = {
    "Section": ["Section", "Sec.", "SECTION", "ARTICLE", "Clause", "Art."],
    "Article": ["Article", "ARTICLE", "Art.", "Section"],
    "Clause": ["Clause", "Section", "Sec.", "Provision"],
    "Exhibit": ["Exhibit", "EXHIBIT", "Schedule", "Appendix", "Annex"],
    "Recitals": ["Recitals", "RECITALS", "WHEREAS", "Background"],
    "Definitions": ["Definitions", "DEFINITIONS", "Defined Terms"],
    "Representations": ["Representations and Warranties", "REPRESENTATIONS AND WARRANTIES", "Representations"],
    "Indemnification": ["Indemnification", "INDEMNIFICATION", "Indemnity"],
    "Termination": ["Termination", "TERMINATION", "Term and Termination"],
    "Miscellaneous": ["Miscellaneous", "MISCELLANEOUS", "General Provisions", "GENERAL PROVISIONS"],
    "Governing Law": ["Governing Law", "GOVERNING LAW", "Choice of Law", "Applicable Law"],
    "Notices": ["Notices", "NOTICES", "Notice Provisions"],
}


def inject_legal_noise(text: str, rate: float = 0.12, seed: Optional[int] = None) -> str:
    """Apply legal-domain-specific noise to document text.

    Perturbation types:
      - Section symbol insertion (Section 3.1 -> S.3.1)
      - Section heading variation (Section -> ARTICLE, Clause, Sec.)
      - Capitalized defined terms (agreement -> Agreement)
      - Citation variation (Section 5.2 -> S.5.2, Sec. 5.2)
      - Whitespace and punctuation variation
      - Numbering style variation (1.1 -> (a))
    """
    if seed is not None:
        _rng.seed(seed)

    lines = text.split("\n")
    result = []

    for line in lines:
        if _rng.random() < rate and line.strip():
            perturb = _rng.choice([
                _legal_perturb_section_symbol,
                _legal_perturb_heading,
                _legal_perturb_defined_term,
                _legal_perturb_citation,
                _legal_perturb_punctuation,
                _legal_perturb_numbering,
                _perturb_whitespace,  # reuse generic whitespace noise
            ])
            line = perturb(line)
        result.append(line)

    # Occasional extra blank line (~3%)
    if rate > 0:
        final = []
        for line in result:
            final.append(line)
            if _rng.random() < 0.03 and line.strip():
                final.append("")
        return "\n".join(final)

    return "\n".join(result)


def _legal_perturb_section_symbol(line: str) -> str:
    """Replace 'Section X' with the section symbol."""
    # Section 3.1 -> S.3.1
    match = re.search(r"\bSection\s+(\d[\d.]*(?:\([a-z]\))?)", line)
    if match:
        ref = match.group(1)
        replacement = _rng.choice([f"\u00a7{ref}", f"\u00a7 {ref}", f"Sec. {ref}"])
        return line[:match.start()] + replacement + line[match.end():]
    return line


def _legal_perturb_heading(line: str) -> str:
    """Swap a legal section heading with an alternate form."""
    stripped = line.strip()

    # Match numbered headings like "Section 2" or "Article IV"
    match = re.match(r"^(\s*)(Section|Article|Clause|SECTION|ARTICLE|CLAUSE)\b(.*)$", line)
    if match:
        indent, keyword, rest = match.groups()
        canonical = keyword.title() if keyword.isupper() else keyword
        if canonical in _LEGAL_HEADING_VARIANTS:
            new_kw = _rng.choice(_LEGAL_HEADING_VARIANTS[canonical])
            return f"{indent}{new_kw}{rest}"
        return line

    # Match standalone headings
    for canonical, variants in _LEGAL_HEADING_VARIANTS.items():
        clean = stripped.rstrip(":.").strip()
        if clean in variants or clean == canonical:
            new_heading = _rng.choice(variants)
            # Preserve trailing punctuation
            if stripped.endswith(":"):
                new_heading += ":"
            elif stripped.endswith("."):
                new_heading += "."
            indent = line[:len(line) - len(line.lstrip())]
            return f"{indent}{new_heading}"

    return line


def _legal_perturb_defined_term(line: str) -> str:
    """Capitalize or de-capitalize a defined term."""
    for lower, upper in _LEGAL_DEFINED_TERMS:
        # Capitalize: "the agreement" -> "the Agreement"
        if lower in line and _rng.random() < 0.4:
            return line.replace(lower, upper, 1)
        # De-capitalize: "the Agreement" -> "the agreement"
        if upper in line and _rng.random() < 0.2:
            return line.replace(upper, lower, 1)
    return line


def _legal_perturb_citation(line: str) -> str:
    """Vary section citation format."""
    # Match "Section 5.2" style references
    match = re.search(r"\bSection\s+(\d[\d.]*)", line)
    if match:
        num = match.group(1)
        variants = [
            f"Section {num}",
            f"Sec. {num}",
            f"\u00a7{num}",
            f"\u00a7 {num}",
            f"Section {num}(a)",
        ]
        replacement = _rng.choice(variants)
        return line[:match.start()] + replacement + line[match.end():]
    return line


def _legal_perturb_punctuation(line: str) -> str:
    """Vary punctuation around section references and labels."""
    # "Section 3:" -> "Section 3" or "Section 3."
    match = re.match(r"^(\s*)((?:Section|Article|Clause)\s+[\d.]+)([:.])(\s*.*)", line)
    if match:
        indent, heading, punct, rest = match.groups()
        new_punct = _rng.choice([":", ".", "", " -"])
        return f"{indent}{heading}{new_punct}{rest}"
    return line


def _legal_perturb_numbering(line: str) -> str:
    """Vary numbering style for list items."""
    stripped = line.lstrip()
    indent = line[:len(line) - len(stripped)]

    # Match "1.1 " or "1.2 " at start of line
    match = re.match(r"^(\d+)\.(\d+)\s+(.*)$", stripped)
    if match:
        major, minor, rest = match.groups()
        minor_int = int(minor)
        # Convert to letter-based: 1 -> (a), 2 -> (b), ...
        if minor_int <= 26:
            letter = chr(ord('a') + minor_int - 1)
            style = _rng.choice([
                f"({letter}) {rest}",
                f"{major}.{minor} {rest}",  # keep original
                f"({minor_int}) {rest}",
            ])
            return f"{indent}{style}"
    return line


# =========================================================================
# Domain noise dispatcher
# =========================================================================

DOMAIN_NOISE = {
    "medical": inject_noise,
    "legal": inject_legal_noise,
}


def get_noise_function(domain: str):
    """Return the noise function for a domain, falling back to generic."""
    return DOMAIN_NOISE.get(domain, inject_noise)
