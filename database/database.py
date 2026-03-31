"""
Firebase Firestore database layer.
Replaces SQLAlchemy with Firestore collections.
"""
import os
from datetime import datetime
from auth.auth import db_firestore


def get_db():
    """FastAPI dependency -- returns Firestore client."""
    return db_firestore


def init_firestore():
    """Seed default data into Firestore if collections are empty."""
    db = db_firestore

    # Check if officers exist
    officers_ref = db.collection("officers")
    if not list(officers_ref.limit(1).stream()):
        _seed_officers(db)

    # Check if persons exist
    persons_ref = db.collection("persons")
    if not list(persons_ref.limit(1).stream()):
        _seed_criminal_data(db)

    print("[DB] Firestore initialized with seed data")


def _seed_officers(db):
    """Create officer profiles matching Firebase Auth accounts."""
    officers = [
        {
            "username": "inspector.sharma",
            "email": "inspector.sharma@crs.gov.in",
            "full_name": "Inspector R.K. Sharma",
            "role": "admin",
            "badge_number": "IPS-2019-001",
            "department": "Criminal Investigation Department",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        },
        {
            "username": "si.verma",
            "email": "si.verma@crs.gov.in",
            "full_name": "S.I. Priya Verma",
            "role": "officer",
            "badge_number": "SI-2021-042",
            "department": "Anti-Terrorism Squad",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        },
        {
            "username": "constable.kumar",
            "email": "constable.kumar@crs.gov.in",
            "full_name": "Constable Amit Kumar",
            "role": "officer",
            "badge_number": "HC-2022-187",
            "department": "Crime Branch",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        },
    ]
    for off in officers:
        db.collection("officers").add(off)
    print(f"[DB] Seeded {len(officers)} officers")


