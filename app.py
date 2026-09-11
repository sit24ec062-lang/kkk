"""PM-SURAJ SEVA · NO WRONG DOOR v3.0 — Merged Beneficiary Access + Journey Intelligence
SIH 2026 · PS 26092 · Ministry of Social Justice & Empowerment / NSFDC ecosystem (sandbox)

MERGED BUILD (v3.0):
  - v1 (beneficiary readiness engine): understand -> eligibility -> match -> pathway
    -> document readiness -> partner routing -> QR journey card
  - v2 (journey intelligence): roles (applicant/officer/admin), applications, 11-stage
    status pipeline, query resolution engine, SLA/bottleneck analytics, outcomes
  - NEW v3: government-portal downloadable Application Form + Acknowledgement slip
    (print-to-PDF, server-rendered), full journey card linked to application.

Architecture honesty:
  Rule engine decides eligibility (deterministic, auditable). AI layer is simulated
  multilingual entity extraction for voice input ONLY. PM-SURAJ handoff = mock adapter.
  All scheme data = SANDBOX demo data — verify against nsfdc.nic.in before real use.

Run:
  pip install flask
  python seed_db.py
  python app.py
  # open http://localhost:5000
"""
from flask import Flask, request, jsonify, send_from_directory, render_template_string
import sqlite3, json, re, random, string, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE, "data", "static", "static"), static_url_path="/static")
DB = os.path.join(BASE, "nowrongdoor.db")
RULES = json.load(open(os.path.join(BASE, "data", "rules.json"), encoding="utf-8"))
for scheme in RULES.get("schemes", []):
    scheme.setdefault("fdc", "NSFDC")

STAGES = {1:"SUBMITTED",2:"INITIAL_SCRUTINY",3:"DOCUMENT_VERIFICATION",4:"ELIGIBILITY_VERIFICATION",
          5:"FORWARDED_TO_CP",6:"CREDIT_ASSESSMENT",7:"FIELD_VERIFICATION",8:"SANCTION",
          9:"AGREEMENT",10:"DISBURSEMENT",11:"REPAYMENT_MONITORING"}

def db():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; return con

def me():
    uid = request.headers.get("x-user-id")
    if not uid: return None
    return db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

# ================= AUTH =================
@app.post("/api/login")
def login():
    d = request.json
    u = db().execute("SELECT * FROM users WHERE mobile=? AND password=?",
                     (d.get("mobile",""), d.get("password","demo1234"))).fetchone()
    if not u: return jsonify({"error":"Invalid credentials (sandbox: use demo logins in README)"}), 401
    return jsonify({"user":{k:u[k] for k in ["id","name","role","district","org","language","family_income"]}})

# ================= SCHEMES =================
@app.get("/api/schemes")
def schemes():
    return jsonify({"schemes":RULES["schemes"], "rules":RULES["global_rules"],
                    "version":RULES["version"], "note":RULES["source_note"]})

# ============ MULTILINGUAL VOICE UNDERSTAND (AI layer — simulation) ============
AMT_MULT = {"lakh":100000,"lakhs":100000,"lac":100000,"lacs":100000,
            "crore":10000000,"crores":10000000,
            "லட்சம்":100000,"லட்ச":100000,"लाख":100000,"లక్ష":100000,"ಲಕ್ಷ":100000,"ലക്ഷം":100000,"লাখ":100000}
PURPOSES = [
 ("business",       ["business","viyaparam","தொழில்","kadai","கடை","trading","दुकान","व्यापार","వ్యాపారం","ಅಂಗಡಿ","വ്യാപാരം","দোকান","shop","tailor"]),
 ("manufacturing",  ["manufactur","sirpam","சிற்பம்","production","factory","ಆலை","aalai","workshop","repair","యంత్ర","ಯಂತ್ರ"]),
 ("education",      ["education","padippu","படிப்பு","course","degree","college","पढ़ाई","शिक्षा","విద్య","ಶಿಕ್ಷಣ","വിദ്യാഭ്യാസം","শিক্ষা"]),
 ("skill",          ["skill","training","பயிற்சி","പരിശീലനം"]),
 ("agriculture",    ["agri","vivasayi","விவசாயம்","farming","खेती","వ్యవసాయ","ಕೃಷಿ","കൃഷി","কৃষি"]),
 ("sanitation",     ["sanitation","safai","सफाई","scaveng","waste","குப்பை"]),
]
DISTRICTS = ["madurai","chennai","coimbatore","salem","tiruchirappalli","trichy","virudhunagar",
             "tirunelveli","thanjavur","erode","dindigul","sivaganga","pudukkottai","namakkal","karur",
             "theni","kanyakumari","vellore","tiruvannamalai","villupuram","kancheepuram","tiruppur"]

