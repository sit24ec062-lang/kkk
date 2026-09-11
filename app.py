"""PM-SURAJ SEVA · NO WRONG DOOR v2.0 — Beneficiary Journey Intelligence
SIH 2026 · PS 26092 · MoSJE / NSFDC ecosystem (sandbox)

Rule engine decides eligibility (deterministic, auditable).
AI layer = multilingual entity extraction for voice input ONLY.
Demo auth via x-user-id header (sandbox). Production: Aadhaar OTP / NIC SSO.
"""
from flask import Flask, request, jsonify, send_from_directory, g
import sqlite3, json, re, random, string, os, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(BASE, "data", "static", "static"), static_url_path="")
DB = os.path.join(BASE, "nowrongdoor.db")
RULES = json.load(open(os.path.join(BASE, "data", "rules.json")))

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
    if not u: return jsonify({"error":"Invalid credentials (sandbox: use demo logins)"}), 401
    return jsonify({"user":{k:u[k] for k in ["id","name","role","district","org","language","family_income"]}})

# ================= SCHEMES =================
@app.get("/api/schemes")
def schemes():
    return jsonify({"schemes":RULES["schemes"], "rules":RULES["global_rules"],
                    "version":RULES["version"], "note":RULES["source_note"]})

# ================= MULTILINGUAL VOICE UNDERSTAND (AI layer — simulation) =================
AMT_MULT = {"lakh":100000,"lakhs":100000,"lac":100000,"lacs":100000,
            "crore":10000000,"crores":10000000,
            "लाख":100000,"लाखों":100000,"కోట్ల":10000000,"ಲಕ್ಷ":100000,"ലക്ഷം":100000,"লাখ":100000}
PURPOSES = [
 ("business",       ["business","viyaparam","தொழில்","kadai","கடை","trading","दुकान","व्यापार","వ్యాపారం","ಅಂಗಡಿ","വ്യാപാരം","দোকান","shop"]),
 ("manufacturing",  ["manufactur","sirpam","சிற்பம்","production","factory","आल","फैक्ट्री","యంత్ర","ಯಂತ್ರ","ദ്വ","","workshop","repair"]),
 ("education",      ["education","padippu","படிப்பு","course","degree","college","पढ़ाई","शिक्षा","విద్య","ಶಿಕ್ಷಣ","വിദ്യാഭ്യാസം","শিক্ষা","പഠനം","பயிற்சி"]),
 ("skill",          ["skill","training","पரிசீலനை","പരിശീലനം","training"]),
 ("agriculture",    ["agri","vivasayi","விவசாயம்","farming","खेती","వ్యవసాయ","ಕೃಷಿ","കൃഷി","কৃষি"]),
 ("sanitation",     ["sanitation","safai","सफाई","scaveng","waste","குப்பை","మురుగు","கிராம","","",""]),
]
DISTRICTS = ["madurai","chennai","coimbatore","salem","tiruchirappalli","trichy","virudhunagar",
             "tirunelveli","thanjavur","erode","dindigul","sivaganga","pudukkottai","namakkal","karur",
             "theni","kanyakumari","vellore","tiruvannamalai","villupuram","kancheepuram","tiruppur"]

def parse_amount(t):
    m = re.findall(r"(?:₹|rs\\.?|rupees?)\\s*([\\d,.]+)\\s*(lakh|lakhs|lac|lacs|crore|crores)?", t.lower())
    if not m:
        m = re.findall(r"([\\d,.]+)\\s*(lakh|lakhs|lac|lacs|crore|crores)", t.lower()) or []
    if not m: return None
    v = float(m[0][0].replace(",",""))
    if len(m[0])>1 and m[0][1]: v *= AMT_MULT.get(m[0][1].lower(), 1)
    return int(v)

