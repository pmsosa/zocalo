"""Country codes used by the surveys: ISO 3166 numeric → (alpha-2, English name), plus name lookups."""
from __future__ import annotations

ISO = {
    4: ("AF", "Afghanistan"), 8: ("AL", "Albania"), 12: ("DZ", "Algeria"), 20: ("AD", "Andorra"), 24: ("AO", "Angola"),
    32: ("AR", "Argentina"), 51: ("AM", "Armenia"), 36: ("AU", "Australia"), 40: ("AT", "Austria"), 31: ("AZ", "Azerbaijan"),
    50: ("BD", "Bangladesh"), 112: ("BY", "Belarus"), 56: ("BE", "Belgium"), 204: ("BJ", "Benin"), 68: ("BO", "Bolivia"),
    70: ("BA", "Bosnia and Herzegovina"), 72: ("BW", "Botswana"), 76: ("BR", "Brazil"), 100: ("BG", "Bulgaria"),
    854: ("BF", "Burkina Faso"), 108: ("BI", "Burundi"), 132: ("CV", "Cabo Verde"), 116: ("KH", "Cambodia"),
    120: ("CM", "Cameroon"), 124: ("CA", "Canada"), 152: ("CL", "Chile"), 156: ("CN", "China"), 170: ("CO", "Colombia"),
    188: ("CR", "Costa Rica"), 384: ("CI", "Côte d'Ivoire"), 191: ("HR", "Croatia"), 196: ("CY", "Cyprus"),
    203: ("CZ", "Czechia"), 208: ("DK", "Denmark"), 214: ("DO", "Dominican Republic"), 218: ("EC", "Ecuador"),
    818: ("EG", "Egypt"), 222: ("SV", "El Salvador"), 233: ("EE", "Estonia"), 748: ("SZ", "Eswatini"), 231: ("ET", "Ethiopia"),
    246: ("FI", "Finland"), 250: ("FR", "France"), 266: ("GA", "Gabon"), 270: ("GM", "Gambia"), 268: ("GE", "Georgia"),
    276: ("DE", "Germany"), 288: ("GH", "Ghana"), 300: ("GR", "Greece"), 320: ("GT", "Guatemala"), 324: ("GN", "Guinea"),
    340: ("HN", "Honduras"), 344: ("HK", "Hong Kong"), 348: ("HU", "Hungary"), 352: ("IS", "Iceland"), 356: ("IN", "India"),
    360: ("ID", "Indonesia"), 364: ("IR", "Iran"), 368: ("IQ", "Iraq"), 372: ("IE", "Ireland"), 376: ("IL", "Israel"),
    380: ("IT", "Italy"), 388: ("JM", "Jamaica"), 392: ("JP", "Japan"), 400: ("JO", "Jordan"), 398: ("KZ", "Kazakhstan"),
    404: ("KE", "Kenya"), 410: ("KR", "South Korea"), 414: ("KW", "Kuwait"), 417: ("KG", "Kyrgyzstan"), 428: ("LV", "Latvia"),
    422: ("LB", "Lebanon"), 426: ("LS", "Lesotho"), 430: ("LR", "Liberia"), 434: ("LY", "Libya"), 440: ("LT", "Lithuania"),
    442: ("LU", "Luxembourg"), 446: ("MO", "Macao"), 450: ("MG", "Madagascar"), 454: ("MW", "Malawi"), 458: ("MY", "Malaysia"),
    462: ("MV", "Maldives"), 466: ("ML", "Mali"), 470: ("MT", "Malta"), 478: ("MR", "Mauritania"), 480: ("MU", "Mauritius"),
    484: ("MX", "Mexico"), 498: ("MD", "Moldova"), 496: ("MN", "Mongolia"), 499: ("ME", "Montenegro"), 504: ("MA", "Morocco"),
    508: ("MZ", "Mozambique"), 104: ("MM", "Myanmar"), 516: ("NA", "Namibia"), 524: ("NP", "Nepal"), 528: ("NL", "Netherlands"),
    554: ("NZ", "New Zealand"), 558: ("NI", "Nicaragua"), 562: ("NE", "Niger"), 566: ("NG", "Nigeria"), 807: ("MK", "North Macedonia"),
    578: ("NO", "Norway"), 586: ("PK", "Pakistan"), 275: ("PS", "Palestine"), 591: ("PA", "Panama"), 600: ("PY", "Paraguay"),
    604: ("PE", "Peru"), 608: ("PH", "Philippines"), 616: ("PL", "Poland"), 620: ("PT", "Portugal"), 630: ("PR", "Puerto Rico"),
    634: ("QA", "Qatar"), 642: ("RO", "Romania"), 643: ("RU", "Russia"), 646: ("RW", "Rwanda"), 682: ("SA", "Saudi Arabia"),
    686: ("SN", "Senegal"), 688: ("RS", "Serbia"), 694: ("SL", "Sierra Leone"), 702: ("SG", "Singapore"), 703: ("SK", "Slovakia"),
    705: ("SI", "Slovenia"), 710: ("ZA", "South Africa"), 724: ("ES", "Spain"), 144: ("LK", "Sri Lanka"), 729: ("SD", "Sudan"),
    752: ("SE", "Sweden"), 756: ("CH", "Switzerland"), 760: ("SY", "Syria"), 158: ("TW", "Taiwan"), 762: ("TJ", "Tajikistan"),
    834: ("TZ", "Tanzania"), 764: ("TH", "Thailand"), 768: ("TG", "Togo"), 780: ("TT", "Trinidad and Tobago"), 788: ("TN", "Tunisia"),
    792: ("TR", "Türkiye"), 800: ("UG", "Uganda"), 804: ("UA", "Ukraine"), 784: ("AE", "United Arab Emirates"),
    826: ("GB", "United Kingdom"), 840: ("US", "United States"), 858: ("UY", "Uruguay"), 860: ("UZ", "Uzbekistan"),
    862: ("VE", "Venezuela"), 704: ("VN", "Vietnam"), 887: ("YE", "Yemen"), 894: ("ZM", "Zambia"), 716: ("ZW", "Zimbabwe"),
    909: ("XK", "Kosovo"), 383: ("XK", "Kosovo"), 728: ("SS", "South Sudan"), 178: ("CG", "Congo"), 180: ("CD", "DR Congo"),
    226: ("GQ", "Equatorial Guinea"), 262: ("DJ", "Djibouti"), 232: ("ER", "Eritrea"), 706: ("SO", "Somalia"), 624: ("GW", "Guinea-Bissau"),
    678: ("ST", "São Tomé and Príncipe"), 690: ("SC", "Seychelles"), 174: ("KM", "Comoros"),
}
A2_NAME = {}
for _num, (_a2, _name) in ISO.items():
    A2_NAME.setdefault(_a2, _name)