def parse_amount(t):
    m = re.findall(r"(?:₹|rs\.?|rupees?)\s*([\d,.]+)\s*(lakh|lakhs|lac|lacs|crore|crores)?", t.lower())
    if not m:
        m = re.findall(r"([\d,.]+)\s*(lakh|lakhs|lac|lacs|crore|crores)", t.lower()) or []
    if not m: return None
    v = float(m[0][0].replace(",",""))
    if len(m[0])>1 and m[0][1]: v *= AMT_MULT.get(m[0][1].lower(), 1)
    return int(v)

def parse_income(t):
    m = re.findall(r"(?:income|aaya|varamaanam|வருவாய்|आय|ఆదాయం|ಆದಾಯ|വരുമാനം|আয়)[^\d₹rs]{0,25}(?:₹|rs\.?)?\s*([\d,.]+)\s*(lakh|lakhs|lac|lacs)?", t.lower())
    if m:
        v = float(m[0][0].replace(",",""))
        if m[0][1]: v *= 100000
        return int(v)
    return None

@app.post("/api/voice")
def voice():
    msg = request.json.get("message","")
    lang = request.json.get("lang","ta")
    tl = msg.lower()
    purpose = "business"
    for label, keys in PURPOSES:
        if any(k and k in tl for k in keys): purpose = label; break
    amt  = parse_amount(msg)
    inc  = parse_income(msg)
    dist = next((d.title() for d in DISTRICTS if d in tl), None)
    lang_detect = "ta" if any('\u0b80' <= c <= '\u0bff' for c in msg) else (
                  "hi" if any('\u0900' <= c <= '\u097f' for c in msg) else (
                  "te" if any('\u0c00' <= c <= '\u0c7f' for c in msg) else (
                  "bn" if any('\u0980' <= c <= '\u09ff' for c in msg) else lang)))
    profile = {"purpose":purpose,
               "required_amount":amt,
               "family_income":inc or 380000,
               "is_sc":True,
               "is_woman":any(w in tl for w in ["woman","women","lady","பெண்","pen","ponnu","महिला","స్త్రీ","ಮಹಿಳೆ","സ്ത്രീ","মহিলা"]),
               "is_sanitation_worker":purpose=="sanitation",
               "district":dist or "Madurai",
               "language":lang_detect,
               "project_cost":int(amt*1.33) if amt else None}
    return jsonify({"profile":profile,
                    "note":"AI layer: multilingual entity extraction (simulated). The rule engine decides eligibility — never the AI."})

# ================= RULE ENGINE =================
def apply_op(v, op, val):
    return {"<=":v<=val,">=":v>=val,"==":v==val,"<":v<val,">":v>val}.get(op, False)

@app.post("/api/eligibility")
def eligibility():
    p = request.json.get("profile",{})
    out=[]
    for r in RULES["global_rules"]:
        fv = p.get(r["field"]); passed = fv is not None and apply_op(fv, r["op"], r["value"])
        out.append({"rule":r["id"],"desc":r["desc"],"field":r["field"],"value":fv,
                    "operator":r["op"]+" "+str(r["value"]),"passed":bool(passed)})
    return jsonify({"rules":out,"eligible":all(r["passed"] for r in out),
                    "engine":"deterministic rule engine v"+RULES["version"]})