def parse_income(t):
    m = re.findall(r"(?:income|aaya|varamaanam|வருவாய்|आय|ఆదాయం|ಆದಾಯ|വരുമാനം|আয়)[^\\d₹rs]{0,25}(?:₹|rs\\.?)?\\s*([\\d,.]+)\\s*(lakh|lakhs|lac|lacs)?", t.lower())
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
    lang_detect = "ta" if any('\\u0b80' <= c <= '\\u0bff' for c in msg) else (
                  "hi" if any('\\u0900' <= c <= '\\u097f' for c in msg) else (
                  "te" if any('\\u0c00' <= c <= '\\u0c7f' for c in msg) else (
                  "bn" if any('\\u0980' <= c <= '\\u09ff' for c in msg) else lang)))
    profile = {"purpose":purpose,
               "required_amount":amt,
               "family_income":inc or 380000,
               "is_sc":True,
               "is_woman":any(w in tl for w in ["woman","women","lady","பெண்","महिला","స్త్రీ","ಮಹಿಳೆ","സ്ത്രീ","মহিলা","pen"]),
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
        ev.append({"scheme":s["name"],"scheme_id":s["id"],"fdc":s["fdc"],"suitable":not reasons,
                   "rejection_reasons":reasons,"interest_demo":s["interest_demo"],
                   "desc":s["desc"],"max_loan":s["max_loan"]})
    fits=[e for e in ev if e["suitable"]]
    best=None
    if fits:
        suff=[e for e in fits if e["max_loan"]>=amt] or fits
        best=min(suff,key=lambda e:e["max_loan"])
    return jsonify({"evaluations":ev,"recommended":best,
                    "note":"Smallest sufficient scheme recommended to minimize debt burden."})

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
    con.execute("""INSERT INTO status_events (app_id,stage,stage_key,actor,note) VALUES (?,1,'SUBMITTED','SYSTEM',?)""",
                (appid,"Application created on PM-SURAJ Seva layer — handoff to authorized PM-SURAJ flow (sandbox adapter)."))
    con.commit()
    return jsonify({"app_no":app_no,"app_id":appid,
                    "note":"SANDBOX adapter: production hands off via authorized PM-SURAJ API."})

# ================= APPLICANT: my applications + timeline =================
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
    a = con.execute("""SELECT a.*, p.name AS partner_name, p.ptype AS partner_type, p.address AS partner_addr
                       FROM applications a LEFT JOIN partners p ON p.id=a.partner_id WHERE a.id=?""",(aid,)).fetchone()
    if not a: return jsonify({"error":"not found"}),404
    events = con.execute("SELECT * FROM status_events WHERE app_id=? ORDER BY id",(aid,)).fetchall()
    queries = con.execute("SELECT * FROM queries WHERE app_id=? ORDER BY id DESC",(aid,)).fetchall()
    docs = con.execute("SELECT * FROM documents WHERE app_id=?",(aid,)).fetchall()
    outcome = con.execute("SELECT * FROM outcomes WHERE app_id=?",(aid,)).fetchone()
    return jsonify({"application":{**dict(a),"stage_key":STAGES[a["stage"]]},
                    "timeline":[dict(e) for e in events],
                    "queries":[dict(q) for q in queries],
                    "documents":[dict(d) for d in docs],
                    "outcome":dict(outcome) if outcome else None,
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

# ================= ADMIN ANALYTICS (SLA / bottleneck / outcomes) =================
@app.get("/api/analytics")
def analytics():
    u = me()
    if not u or u["role"]!="admin": return jsonify({"error":"admin login required"}),401
    con = db()
    aging = con.execute("""SELECT stage_key, COUNT(*) n, AVG(days_taken) avg_days, MAX(days_taken) max_days
                           FROM status_events GROUP BY stage_key ORDER BY stage""").fetchall()
    total = con.execute("SELECT COUNT(*) c FROM applications").fetchone()["c"]
    qopen = con.execute("SELECT COUNT(*) c FROM queries WHERE status='OPEN'").fetchone()["c"]
    disb  = con.execute("SELECT COUNT(*) c FROM applications WHERE stage>=10").fetchone()["c"]
    repay = con.execute("SELECT repayment_status, COUNT(*) c FROM outcomes GROUP BY repayment_status").fetchall()
    bystage = con.execute("SELECT stage_key, COUNT(*) c FROM applications GROUP BY stage_key").fetchall()
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

@app.get("/")
def home(): return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
