import sqlite3, json, glob, re, os, statistics as st
R="/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar"
con=sqlite3.connect(os.path.join(R,"data/radar.db")); con.row_factory=sqlite3.Row
T={}
for f in sorted(glob.glob(os.path.join(R,"data/analysis/transcripts/*.json"))):
    d=json.load(open(f)); T[d["code"]]=d
VF={r["code"]:dict(r) for r in con.execute("select * from video_features")}
CAP={r["code"]:dict(r) for r in con.execute("select code,cap from reels group by code")}
def med(codes,f):
    v=[VF[c][f] for c in codes if VF.get(c,{}).get(f) is not None and (VF[c]['play'] or 0)>=100]
    return round(st.median(v),5) if v else None
def blob(c):
    d=T[c]; s=d.get("semantics",{})
    return " ".join(x for x in [s.get("subtopic",""),s.get("subject",""),s.get("thesis",""),s.get("problem",""),s.get("solution",""),s.get("hook_text",""),d.get("interpretation",{}).get("audience_tension","")]+[b.get("text","") for b in d.get("beats",[])]+[CAP.get(c,{}).get("cap") or ""] if x).lower()
B={c:blob(c) for c in T}
CH={
"permission / boss / policy / 'am I allowed'": r"\ballowed\b|permission|company policy|my boss|your boss|get in trouble|approve[ds]? (it|this)|compliance team|it department|told me to|admit(ting)? (i|you) used",
"AI search traffic / get found in ChatGPT (AEO/GEO)": r"\baeo\b|\bgeo\b|generative engine|get found (in|on) (chatgpt|ai)|ai (search|answers|overview)|rank in chatgpt|cited by chatgpt|traffic from chatgpt",
"human review / keep a human in control": r"human (in the loop|review|oversight|approval)|keep a human|you still (check|review|approve)|don'?t (just )?trust the output|always review|double.?check",
"batch / bulk processing of records": r"\bbatch(es|ing)?\b|in bulk|hundreds of (products|rows|files)|csv|spreadsheet of|at (a )?time",
"presentations / slides / decks": r"powerpoint|\bslides?\b|\bdeck\b|presentation|google slides|pitch deck",
"'my output sounded fake / robotic'": r"sound(s|ed)? (fake|robotic|like ai|generic)|ai slop|\bslop\b|obviously ai|generic output|reads like chatgpt",
"training / upskilling / course": r"\bcourse\b|training|upskill|certificat|curriculum|learn ai|bootcamp",
"team adoption / getting others to use it": r"\bmy team\b|your team|get (your|the) team|team adoption|roll (it )?out to|onboard (the|your) team",
}
print("=== ROUND-2 CROSS-CHECKS (n=274 transcripts; regex over semantics+beats+caption) ===")
print(f"{'probe':52s} {'n':>4s} {'share':>8s} {'save':>8s} {'lift':>8s}")
for k,rx in CH.items():
    codes=[c for c in T if re.search(rx,B[c])]
    print(f"{k:52s} {len(codes):4d} {str(med(codes,'share_rate')):>8s} {str(med(codes,'save_rate')):>8s} {str(med(codes,'view_lift')):>8s}")
print(f"{'BASELINE 274':52s} {274:4d} {med(list(T),'share_rate'):>8} {med(list(T),'save_rate'):>8} {med(list(T),'view_lift'):>8}")

# examples for the interesting ones
for k in ["permission / boss / policy / 'am I allowed'","AI search traffic / get found in ChatGPT (AEO/GEO)","human review / keep a human in control","'my output sounded fake / robotic'"]:
    rx=CH[k]; codes=[c for c in T if re.search(rx,B[c])]
    print(f"\n-- {k}: {len(codes)} codes:", codes[:14])

# meeting notes / support detail
for name,rx in [("meeting notes",r"\b(meeting (notes|summary|recording|minutes)|transcri(be|pt|ption)|note ?taker)"),
                ("customer support",r"\b(customer (support|service)|support ticket|chatbot|faq|whatsapp bot|reply to (customer|dm|message)|inbox)")]:
    codes=[c for c in T if re.search(rx,B[c])]
    print(f"\n{name}: n={len(codes)} share={med(codes,'share_rate')} save={med(codes,'save_rate')} lift={med(codes,'view_lift')} codes={codes[:12]}")