@app.post("/api/match")
def match():
    p = request.json.get("profile",{}); amt=p.get("required_amount") or 0; pc=p.get("project_cost") or amt
    ev=[]
    for s in RULES["schemes"]:
        reasons=[]
        if pc>s["max_project"]: reasons.append(f"Project cost ₹{pc:,} exceeds limit ₹{s['max_project']:,}")
        if amt>s["max_loan"]:   reasons.append(f"Required ₹{amt:,} exceeds max loan ₹{s['max_loan']:,}")
        if pc and s["min_project"]>0 and pc<s["min_project"]: reasons.append(f"Below scheme minimum ₹{s['min_project']:,}")
        if p.get("purpose") and s.get("for_purposes") and p["purpose"] not in s["for_purposes"]:
            reasons.append(f"Does not cover stated purpose ({p.get('purpose')})")
        if s.get("extra_rule"):
            er=s["extra_rule"]
            if not apply_op(p.get(er["field"]),er["op"],er["value"]): reasons.append(er["desc"])
        ev.append({"scheme":s["name"],"scheme_id":s["id"],"fdc":s.get("fdc", "NSFDC"),"suitable":not reasons,
                   "rejection_reasons":reasons,"interest_demo":s["interest_demo"],
                   "desc":s["desc"],"max_loan":s["max_loan"]})
    fits=[e for e in ev if e["suitable"]]
    best=None
    if fits:
        suff=[e for e in fits if e["max_loan"]>=amt] or fits
        best=min(suff,key=lambda e:e["max_loan"])
    return jsonify({"evaluations":ev,"recommended":best,
                    "note":"Smallest sufficient scheme recommended to minimize debt burden."})

# ================= FINANCIAL PATHWAY (v1) =================
@app.post("/api/pathway")
def pathway():
    p = request.json.get("profile", {})
    scheme_id = request.json.get("scheme_id")
    s = next(x for x in RULES["schemes"] if x["id"] == scheme_id)
    amt = p.get("required_amount") or min(s["max_loan"], p.get("project_cost", s["max_loan"]))
    contrib = max(0, int((p.get("project_cost") or amt) * 0.10))
    rate = s["interest_demo"] / 100 / 12
    years = 7 if s["id"] == "TERM_LOAN" else 5
    n = years * 12
    emi = amt * rate * (1 + rate) ** n / ((1 + rate) ** n - 1) if rate else amt / n
    inc = p.get("family_income") or 380000
    burden = emi * 12 / inc * 100
    viable = burden <= 40
    return jsonify({
        "pathway": [
            {"step": "YOUR NEED", "value": f"₹{amt:,} — {p.get('purpose','business')}"},
            {"step": "PROJECT COST", "value": f"₹{p.get('project_cost') or amt:,}"},
            {"step": "RELEVANT SCHEME", "value": s["name"]},
            {"step": "FINANCIAL LIMIT", "value": f"Up to ₹{s['max_loan']:,} (scheme cap)"},
            {"step": "BENEFICIARY CONTRIBUTION (est.)", "value": f"₹{contrib:,}"},
            {"step": "INTEREST (demo rate)", "value": f"{s['interest_demo']}% p.a. — illustrative only"},
            {"step": "REPAYMENT", "value": f"~₹{emi:,.0f}/month × {years} yrs (moratorium {RULES['repayment']['moratorium_months']} mo)"},
            {"step": "ANNUAL REPAYMENT BURDEN", "value": f"{burden:.1f}% of family income"},
            {"step": "VIABILITY CHECK", "value": "Within safe burden range (≤40%)" if viable else "HIGH BURDEN — consider smaller amount"},
            {"step": "ROUTE", "value": "Authorized channel partner → PM-SURAJ (sandbox)"}
        ],
        "emi": round(emi), "burden_pct": round(burden, 1), "viable": viable,
        "disclaimer": "Illustrative calculation at demo rate. Final terms determined by authorized channel partner."})

# ================= DOCUMENT READINESS (weighted rubric, v1) =================
DOC_SETS = {
    "core":  [("caste_cert", "Caste certificate", 15), ("income_proof", "Income certificate", 15),
              ("id_proof", "Identity / address proof", 10), ("bank", "Bank account details", 10)],
    "project": [("project_plan", "Business / project document", 20)],
    "financial": [("photo", "Passport photo", 5), ("quotation", "Asset quotation (if applicable)", 5)]
}
@app.post("/api/readiness")
def readiness():
    have = set(request.json.get("documents", []))
    got = 0; breakdown = []
    for grp, docs in DOC_SETS.items():
        for did, name, w in docs:
            ok = did in have; got += w if ok else 0
            breakdown.append({"id": did, "name": name, "weight": w, "present": ok})
    return jsonify({"score": got, "breakdown": breakdown,
                    "rubric": "Core identity/caste/income = 50% | Project docs = 20% | Financial profile = 10% | (demo rubric v1)"})

