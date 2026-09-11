"""seed_db.py — PM-SURAJ Seva v2.0 · grounded sandbox seed
Run: python seed_db.py
Grounding: TAHDCO = TN SCA for NSFDC/NSTFDC/NSKFDC (tahdco.tn.gov.in).
District offices sit inside District Collectorates (District Manager, TAHDCO).
"""
import sqlite3, os

DB   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nowrongdoor.db")
SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")

# ---- PM-SURAJ journey stages (application -> sanction -> disbursement -> monitoring)
STAGES = [
    (1,  "SUBMITTED",              "Application submitted on PM-SURAJ"),
    (2,  "INITIAL_SCRUTINY",       "Initial scrutiny by SCA (TAHDCO) office"),
    (3,  "DOCUMENT_VERIFICATION",  "Document verification (caste/income/KYC cross-check)"),
    (4,  "ELIGIBILITY_VERIFICATION","Eligibility verification against scheme rules"),
    (5,  "FORWARDED_TO_CP",        "Forwarded to Channel Partner (bank / NBFC)"),
    (6,  "CREDIT_ASSESSMENT",      "Credit & project viability assessment"),
    (7,  "FIELD_VERIFICATION",     "Field verification of unit / residence"),
    (8,  "SANCTION",               "Loan sanction decision"),
    (9,  "AGREEMENT",              "Loan agreement & documentation"),
    (10, "DISBURSEMENT",           "Disbursement to beneficiary account"),
    (11, "REPAYMENT_MONITORING",   "Repayment & business monitoring"),
]

ALL_SCHEMES = "MICRO_FINANCE,NEW_SWARNIMA,MAHILA_SAMRIDHI,TERM_LOAN,EDUCATION_LOAN"
VER = "Sep 2026 (demo)"

# Grounded partner network: TAHDCO district units (Collectorate) + PSB/RRB/MFI partners
PARTNERS = [
    ("District Manager, TAHDCO", "SCA",  "NSFDC", "Madurai",       "Collectorate, Madurai 625001",              ALL_SCHEMES,                  "Collectorate Complex, Madurai 625001",              "0452-2531730"),
    ("Indian Bank — Main Branch","PSB",  "NSFDC", "Madurai",       "West Veli Street",                          "TERM_LOAN,EDUCATION_LOAN",   "127, West Veli Street, Madurai 625001",           "0452-2342286"),
    ("Canara Bank — Madurai",    "PSB",  "NSFDC", "Madurai",       "Town Hall Road",                            "TERM_LOAN,MICRO_FINANCE",    "13, Town Hall Road, Madurai 625003",              "0452-4370348"),
    ("Madurai DCC Bank",         "RRB",  "NSFDC", "Madurai",       "Anna Nagar",                                "MICRO_FINANCE,NEW_SWARNIMA", "P.T. Rajan Road, Anna Nagar, Madurai 625020",     "0452-2530460"),
    ("DHAN Foundation (MFI)",    "MFI",  "NSFDC", "Madurai",       "K.Pudur",                                   "MICRO_FINANCE,MAHILA_SAMRIDHI","18, K.Pudur, Madurai 625007",                   "0452-2562024"),
    ("District Manager, TAHDCO", "SCA",  "NSFDC", "Chennai",       "Collectorate, Chennai 600005",              ALL_SCHEMES,                  "Ezhilagam, Chepauk, Chennai 600005",              "044-28520952"),
    ("State Bank of India",      "PSB",  "NSFDC", "Chennai",       "Rajaji Salai",                              "TERM_LOAN,EDUCATION_LOAN",   "33, Rajaji Salai, Chennai 600001",                "044-25330351"),
    ("Indian Overseas Bank",     "PSB",  "NSFDC", "Chennai",       "Anna Salai",                                "TERM_LOAN,MICRO_FINANCE",    "763, Anna Salai, Chennai 600002",                 "044-28519574"),
    ("District Manager, TAHDCO", "SCA",  "NSFDC", "Coimbatore",    "Collectorate, Coimbatore 641018",           ALL_SCHEMES,                  "Collectorate, Coimbatore 641018",                 "0422-2301170"),
    ("Canara Bank — Coimbatore", "PSB",  "NSFDC", "Coimbatore",    "RS Puram",                                  "TERM_LOAN,MICRO_FINANCE,EDUCATION_LOAN","DB Road, RS Puram, Coimbatore 641002","0422-2546470"),
    ("District Manager, TAHDCO", "SCA",  "NSFDC", "Tirunelveli",   "Collectorate, Tirunelveli 627002",          ALL_SCHEMES,                  "Collectorate, Tirunelveli 627002",                "0462-2502142"),
    ("Indian Bank — Tirunelveli","PSB",  "NSFDC", "Tirunelveli",   "S.N. Road",                                 "TERM_LOAN,MICRO_FINANCE",    "S.N. Road, Tirunelveli 627001",                   "0462-2332417"),
    ("District Manager, TAHDCO", "SCA",  "NSFDC", "Thanjavur",     "Collectorate, Thanjavur 613001",            ALL_SCHEMES,                  "Collectorate, Thanjavur 613001",                  "04362-230245"),
    ("Pandyan Grama Bank",       "RRB",  "NSFDC", "Virudhunagar",  "Vishwanathapuram",                          "MICRO_FINANCE,MAHILA_SAMRIDHI","Vishwanathapuram, Virudhunagar 626001",        "04562-280222"),
    ("District Manager, TAHDCO", "SCA",  "NSKFDC","Madurai",       "Collectorate, Madurai 625001",              "NSKFDC_SWACHH",              "Collectorate Complex, Madurai 625001",            "0452-2531730"),
]