def _seed_criminal_data(db):
    """Insert real Indian criminals/terrorists with detailed records."""
    now = datetime.utcnow().isoformat()
    criminals = [
        {
            "full_name": "Dawood Ibrahim",
            "date_of_birth": "1955-12-26",
            "gender": "Male",
            "nationality": "Indian",
            "address": "White House, Clifton, Karachi, Pakistan (suspected)",
            "government_id_number": "INTERPOL Red Notice 1996",
            "record_status": "Most Wanted",
            "risk_level": "High",
            "last_seen_location": "Karachi, Pakistan",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Mastermind of the 1993 Mumbai serial bombings that killed 257 people and injured 700+",
                    "case_number": "RC-1/S/93-TADA",
                    "date_of_offense": "1993-03-12",
                    "arrest_date": None,
                    "conviction_status": "Absconding",
                    "sentence_details": "Death sentence (in absentia) by TADA Court",
                    "law_enforcement_agency": "CBI / NIA",
                    "court_name": "TADA Court, Mumbai",
                },
                {
                    "crime_type": "Organized Crime",
                    "crime_description": "Head of D-Company international crime syndicate involved in extortion, drug trafficking and arms smuggling",
                    "case_number": "MCOCA-D-2002-001",
                    "date_of_offense": "1986-01-01",
                    "arrest_date": None,
                    "conviction_status": "Wanted",
                    "sentence_details": "Multiple warrants pending",
                    "law_enforcement_agency": "Mumbai Police / INTERPOL",
                    "court_name": "Mumbai Sessions Court",
                },
            ],
        },
        {
            "full_name": "Masood Azhar",
            "date_of_birth": "1968-07-10",
            "gender": "Male",
            "nationality": "Pakistani",
            "address": "Bahawalpur, Punjab, Pakistan",
            "government_id_number": "UN Designated Terrorist (2019)",
            "record_status": "Most Wanted",
            "risk_level": "High",
            "last_seen_location": "Bahawalpur, Pakistan",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Founder of Jaish-e-Mohammed (JeM). Mastermind of Pulwama attack (2019) killing 40 CRPF personnel",
                    "case_number": "NIA-RC-01/2019/NIA/DLI",
                    "date_of_offense": "2019-02-14",
                    "arrest_date": None,
                    "conviction_status": "Wanted",
                    "sentence_details": "NIA charge sheet filed",
                    "law_enforcement_agency": "NIA",
                    "court_name": "NIA Special Court, New Delhi",
                },
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Attack on Indian Parliament (2001) by JeM operatives",
                    "case_number": "FIR-394/2001-SP",
                    "date_of_offense": "2001-12-13",
                    "arrest_date": None,
                    "conviction_status": "Wanted",
                    "sentence_details": "Pending",
                    "law_enforcement_agency": "Delhi Police Special Cell / NIA",
                    "court_name": "Patiala House Court, Delhi",
                },
            ],
        },
        {
            "full_name": "Hafiz Muhammad Saeed",
            "date_of_birth": "1950-06-05",
            "gender": "Male",
            "nationality": "Pakistani",
            "address": "Lahore, Pakistan (under house arrest)",
            "government_id_number": "UN Designated Terrorist (2008)",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Lahore, Pakistan",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Founder of Lashkar-e-Taiba (LeT). Mastermind of 26/11 Mumbai attacks (2008) killing 166 people",
                    "case_number": "NIA-RC-06/2008/NIA/MUM",
                    "date_of_offense": "2008-11-26",
                    "arrest_date": "2019-07-17",
                    "conviction_status": "Convicted",
                    "sentence_details": "Sentenced to 36 years by Pakistan Anti-Terrorism Court (terror financing)",
                    "law_enforcement_agency": "NIA / INTERPOL",
                    "court_name": "Anti-Terrorism Court, Lahore",
                },
            ],
        },
        {
            "full_name": "Tiger Memon",
            "date_of_birth": "1960-02-05",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Unknown (suspected Karachi, Pakistan)",
            "government_id_number": "INTERPOL Red Notice",
            "record_status": "Most Wanted",
            "risk_level": "High",
            "last_seen_location": "Karachi, Pakistan",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Key conspirator of 1993 Mumbai serial bombings. Organized RDX supply and logistics",
                    "case_number": "TADA-1/93-Mumbai",
                    "date_of_offense": "1993-03-12",
                    "arrest_date": None,
                    "conviction_status": "Absconding",
                    "sentence_details": "Death sentence (in absentia)",
                    "law_enforcement_agency": "CBI / Mumbai Police",
                    "court_name": "TADA Court, Mumbai",
                },
            ],
        },
        {
            "full_name": "Chhota Rajan",
            "date_of_birth": "1960-03-20",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Tihar Jail, New Delhi (incarcerated)",
            "government_id_number": "MCOCA-CR-2001",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Tihar Jail, New Delhi",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Murder",
                    "crime_description": "Ordered the murder of journalist J. Dey (2011) and multiple gang-related killings",
                    "case_number": "CR-81/2011-CIU",
                    "date_of_offense": "2011-06-11",
                    "arrest_date": "2015-10-25",
                    "conviction_status": "Convicted",
                    "sentence_details": "Life imprisonment by Mumbai Sessions Court",
                    "law_enforcement_agency": "Mumbai Police Crime Branch",
                    "court_name": "Mumbai Sessions Court",
                },
                {
                    "crime_type": "Organized Crime",
                    "crime_description": "Ran international crime syndicate involved in extortion, contract killings and smuggling",
                    "case_number": "MCOCA-15/2001",
                    "date_of_offense": "1995-01-01",
                    "arrest_date": "2015-10-25",
                    "conviction_status": "Convicted",
                    "sentence_details": "Multiple life sentences",
                    "law_enforcement_agency": "CBI / INTERPOL",
                    "court_name": "MCOCA Court, Mumbai",
                },
            ],
        },
        {
            "full_name": "Abu Salem",
            "date_of_birth": "1969-12-15",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Taloja Central Jail, Navi Mumbai (incarcerated)",
            "government_id_number": "TADA-ABU-2005",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Taloja Jail, Navi Mumbai",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Convicted in 1993 Mumbai bombings case for arms supply and conspiracy",
                    "case_number": "RC-1/S/93-TADA-ABU",
                    "date_of_offense": "1993-03-12",
                    "arrest_date": "2002-09-18",
                    "conviction_status": "Convicted",
                    "sentence_details": "Life imprisonment (extradited from Portugal in 2005)",
                    "law_enforcement_agency": "CBI",
                    "court_name": "TADA Court, Mumbai",
                },
                {
                    "crime_type": "Extortion",
                    "crime_description": "Extortion of Bollywood film producers and builders in Mumbai",
                    "case_number": "CR-204/2001-EOW",
                    "date_of_offense": "1998-06-01",
                    "arrest_date": "2002-09-18",
                    "conviction_status": "Convicted",
                    "sentence_details": "7 years imprisonment",
                    "law_enforcement_agency": "Mumbai Police",
                    "court_name": "Mumbai Sessions Court",
                },
            ],
        },
        {
            "full_name": "Ajmal Kasab",
            "date_of_birth": "1987-07-13",
            "gender": "Male",
            "nationality": "Pakistani",
            "address": "Deceased (executed 2012)",
            "government_id_number": "26/11-ACC-01",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Yerwada Jail, Pune (executed)",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Only surviving gunman of the 26/11 Mumbai attacks (2008). Attacked CST station and Cama Hospital killing 72 people",
                    "case_number": "SC-175/2009",
                    "date_of_offense": "2008-11-26",
                    "arrest_date": "2008-11-26",
                    "conviction_status": "Convicted",
                    "sentence_details": "Death sentence (executed 21 Nov 2012)",
                    "law_enforcement_agency": "Mumbai Police / NIA",
                    "court_name": "Supreme Court of India",
                },
            ],
        },
        {
            "full_name": "Veerappan",
            "date_of_birth": "1952-01-18",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Deceased (killed 2004)",
            "government_id_number": "STF-VEERA-1990",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Dharmapuri forests, Tamil Nadu (killed in encounter)",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Murder",
                    "crime_description": "Killed 184 people including police and forest officials over 3 decades in forests of Karnataka/Tamil Nadu",
                    "case_number": "STF-CR-001/1990",
                    "date_of_offense": "1987-01-01",
                    "arrest_date": None,
                    "conviction_status": "Killed in Encounter",
                    "sentence_details": "Eliminated in STF operation on 18 Oct 2004",
                    "law_enforcement_agency": "Tamil Nadu STF",
                    "court_name": "Mysore Sessions Court",
                },
                {
                    "crime_type": "Kidnapping",
                    "crime_description": "Kidnapped Kannada actor Rajkumar and held for 108 days demanding release of jailed associates",
                    "case_number": "CR-KID-2000-RK",
                    "date_of_offense": "2000-07-30",
                    "arrest_date": None,
                    "conviction_status": "Case closed (deceased)",
                    "sentence_details": "N/A",
                    "law_enforcement_agency": "Karnataka Police STF",
                    "court_name": "Mysore Sessions Court",
                },
            ],
        },
        {
            "full_name": "Charles Sobhraj",
            "date_of_birth": "1944-04-06",
            "gender": "Male",
            "nationality": "French-Vietnamese",
            "address": "Released — deported to France (2023)",
            "government_id_number": "INTERPOL-SOBHRAJ-1976",
            "record_status": "Released",
            "risk_level": "Medium",
            "last_seen_location": "Paris, France",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Serial Murder",
                    "crime_description": "The Serpent — serial killer who murdered at least 12 Western tourists across Southeast Asia in the 1970s",
                    "case_number": "NEPAL-HC-2004",
                    "date_of_offense": "1975-01-01",
                    "arrest_date": "2003-09-01",
                    "conviction_status": "Released",
                    "sentence_details": "Life imprisonment in Nepal (released 2023, deported to France)",
                    "law_enforcement_agency": "Nepal Police / INTERPOL",
                    "court_name": "Nepal Supreme Court",
                },
            ],
        },
        {
            "full_name": "Chota Shakeel",
            "date_of_birth": "1955-01-15",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Unknown (suspected Karachi, Pakistan)",
            "government_id_number": "INTERPOL-CS-2003",
            "record_status": "Most Wanted",
            "risk_level": "High",
            "last_seen_location": "Karachi, Pakistan",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Organized Crime",
                    "crime_description": "Second-in-command of D-Company under Dawood Ibrahim. Involved in extortion, contract killings and real estate fraud",
                    "case_number": "MCOCA-CS-2003",
                    "date_of_offense": "1993-01-01",
                    "arrest_date": None,
                    "conviction_status": "Wanted",
                    "sentence_details": "Multiple warrants pending",
                    "law_enforcement_agency": "Mumbai Police / NIA",
                    "court_name": "Mumbai Sessions Court",
                },
            ],
        },
        {
            "full_name": "Iqbal Mirchi",
            "date_of_birth": "1950-02-10",
            "gender": "Male",
            "nationality": "Indian",
            "address": "Deceased (died 2013, London)",
            "government_id_number": "ED-PMLA-2019",
            "record_status": "Under Investigation",
            "risk_level": "High",
            "last_seen_location": "London, United Kingdom (deceased)",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Drug Trafficking",
                    "crime_description": "One of Indias biggest drug lords. Trafficked heroin internationally through D-Company network",
                    "case_number": "NCB-DT-2001",
                    "date_of_offense": "1986-01-01",
                    "arrest_date": None,
                    "conviction_status": "Deceased",
                    "sentence_details": "Cases continue against associates under PMLA",
                    "law_enforcement_agency": "NCB / Enforcement Directorate",
                    "court_name": "PMLA Court, Mumbai",
                },
                {
                    "crime_type": "Money Laundering",
                    "crime_description": "Laundered over Rs 30,000 crore through real estate in Mumbai and London",
                    "case_number": "ED-PMLA-RPC-5/2019",
                    "date_of_offense": "1998-01-01",
                    "arrest_date": None,
                    "conviction_status": "Under Investigation",
                    "sentence_details": "Properties seized by ED worth Rs 600 crore",
                    "law_enforcement_agency": "Enforcement Directorate",
                    "court_name": "PMLA Special Court, Mumbai",
                },
            ],
        },
        {
            "full_name": "Osama bin Laden",
            "date_of_birth": "1957-03-10",
            "gender": "Male",
            "nationality": "Saudi Arabian",
            "address": "Deceased (killed 2011, Abbottabad, Pakistan)",
            "government_id_number": "FBI Most Wanted 1999-2011",
            "record_status": "Convicted",
            "risk_level": "High",
            "last_seen_location": "Abbottabad, Pakistan (killed in US operation)",
            "image_path": None,
            "face_embedding_encrypted": None,
            "created_at": now,
            "updated_at": now,
            "crimes": [
                {
                    "crime_type": "Terrorism",
                    "crime_description": "Founder of al-Qaeda. Mastermind of 9/11 attacks (2001) killing nearly 3000 people. Also orchestrated 1998 US Embassy bombings",
                    "case_number": "FBI-TOP10-OBL-1999",
                    "date_of_offense": "2001-09-11",
                    "arrest_date": None,
                    "conviction_status": "Killed in Operation",
                    "sentence_details": "Killed by US Navy SEALs in Operation Neptune Spear on 2 May 2011",
                    "law_enforcement_agency": "FBI / CIA / US JSOC",
                    "court_name": "US Federal Court (indicted)",
                },
            ],
        },
    ]

    for criminal in criminals:
        crimes = criminal.pop("crimes", [])
        # Add person
        doc_ref = db.collection("persons").add(criminal)
        person_id = doc_ref[1].id

        # Add criminal records
        for crime in crimes:
            crime["person_id"] = person_id
            crime["last_updated"] = now
            db.collection("criminal_records").add(crime)

    print(f"[DB] Seeded {len(criminals)} criminals with detailed records")