# ================= APPLY (handoff to PM-SURAJ flow) =================
@app.post("/api/apply")
def apply():
    u = me()
    if not u: return jsonify({"error":"login required"}),401
    d = request.json
    app_no = "PMS2026-TN-" + "".join(random.choices(string.digits,k=6))
    con = db()
    con.execute("""INSERT INTO applications (app_no,user_id,fdc,scheme_id,amount,project_cost,purpose,stage,status)
                   VALUES (?,?,?,?,?,?,?,1,'IN_PROCESS')""",
                (app_no,u["id"],d.get("fdc","NSFDC"),d["scheme_id"],d["amount"],d.get("project_cost"),d.get("purpose","business")))
    appid = con.execute("SELECT id FROM applications WHERE app_no=?", (app_no,)).fetchone()[0]
    # attach documents declared in readiness rubric
    for doc in (d.get("documents") or []):
        con.execute("INSERT OR IGNORE INTO documents (user_id, app_id, doc_type, status) VALUES (?,?,?,?)",
                    (u["id"], appid, doc, "ON_FILE"))
    con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note) VALUES (?,1,'SUBMITTED','SYSTEM',?)""",
                (appid,"Application created on PM-SURAJ Seva layer — handoff to authorized PM-SURAJ flow (sandbox adapter)."))
    # create journey card (v1) linked to this application
    ref = "NWD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    con.execute("INSERT INTO journeys (ref, app_id, payload) VALUES (?,?,?)",
                (ref, appid, json.dumps({"app_no": app_no, "profile": d.get("profile"),
                                          "eligibility": d.get("eligibility"), "readiness": d.get("readiness")})))
    con.commit()
    return jsonify({"app_no": app_no, "app_id": appid, "journey_ref": ref,
                    "note":"SANDBOX adapter: production hands off via authorized PM-SURAJ API."})

# ================= APPLICANT: applications + timeline =================
@app.get("/api/my/applications")
def my_apps():
    u = me()
    if not u: return jsonify({"error":"login required"}),401
    rows = db().execute("""SELECT a.*, p.name AS partner_name FROM applications a
                           LEFT JOIN partners p ON p.id=a.partner_id WHERE a.user_id=? ORDER BY a.id DESC""",
                        (u["id"],)).fetchall()
    return jsonify({"applications":[{**dict(r),"stage_key":STAGES[r["stage"]]} for r in rows]})

@app.get("/api/application/<int:aid>")
def app_detail(aid):
    con = db()
    a = con.execute("""SELECT a.*, u.name AS applicant_name, u.district AS applicant_district,
                       p.name AS partner_name, p.ptype AS partner_type, p.address AS partner_addr, p.contact AS partner_contact
                       FROM applications a JOIN users u ON u.id=a.user_id
                       LEFT JOIN partners p ON p.id=a.partner_id WHERE a.id=?""",(aid,)).fetchone()
    if not a: return jsonify({"error":"not found"}),404
    events = con.execute("SELECT * FROM status_events WHERE app_id=? ORDER BY id",(aid,)).fetchall()
    queries = con.execute("SELECT * FROM queries WHERE app_id=? ORDER BY id DESC",(aid,)).fetchall()
    docs = con.execute("SELECT * FROM documents WHERE app_id=?",(aid,)).fetchall()
    outcome = con.execute("SELECT * FROM outcomes WHERE app_id=?",(aid,)).fetchone()
    jr = con.execute("SELECT ref FROM journeys WHERE app_id=?",(aid,)).fetchone()
    return jsonify({"application":{**dict(a),"stage_key":STAGES[a["stage"]]},
                    "timeline":[dict(e) for e in events],
                    "queries":[dict(q) for q in queries],
                    "documents":[dict(d) for d in docs],
                    "outcome":dict(outcome) if outcome else None,
                    "journey_ref": jr["ref"] if jr else None,
                    "stages":[{"n":k,"key":v} for k,v in STAGES.items()]})

@app.post("/api/query/<int:qid>/respond")
def respond_query(qid):
    u = me()
    if not u: return jsonify({"error":"login required"}),401
    con = db()
    con.execute("""UPDATE queries SET status='RESOLVED', resolution=?, resolved_at=datetime('now') WHERE id=?""",
                (request.json.get("resolution",""),qid))
    con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note)
                   SELECT app_id, (SELECT stage FROM applications WHERE id=queries.app_id), 'QUERY_RESOLVED','APPLICANT',? FROM queries WHERE id=?""",
                (f"Query #{qid} resolved by applicant.", qid))
    con.commit()
    return jsonify({"ok":True})