def main():
    con = sqlite3.connect(DB)
    con.executescript(open(SCHEMA).read())
    con.execute("DELETE FROM partners")
    con.executemany("""INSERT INTO partners (name,ptype,fdc,district,block,schemes,address,contact,last_verified)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    [(n,t,f,d,b,sc,a,c,VER) for (n,t,f,d,b,sc,a,c) in PARTNERS])

    # ---- Users: Ravi (applicant), TAHDCO officer, admin
    def uid(mobile, name, role, district, org="", lang="ta", inc=380000, woman=0):
        con.execute("""INSERT OR IGNORE INTO users (name,mobile,role,org,district,language,family_income,is_woman)
                       VALUES (?,?,?,?,?,?,?,?)""", (name,mobile,role,org,district,lang,inc,woman))
        return con.execute("SELECT id FROM users WHERE mobile=?", (mobile,)).fetchone()[0]

    ravi   = uid("98XXXXXX01", "Ravi Kumar",  "applicant", "Madurai", lang="ta")
    off1   = uid("98XXXXXX02", "S. Priya",    "officer",   "Madurai", org="TAHDCO — District Manager Office")
    uid("98XXXXXX99", "Admin — MoSJE Cell", "admin", "Chennai", org="PM-SURAJ Monitoring Cell", lang="en")

    # ---- Ravi's Term Loan application — mid-journey (stage 6: credit assessment)
    con.execute("DELETE FROM applications WHERE app_no='PMS2026-TN-004217'")
    partner = con.execute("SELECT id FROM partners WHERE district='Madurai' AND ptype='PSB' LIMIT 1").fetchone()[0]
    cur = con.execute("""INSERT INTO applications (app_no,user_id,fdc,scheme_id,amount,project_cost,purpose,stage,status,partner_id)
                         VALUES ('PMS2026-TN-004217',?,?,?,?,?,?,?,?,?)""",
                      (ravi,"NSFDC","TERM_LOAN",300000,400000,"business",6,"QUERY_RAISED",partner))
    appid = cur.lastrowid

    # ---- Status timeline (grounded dates, shows SLA per stage)
    timeline = [
        (1,"SUBMITTED","APPLICANT","Application filed via CSC-assisted PM-SURAJ flow",0,"2026-07-14 10:22"),
        (2,"INITIAL_SCRUTINY","TAHDCO","Received at District Manager office, Madurai. Master register entry done.",2,"2026-07-16 11:05"),
        (3,"DOCUMENT_VERIFICATION","TAHDCO","Caste certificate ✔ verified (TN Revenue Dept). Income certificate verified.",4,"2026-07-20 15:40"),
        (4,"ELIGIBILITY_VERIFICATION","TAHDCO","SC ✔ · family income ₹3.8L within ₹5L ceiling (NSFDC rule, w.e.f. 07-01-2026) ✔",3,"2026-07-23 12:10"),
        (5,"FORWARDED_TO_CP","SYSTEM","Forwarded to Canara Bank, Town Hall Road — NSFDC channel partner for Term Loan",2,"2026-07-25 09:30"),
        (6,"CREDIT_ASSESSMENT","BANK_OFFICER","Project report under appraisal. Electrical repair workshop — viability & DSCR check in progress.",18,""),
    ]
    for stage,key,actor,note,days,ts in timeline:
        if ts:
            con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note,days_taken,created_at)
                           VALUES (?,?,?,?,?,?,?)""", (appid,stage,key,actor,note,days,ts))
        else:
            con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note,days_taken)
                           VALUES (?,?,?,?,?,?)""", (appid,stage,key,actor,note,days))

    # ---- Queries: one resolved (data mismatch demo), one OPEN (blocking)
    con.execute("""INSERT INTO queries (app_id,raised_by,category,title,detail,action_by,blocking,status,resolution,created_at,resolved_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
               (appid,"TAHDCO — Doc Cell","DATA_MISMATCH","Name mismatch across documents",
                "Aadhaar shows 'RAVI KUMAR' but caste certificate shows 'RAVIKUMAR'. Please confirm correct spelling or upload corrected certificate.",
                "APPLICANT",1,"RESOLVED",
                "Applicant submitted corrected caste certificate from Tahsildar (Name: RAVI KUMAR). Verified against Aadhaar. ✔",
                "2026-07-17 14:20","2026-07-19 10:05"))
    con.execute("""INSERT INTO queries (app_id,raised_by,category,title,detail,action_by,blocking,status,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
               (appid,"Canara Bank — Credit Cell","DOCUMENT","Updated bank statement required",
                "Last 6 months bank statement needed for credit assessment. Your uploaded statement covers only 4 months. Upload the full 6-month statement to avoid sanction delay.",
                "APPLICANT",1,"OPEN","2026-08-10 16:45"))

    # ---- Documents
    for dt,st,nt in [("caste_cert","VERIFIED","Verified — TN Revenue Dept"),
                     ("income_proof","VERIFIED","Tahsildar certificate ₹3.8L"),
                     ("id_proof","VERIFIED","Aadhaar ✔"),
                     ("bank","ON_FILE","4-month statement — needs update (see query Q-2)"),
                     ("project_plan","VERIFIED","Workshop project report appraised")]:
        con.execute("INSERT OR IGNORE INTO documents (user_id,app_id,doc_type,status,note) VALUES (?,?,?,?,?)",
                    (ravi,appid,dt,st,nt))

    con.commit()
    print(f"✔ {con.execute('SELECT COUNT(*) FROM partners').fetchone()[0]} partners · "
          f"app {appid} seeded with {len(timeline)}-stage timeline · 2 queries (1 open)")

if __name__ == "__main__":
    main()