NAME_A2 = {name.lower(): a2 for a2, name in A2_NAME.items()}
NAME_A2.update({"usa": "US", "u.s.": "US", "the united states": "US", "britain": "GB", "great britain": "GB", "uk": "GB",
                "korea": "KR", "south korea": "KR", "republic of korea": "KR", "cote d'ivoire": "CI", "ivory coast": "CI",
                "turkey": "TR", "czech republic": "CZ", "russian federation": "RU", "eswatini": "SZ", "swaziland": "SZ",
                "cape verde": "CV", "cabo verde": "CV", "palestinian territories": "PS", "palestine": "PS",
                "macedonia": "MK", "north macedonia": "MK", "the netherlands": "NL", "viet nam": "VN", "iran (islamic republic of)": "IR",
                "bolivia (plurinational state of)": "BO", "venezuela (bolivarian republic of)": "VE", "tanzania, united republic of": "TZ",
                "drc": "CD", "congo-brazzaville": "CG", "sao tome and principe": "ST", "são tomé and príncipe": "ST",
                "brasil": "BR", "méxico": "MX", "perú": "PE", "panamá": "PA", "república dominicana": "DO"})


def to_a2(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not (isinstance(value, float) and value != value):
        return ISO.get(int(value), (None,))[0]
    s = str(value).strip()
    if len(s) == 2 and s.upper() in A2_NAME:
        return s.upper()
    if s.isdigit():
        return ISO.get(int(s), (None,))[0]
    s2 = s.lower().split("(")[0].strip() if "(" in s and s.lower() not in NAME_A2 else s.lower()
    return NAME_A2.get(s.lower()) or NAME_A2.get(s2)


def name(a2: str) -> str:
    return A2_NAME.get(a2, a2)


US_STATES = {1: "Alabama", 2: "Alaska", 4: "Arizona", 5: "Arkansas", 6: "California", 8: "Colorado", 9: "Connecticut",
             10: "Delaware", 11: "District of Columbia", 12: "Florida", 13: "Georgia", 15: "Hawaii", 16: "Idaho", 17: "Illinois",
             18: "Indiana", 19: "Iowa", 20: "Kansas", 21: "Kentucky", 22: "Louisiana", 23: "Maine", 24: "Maryland",
             25: "Massachusetts", 26: "Michigan", 27: "Minnesota", 28: "Mississippi", 29: "Missouri", 30: "Montana",
             31: "Nebraska", 32: "Nevada", 33: "New Hampshire", 34: "New Jersey", 35: "New Mexico", 36: "New York",
             37: "North Carolina", 38: "North Dakota", 39: "Ohio", 40: "Oklahoma", 41: "Oregon", 42: "Pennsylvania",
             44: "Rhode Island", 45: "South Carolina", 46: "South Dakota", 47: "Tennessee", 48: "Texas", 49: "Utah",
             50: "Vermont", 51: "Virginia", 53: "Washington", 54: "West Virginia", 55: "Wisconsin", 56: "Wyoming",
             72: "Puerto Rico"}