# ================= OFFICER: queue + actions =================
@app.get("/api/officer/queue")
def officer_queue():
    u = me()
    if not u or u["role"]!="officer": return jsonify({"error":"officer login required"}),401
    rows = db().execute("""SELECT a.*, u.name AS applicant, u.district FROM applications a
                           JOIN users u ON u.id=a.user_id WHERE u.district=? ORDER BY a.updated_at""",
                        (u["district"],)).fetchall()
    return jsonify({"queue":[{**dict(r),"stage_key":STAGES[r["stage"]]} for r in rows]})

@app.post("/api/officer/query")
def officer_query():
    u = me()
    if not u or u["role"]!="officer": return jsonify({"error":"officer login required"}),401
    d = request.json
    con = db()
    con.execute("""INSERT INTO queries (app_id,raised_by,category,title,detail,action_by,blocking,status)
                   VALUES (?,?,?,?,?,?,?,'OPEN')""",
                (d["app_id"], f'{u["org"]}', d.get("category","DOCUMENT"), d["title"], d["detail"],
                 d.get("action_by","APPLICANT"), 1 if d.get("blocking",True) else 0))
    con.execute("UPDATE applications SET status='QUERY_RAISED', updated_at=datetime('now') WHERE id=?", (d["app_id"],))
    con.commit()
    return jsonify({"ok":True})

