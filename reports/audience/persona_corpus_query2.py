import sqlite3, json, glob, re, statistics as st, os, collections
R="/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar"
con=sqlite3.connect(os.path.join(R,"data/radar.db")); con.row_factory=sqlite3.Row
T={}
for f in sorted(glob.glob(os.path.join(R,"data/analysis/transcripts/*.json"))):
    d=json.load(open(f)); T[d["code"]]=d
VF={r["code"]:dict(r) for r in con.execute("select * from video_features")}
CAP={r["code"]:dict(r) for r in con.execute("select code,cap,play,resh,save from reels group by code")}
def med(codes, field):
    v=[VF[c][field] for c in codes if c in VF and VF[c].get(field) is not None and (VF[c]['play'] or 0)>=100]
    return round(st.median(v),5) if v else None
def blob(c):
    d=T[c]; s=d.get("semantics",{})
    p=[s.get("subtopic",""),s.get("subject",""),s.get("thesis",""),s.get("problem",""),s.get("solution",""),s.get("hook_text","")]
    p+=[b.get("text","") for b in d.get("beats",[])]
    p.append(CAP.get(c,{}).get("cap") or "")
    return " ".join(x for x in p if x).lower()
B={c:blob(c) for c in T}

# ---------- Q3 concrete tasks/processes ----------
TASKS=[
 ("content / video / posts", r"\b(content|reels?|posts?|videos?|captions?|script|thumbnail|carousel|shorts|ugc|ad creative)\b"),
 ("lead gen / outreach / cold email", r"\b(lead[s]?\b|leadgen|lead gen|cold (email|dm|call)|outreach|prospect|scrap(e|ing)|apollo|list of leads|dm(s)? (to|when)|comment.{0,12}dm)"),
 ("customer support / replies / chatbot", r"\b(customer (support|service)|support ticket|chatbot|answer(s|ing)? (customer|question)|faq|whatsapp bot|reply to (customer|dm|message)|inbox)"),
 ("website / landing page / design", r"\b(website|landing page|web ?app|figma|ui design|logo|brand kit|mockup|deploy(ed)? (a|the) site)"),
 ("coding / app building", r"\b(cod(e|ing)|build (an?|the) app|repo|github|debug|refactor|cursor|claude code|vibe cod|deploy)"),
 ("research / analysis / reports", r"\b(research|competitor analysis|market research|report(s|ing)?\b|analy(se|ze|sis) (the )?data|summar(y|ise|ize)|deep research)"),
 ("meeting notes / transcription", r"\b(meeting (notes|summary|recording)|transcri(be|pt|ption)|note ?taker|zoom call|otter)"),
 ("email / inbox management", r"\b(email(s)? (inbox|triage|reply|draft)|gmail|inbox zero|sort(ing)? (my |your )?email)"),
 ("hiring / recruiting / HR", r"\b(hir(e|ing)|recruit(er|ing|ment)|resume|cv\b|candidate|job (post|description)|interview (candidate|process)|onboard(ing)? (new )?(hire|employee))"),
 ("invoices / bookkeeping / finance", r"\b(invoice|bookkeep|accounting|receipt|expense(s)? (report|track)|payroll|quickbooks|reconcil|tax(es)?\b|financial (model|report))"),
 ("proposals / quotes / contracts", r"\b(proposal|quote(s)? (for|to) client|contract|sow\b|statement of work|pitch deck|onboarding doc)"),
 ("data entry / spreadsheets / CRM", r"\b(data entry|spreadsheet|google sheet|excel|crm\b|hubspot|airtable|notion database|copy.{0,10}paste (data|into))"),
 ("scheduling / calendar / booking", r"\b(calendar|schedul(e|ing)|book(ing)? (a|an|call|appointment)|calendly|appointment)"),
 ("sales calls / follow-up", r"\b(sales call|follow.?up|close (the )?deal|pipeline|discovery call|objection handling)"),
 ("social DMs / community", r"\b(dm automation|manychat|instagram dm|comment (to|for) dm|community manag)"),
 ("SEO / ads", r"\b(seo\b|keyword research|google ads|meta ads|facebook ads|ad (copy|campaign)|ppc)"),
 ("voice agents / phone", r"\b(voice agent|phone (call|agent)|receptionist|vapi|retell|answers the phone|cold call(ing)? agent)"),
 ("translation / subtitles", r"\b(translat(e|ion)|subtitle|dub(bing|bed)|caption(s)? in \w+ language)"),
]
print("=== Q3 CONCRETE TASKS / PROCESSES (n=274 transcripts; beats+captions+semantics) ===")
print(f"{'task':40s} {'n':>4s} {'share':>8s} {'save':>8s} {'lift':>8s}  top tools")
tc={}
for name,rx in TASKS:
    codes=[c for c in T if re.search(rx,B[c])]; tc[name]=codes
    tools=collections.Counter()
    for c in codes:
        for t in T[c].get("semantics",{}).get("tools_mentioned",[]) or []:
            tools[str(t).strip()]+=1
    tt=", ".join(f"{k}({v})" for k,v in tools.most_common(6))
    print(f"{name:40s} {len(codes):4d} {str(med(codes,'share_rate')):>8s} {str(med(codes,'save_rate')):>8s} {str(med(codes,'view_lift')):>8s}  {tt}")

print("\n=== tools_mentioned overall (274) ===")
alltools=collections.Counter()
for c in T:
    for t in T[c].get("semantics",{}).get("tools_mentioned",[]) or []: alltools[str(t).strip()]+=1
print("distinct tools:",len(alltools),"| total mentions:",sum(alltools.values()))
for k,v in alltools.most_common(30): print(f"  {k:32s} {v}")
n_no=sum(1 for c in T if not (T[c].get('semantics',{}).get('tools_mentioned') or []))
print("reels naming zero tools:", n_no)

# ---------- Q4 cost ----------
print("\n=== Q4 COST / PRICING TALK ===")
COST={
 "any money talk": r"\$\d|\bprice|pricing|\bcost|subscription|per month|/mo\b|\bfree\b|token(s)?\b|credits|\bpaid\b|billing|expensive|cheap",
 "explicit $ amount": r"\$\s?\d",
 "'free' / free tier / no cost": r"\bfree\b|free tier|no cost|zero cost|without paying|for free",
 "subscription / per-month": r"subscription|per month|/mo\b|monthly (plan|fee|cost)|\$\d+\s?(a|per) month|20 dollars a month",
 "tokens / credits / API bill": r"\btokens?\b|credits|api (bill|cost|pricing)|per (million|1m) tokens|context window cost",
 "replacing paid staff/tools (cost saving)": r"instead of (hiring|paying)|fire (your|the)|replace(s|d)? (a|an|your) (\$|agency|employee|va\b|assistant)|save(s|d)? (you )?\$|cheaper than",
}
for name,rx in COST.items():
    codes=[c for c in T if re.search(rx,B[c])]
    print(f"  {name:42s} {len(codes):4d}  share={med(codes,'share_rate')} save={med(codes,'save_rate')} lift={med(codes,'view_lift')}")
# numbers_used with $
nums=collections.Counter()
for c in T:
    for n in T[c].get("semantics",{}).get("numbers_used",[]) or []:
        s=str(n)
        if re.search(r"\$|dollar|per month|/mo|free|token|credit|price|cost", s, re.I): nums[s.strip()[:90]]+=1
print("  money-ish entries in numbers_used:", sum(nums.values()), "across", len(set(nums)), "distinct")
for k,v in nums.most_common(35): print("   *", k, f"({v})" if v>1 else "")