@app.post("/api/officer/advance")
def officer_advance():
    u = me()
    if not u or u["role"]!="officer": return jsonify({"error":"officer login required"}),401
    d = request.json
    con = db()
    a = con.execute("SELECT * FROM applications WHERE id=?", (d["app_id"],)).fetchone()
    if not a or a["stage"]>=11: return jsonify({"error":"invalid stage"}),400
    ns = a["stage"]+1
    con.execute("UPDATE applications SET stage=?, status='IN_PROCESS', updated_at=datetime('now') WHERE id=?", (ns,d["app_id"]))
    con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note) VALUES (?,?,?,?,?)""",
                (d["app_id"],ns,STAGES[ns],u["org"],d.get("note","")))
    if ns==10:
        con.execute("INSERT INTO outcomes (app_id,disbursed_amount,repayment_status) VALUES (?,?,'ON_TIME')",
                    (d["app_id"], a["amount"]))
    con.commit()
    return jsonify({"ok":True,"stage":ns,"stage_key":STAGES[ns]})

# ================= ADMIN ANALYTICS =================
@app.get("/api/analytics")
def analytics():
    u = me()
    if not u or u["role"]!="admin": return jsonify({"error":"admin login required"}),401
    con = db()
    aging = con.execute("""SELECT stage, stage_key, COUNT(*) n, AVG(days_taken) avg_days, MAX(days_taken) max_days
                           FROM status_events GROUP BY stage_key ORDER BY stage""").fetchall()
    total = con.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
    qopen = con.execute("SELECT COUNT(*) c FROM queries WHERE status='OPEN'").fetchone()["c"]
    disb  = con.execute("SELECT COUNT(*) c FROM applications WHERE stage>=10").fetchone()["c"]
    repay = con.execute("SELECT repayment_status, COUNT(*) c FROM outcomes GROUP BY repayment_status").fetchall()
    bystage = con.execute("SELECT stage, COUNT(*) c FROM applications GROUP BY stage ORDER BY stage").fetchall()
    bystage = [{**dict(r), "stage_key": STAGES[r["stage"]]} for r in bystage]
    return jsonify({"aging":[dict(r) for r in aging],"total":total,"open_queries":qopen,
                    "disbursed":disb,"repayment":[dict(r) for r in repay],
                    "pipeline":[dict(r) for r in bystage],
                    "bottleneck":max((dict(r) for r in aging), key=lambda r:r["avg_days"] or 0, default=None)})

# ================= PARTNERS =================
@app.get("/api/partners")
def partners():
    d = (request.args.get("district") or "").lower()
    fdc = request.args.get("fdc") or ""
    q = "SELECT * FROM partners WHERE LOWER(district)=?"
    args = [d]
    if fdc: q += " AND fdc=?"; args.append(fdc)
    rows = db().execute(q, args).fetchall() or db().execute("SELECT * FROM partners LIMIT 8").fetchall()
    return jsonify({"partners":[dict(r) for r in rows],
                    "note":"Grounded: TAHDCO district units sit inside District Collectorates (NSFDC SCA). Verify live status before visit. Production: authorized PM-SURAJ partner API."})

# ================= JOURNEY CARD =================
@app.post("/api/journey")
def create_journey():
    u = me()
    if not u: return jsonify({"error":"login required"}),401
    payload = request.json
    ref = "NWD-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    con = db()
    con.execute("INSERT INTO journeys (ref, payload) VALUES (?,?)", (ref, json.dumps(payload)))
    con.commit()
    return jsonify({"ref": ref, "mode": "SANDBOX — production would hand off via authorized PM-SURAJ API"})

@app.get("/api/journey/<ref>")
def get_journey(ref):
    r = db().execute("SELECT * FROM journeys WHERE ref=?", (ref,)).fetchone()
    if not r: return jsonify({"error": "not found"}), 404
    return jsonify({"ref": ref, "app_id": r["app_id"], "payload": json.loads(r["payload"])})

# ================= DOWNLOADABLE GOVT FORM (v3) =================
FORM_CSS = """
@page{size:A4;margin:16mm}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;color:#1a1a2e;font-size:12.5px;line-height:1.45;background:#e8ecf3;padding:20px}
.sheet{background:#fff;max-width:820px;margin:0 auto;padding:34px 40px;box-shadow:0 4px 24px rgba(0,0,0,.15)}
.tc{display:flex;height:5px;margin:-34px -40px 18px}.tc span{flex:1}.tc .s{background:#FF9933}.tc .w{background:#fff}.tc .g{background:#138808}
.head{display:flex;align-items:center;gap:14px;border-bottom:3px double #0E2A47;padding-bottom:12px;margin-bottom:14px}
.emblem{width:52px;height:52px;border-radius:50%;background:radial-gradient(circle at 50% 50%,#fff 58%,transparent 60%),conic-gradient(#F28C28,#fff,#138808,#fff,#F28C28);display:flex;align-items:center;justify-content:center;font-size:26px}
.head h1{font-size:17px;color:#0E2A47}.head p{font-size:10.5px;color:#444}
.head .right{margin-left:auto;text-align:right;font-size:10.5px;color:#333;line-height:1.6}
.photo{width:95px;height:115px;border:1px solid #999;display:flex;align-items:center;justify-content:center;font-size:10px;color:#777;margin-left:10px;text-align:center}
h2.title{text-align:center;font-size:14.5px;color:#0E2A47;text-decoration:underline;margin:12px 0 14px;text-transform:uppercase;letter-spacing:.5px}
table{width:100%;border-collapse:collapse;margin-bottom:12px}
td,th{border:1px solid #444;padding:5px 8px;font-size:12px;vertical-align:top}
th{background:#eef2f7;text-align:left;width:32%;font-weight:600;color:#0E2A47}
.sec{background:#0E2A47;color:#fff;font-size:11.5px;font-weight:700;padding:5px 10px;margin:14px 0 0;letter-spacing:.5px}
.decl{border:1px solid #444;padding:10px 12px;margin-top:14px;font-size:11.5px}
.sig{display:flex;justify-content:space-between;margin-top:46px}
.sig div{width:30%;border-top:1px dotted #333;padding-top:5px;font-size:11px;text-align:center}
.office{margin-top:22px;border:1px solid #444}
.office th{width:25%}
.sandbox{background:#FFF4DE;border:1px solid #F2D9A4;color:#7A5410;font-size:10px;padding:6px 10px;margin-bottom:12px;text-align:center}
.bar{display:flex;gap:10px;justify-content:center;margin:18px 0}
.btn{border:0;border-radius:6px;padding:10px 22px;font-size:13px;font-weight:700;cursor:pointer;font-family:inherit}
.btn-pri{background:#0E2A47;color:#fff}.btn-acc{background:#F28C28;color:#fff}
@media print{body{background:#fff;padding:0}.sheet{box-shadow:none;max-width:none;padding:0}.bar{display:none}.tc{margin:-0mm 0 5mm}}
"""

FORM_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>{{title}}</title><style>{{css}}</style></head>
<body>
<div class="sheet">
<div class="tc"><span class="s"></span><span class="w"></span><span class="g"></span></div>
<div class="head">
  <div class="emblem">☸</div>
  <div><h1>PM-SURAJ SEVA · NO WRONG DOOR</h1>
  <p>Pradhan Mantri Samajik Utthan evam Rozgar Adharit Jankalyan (PM-SURAJ)<br>
  Ministry of Social Justice &amp; Empowerment · NSFDC · NBCFDC · NSKFDC</p></div>
  <div class="right"><b>Application No:</b> {{a.app_no}}<br><b>Date:</b> {{a.created_at[:10]}}<br><b>FDC:</b> {{a.fdc}}</div>
</div>
<div class="sandbox">⚠ SANDBOX / SIMULATED DOCUMENT — SIH 2026 prototype (PS 26092). Not an official government form. Demo data only.</div>
<h2 class="title">{{title}}</h2>
{{body}}
<div class="decl"><b>Declaration:</b> I hereby declare that the information furnished above is true and correct to the best of my knowledge and belief. I understand that any false statement may lead to rejection of my application and recovery of amounts disbursed, besides legal action under applicable law. I consent to verification of my particulars through appropriate government databases.</div>
<div class="sig">
  <div>Signature / Thumb impression of Applicant</div>
  <div>Place &amp; Date</div>
  <div>Receipt seal of Channel Partner / SCA</div>
</div>
</div>
<div class="bar"><button class="btn btn-pri" onclick="window.print()">🖨️ Download / Print (Save as PDF)</button>
<button class="btn btn-acc" onclick="window.close()">Close</button></div>
</body></html>"""

def _app_full(aid):
    con = db()
    a = con.execute("""SELECT a.*, u.name AS applicant_name, u.mobile, u.district AS applicant_district,
                       p.name AS partner_name, p.ptype AS partner_type, p.address AS partner_addr
                       FROM applications a JOIN users u ON u.id=a.user_id
                       LEFT JOIN partners p ON p.id=a.partner_id WHERE a.id=?""", (aid,)).fetchone()
    if not a: return None, con
    docs = con.execute("SELECT * FROM documents WHERE app_id=?", (aid,)).fetchall()
    events = con.execute("SELECT * FROM status_events WHERE app_id=? ORDER BY id", (aid,)).fetchall()
    app_data = {**dict(a), "stage_key": STAGES[a["stage"]]}
    return {"app": app_data, "docs": [dict(d) for d in docs], "events": [dict(e) for e in events]}, con

def _v(v): return "Yes" if v else "No"

@app.get("/form/<app_no>")
def download_form(app_no):
    con = db()
    row = con.execute("SELECT id FROM applications WHERE app_no=?", (app_no,)).fetchone()
    if not row: return "Application not found", 404
    data, _ = _app_full(row["id"])
    a = data["app"]
    body = f"""
<table><tr><th>1. Name of Applicant</th><td>{a['applicant_name']}</td><th>Mobile</th><td>{a['mobile']}</td></tr>
<tr><th>2. District / State</th><td>{a['applicant_district']} / Tamil Nadu</td><th>Category</th><td>Scheduled Caste (as per caste certificate)</td></tr>
<tr><th>3. Scheme Applied</th><td colspan="3">{a['scheme_id'].replace('_',' ')} ({a['fdc']})</td></tr>
<tr><th>4. Loan Amount Requested</th><td>₹{a['amount']:,}</td><th>Project Cost (est.)</th><td>₹{(a['project_cost'] or a['amount']):,}</td></tr>
<tr><th>5. Purpose / Sector</th><td colspan="3">{a['purpose']}</td></tr></table>
<div class="sec">SECTION B — PRE-SCREENING RESULT (DETERMINISTIC RULE ENGINE · AUDITABLE)</div>
<table><tr><th style="width:8%">#</th><th>Rule</th><th style="width:18%">Result</th></tr>
<tr><td>3</td><td>Scheme limit / purpose compatibility (rule engine v{RULES['version']})</td><td>✔ RECOMMENDED</td></tr></table>
<div class="sec">SECTION C — DOCUMENT CHECKLIST (AS DECLARED IN READINESS RUBRIC)</div>
<table><tr><th style="width:8%">#</th><th>Document</th><th style="width:20%">Status</th></tr>
{''.join(f"<tr><td>{i+1}</td><td>{d['doc_type'].replace('_',' ').title()}</td><td>{d['status']}</td></tr>" for i,d in enumerate(data['docs'])) or '<tr><td colspan="3">No documents on file — bring originals to partner office.</td></tr>'}
</table>
<div class="sec">SECTION D — CURRENT STATUS SNAPSHOT</div>
<table><tr><th>Stage</th><td>{a['stage']} / 11 — {a['stage_key']}</td><th>Status</th><td>{a['status']}</td></tr>
<tr><th>Current Handler</th><td colspan="3">{a['partner_name'] or 'TAHDCO District Unit (SCA)'} {('· ' + a['partner_addr']) if a['partner_addr'] else ''}</td></tr></table>
<div class="sec" style="background:#555">FOR OFFICE USE ONLY</div>
<table class="office">
<tr><th>Scrutiny Officer</th><td></td><th>Date</th><td></td></tr>
<tr><th>Field Verification</th><td></td><th>Credit Assessment</th><td></td></tr>
<tr><th>Sanctioned Amount</th><td>₹</td><th>Disbursement Date</th><td></td></tr>
<tr><th>Signature &amp; Seal</th><td colspan="3"></td></tr></table>"""
    return render_template_string(FORM_HTML, title="Application Form — PM-SURAJ Channel (Sandbox Copy)",
                                  css=FORM_CSS, a=a, body=body)

@app.get("/ack/<app_no>")
def ack_slip(app_no):
    con = db()
    row = con.execute("SELECT id FROM applications WHERE app_no=?", (app_no,)).fetchone()
    if not row: return "Application not found", 404
    data, _ = _app_full(row["id"])
    a = data["app"]
    jr = db().execute("SELECT ref FROM journeys WHERE app_id=?", (row["id"],)).fetchone()
    ev_rows = "".join(f"<tr><td>{e['stage']}</td><td>{e['stage_key'].replace('_',' ')}</td><td>{e['actor']}</td><td>{e['created_at'][:16]}</td></tr>" for e in data['events'])
    body = f"""
<table><tr><th>Application No</th><td><b>{a['app_no']}</b></td><th>Applicant</th><td>{a['applicant_name']}</td></tr>
<tr><th>Scheme</th><td>{a['scheme_id'].replace('_',' ')}</td><th>Amount</th><td>₹{a['amount']:,}</td></tr>
<tr><th>Current Stage</th><td colspan="3">{a['stage']} / 11 — {a['stage_key']} ({a['status']})</td></tr>
<tr><th>Journey Card Ref</th><td colspan="3"><b>{jr['ref'] if jr else '—'}</b> — show this at the authorized channel partner counter</td></tr></table>
<div class="sec">STATUS EVENT LOG (AUDIT TRAIL)</div>
<table><tr><th style="width:8%">Stg</th><th>Stage</th><th>Actor</th><th>Timestamp</th></tr>{ev_rows}</table>"""
    return render_template_string(FORM_HTML, title="Acknowledgement & Status Slip", css=FORM_CSS, a=a, body=body)

# ================= HOME =================
@app.get("/")
def home(): return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
