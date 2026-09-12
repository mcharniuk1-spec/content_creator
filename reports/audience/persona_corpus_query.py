import sqlite3, json, glob, re, statistics as st, os, collections
R="/Users/mihailampleev/Desktop/M2 Lab/m2-research/radar"
con=sqlite3.connect(os.path.join(R,"data/radar.db")); con.row_factory=sqlite3.Row
T={}
for f in sorted(glob.glob(os.path.join(R,"data/analysis/transcripts/*.json"))):
    d=json.load(open(f)); T[d["code"]]=d
print("transcripts loaded:", len(T))

# metrics
VF={r["code"]:dict(r) for r in con.execute("select * from video_features")}
CAP={}
for r in con.execute("select code, cap, play, resh, save, comm, dur, username from reels group by code"):
    CAP[r["code"]]=dict(r)
print("vf rows:", len(VF), "| reel codes:", len(CAP))
print("transcripts with vf:", sum(1 for c in T if c in VF), "| with play>=100:", sum(1 for c in T if c in VF and (VF[c]['play'] or 0)>=100))

def med(codes, field):
    v=[VF[c][field] for c in codes if c in VF and VF[c].get(field) is not None and (VF[c]['play'] or 0)>=100]
    return (round(st.median(v),5), len(v)) if v else (None,0)

def txtblob(c):
    d=T[c]; s=d.get("semantics",{}); i=d.get("interpretation",{})
    parts=[s.get("audience",""),s.get("audience_stage",""),i.get("audience_tension",""),
           s.get("hook_text",""),s.get("subtopic",""),s.get("thesis",""),s.get("problem","")]
    parts+= [b.get("text","") for b in d.get("beats",[])]
    parts.append((CAP.get(c,{}).get("cap") or ""))
    return " \n ".join(x for x in parts if x)
BLOB={c:txtblob(c).lower() for c in T}
AUD={c:" ".join(x for x in [T[c].get("semantics",{}).get("audience",""),
      T[c].get("semantics",{}).get("audience_stage",""),
      T[c].get("interpretation",{}).get("audience_tension","")] if x).lower() for c in T}

# ---------- Q1 audience labels ----------
AL=[
 ("founder/startup",      r"\bfounder|co-?founder|startup|solopreneur|entrepreneur|indie hacker"),
 ("business owner/SMB",   r"business owner|small business|smb|store owner|shop owner|local business|restaurant|salon|owner-operator|\bowner\b"),
 ("agency/consultant",    r"\bagency|agencies|consultant|freelanc|client work|service provider|coach\b"),
 ("marketer",             r"\bmarketer|marketing team|performance marketer|growth marketer|ad buyer|paid social"),
 ("creator/content",      r"\bcreator|content creator|influencer|youtuber|podcaster|editor\b|videographer"),
 ("developer/engineer",   r"\bdevelop|engineer|programmer|coder|vibe coder|software\b|\bdevs?\b"),
 ("beginner/learner",     r"beginner|newcomer|new to ai|never used|non-?technical|no-?code|student|self-?taught|learner|just starting"),
 ("employee/9-to-5",      r"9-?to-?5|employee|corporate|job seeker|professional[s]? (who|in)|manager\b|team lead|ops lead|operations lead|analyst|accountant|recruiter|hr\b|salesperson|sales rep|realtor|real estate agent"),
 ("AI practitioner/builder", r"ai builder|prompt engineer|agent builder|already running agents|power user|practitioner|automation builder|makes? agents"),
 ("ai-curious/news follower", r"follows? ai news|ai-watching|keeping up|ai news|tech-curious|curious about ai|ai enthusiast"),
 ("money/side-hustle seeker", r"make money|side hustle|online income|passive income|get rich|monetiz"),
]
lab=collections.defaultdict(list)
for c in T:
    for name,rx in AL:
        if re.search(rx, AUD[c]): lab[name].append(c)
print("\n=== Q1 AUDIENCE LABELS (n=%d transcripts, semantics.audience+audience_stage+audience_tension) ==="%len(T))
for name,_ in AL:
    m=med(lab[name],'share_rate'); s=med(lab[name],'save_rate'); v=med(lab[name],'view_lift')
    print(f"{name:28s} {len(lab[name]):4d}  share={m[0]} save={s[0]} lift={v[0]} (n_metric={m[1]})")
none=[c for c in T if not any(re.search(rx,AUD[c]) for _,rx in AL)]
print("unclassified:", len(none))

# mutually-exclusive 4 buckets (priority order)
BUCK=[("founder/owner", r"\bfounder|co-?founder|startup|solopreneur|entrepreneur|business owner|small business|smb|\bowner\b|agency owner|agencies|local business|restaurant owner"),
      ("employee/manager", r"9-?to-?5|employee|corporate|manager\b|team lead|ops lead|operations lead|job seeker|analyst|accountant|recruiter|salesperson|sales rep|realtor|real estate agent|marketer|professional"),
      ("developer", r"\bdevelop|engineer|programmer|coder|vibe coder|\bdevs?\b|software engineer"),
      ("learner/beginner", r"beginner|student|self-?taught|new to ai|never used|non-?technical|learner|just starting|no-?code")]
bk=collections.Counter(); bkc=collections.defaultdict(list); multi=0
for c in T:
    hits=[n for n,rx in BUCK if re.search(rx,AUD[c])]
    if len(hits)>1: multi+=1
    if hits: bk[hits[0]]+=1; bkc[hits[0]].append(c)
    else: bk["none of the four"]+=1; bkc["none of the four"].append(c)
print("\n--- four-bucket (priority: founder>employee>dev>learner) ---")
for k,v in bk.most_common(): print(f"  {k:20s} {v}")
print("  (reels matching 2+ buckets:", multi, ")")

# ---------- Q2 question clusters ----------
QC = {
 "(a) what is AI / how does it work": (
   r"how (it|ai|this|the model|llm|agents?) (actually )?works?|what (is|are) (an? )?(ai|llm|agent|token|context window|mcp|rag)\b|under the hood|explain(ed|s|ing)? (like|in) |mental model|why (models|ai|llms) (hallucinat|fail|forget)",
   ["framework_mental_model"]),
 "(b) which tool for a task": (
   r"which (tool|app|model|one) (to|should|do)|best (tool|app|ai|model) for|\bvs\.?\b|compar(e|ison|ing)|switch(ed|ing)? (from|to)|i tested \d|stop using|use this instead|top \d+ (ai )?tools",
   ["tool_recommendation","tool_comparison"]),
 "(c) how to automate process N": (
   r"automat(e|ed|ing|ion)|workflow|\bagent that\b|build (an?|this) (agent|bot|system|automation)|n8n|zapier|make\.com|pipeline|on autopilot|does it for you|without lifting",
   ["workflow_build","automation","step_by_step"]),
 "(d) cost / price / expenses": (
   r"\$\d|\bprice|pricing|cost(s|ing)?\b|subscription|per month|\bfree\b|\bpaid\b|token(s)? (cost|bill|spend)|credits|api bill|cheap(er)?|expensive|budget",
   []),
 "(e1) will AI replace me / my job": (
   r"replace(d|s|ment)? (you|me|your job|jobs|developers|workers)|lose (your|their) job|out of a job|job(s)? (are|is) (gone|dying)|fired|obsolete|no longer need",
   []),
 "(e2) is it safe / can I trust it": (
   r"hallucinat|can'?t trust|trust (it|ai|the model)|accura(te|cy)|security|privacy|data leak|risk(s|y)?\b|reviewed by a human|human in the loop|gets it wrong|mistake",
   []),
 "(e3) how do I start / first step": (
   r"where (to|do (i|you)) start|get(ting)? started|first step|beginner|step (1|one)|start (here|with)|if you'?re new|how to (learn|begin)",
   []),
 "(e4) how to make money with AI": (
   r"make (money|\$)|earn|revenue|\bmrr\b|charge (clients|\$)|get clients|side hustle|sell(ing)? (ai|this)|business idea|monetiz",
   []),
 "(e5) keeping up with what shipped": (
   r"just (dropped|launched|released|shipped)|new(est)? model|announce(d|ment)|this week in ai|openai (just|released)|anthropic (just|released)|google (just|released)|is (finally )?here",
   []),
}
print("\n=== Q2 QUESTION CLUSTERS (n=274; regex over audience+hook+thesis+beats+caption, plus solution_type) ===")
print(f"{'cluster':38s} {'n':>4s} {'med share_rate':>14s} {'med save_rate':>13s} {'med view_lift':>13s} {'n_met':>6s}")
qcc={}
for name,(rx,sts) in QC.items():
    codes=[c for c in T if re.search(rx,BLOB[c]) or (T[c].get("semantics",{}).get("solution_type") in sts)]
    qcc[name]=codes
    s=med(codes,'share_rate'); sv=med(codes,'save_rate'); vl=med(codes,'view_lift')
    print(f"{name:38s} {len(codes):4d} {str(s[0]):>14s} {str(sv[0]):>13s} {str(vl[0]):>13s} {s[1]:6d}")
allc=[c for c in T]
s=med(allc,'share_rate'); sv=med(allc,'save_rate'); vl=med(allc,'view_lift')
print(f"{'BASELINE all 274':38s} {len(allc):4d} {str(s[0]):>14s} {str(sv[0]):>13s} {str(vl[0]):>13s} {s[1]:6d}")
# full-corpus baseline
fc=[c for c in VF if (VF[c]['play'] or 0)>=100]
print("full corpus 3211 baseline (play>=100, n=%d): share=%s save=%s lift=%s"%(len(fc),
   med(fc,'share_rate')[0],med(fc,'save_rate')[0],med(fc,'view_lift')[0]))

print("\n--- pain enum (video_features.pain, n=272) with performance ---")
for r in con.execute("select pain,count(*) n from video_features where pain is not null group by 1 order by n desc"):
    codes=[x[0] for x in con.execute("select code from video_features where pain=?", (r[0],))]
    print(f"  {r[0]:26s} {r[1]:3d}  share={med(codes,'share_rate')[0]} save={med(codes,'save_rate')[0]} lift={med(codes,'view_lift')[0]}")
print("\n--- solution_type ---")
for r in con.execute("select solution_type,count(*) n from video_features where solution_type is not null group by 1 order by n desc"):
    codes=[x[0] for x in con.execute("select code from video_features where solution_type=?", (r[0],))]
    print(f"  {r[0]:26s} {r[1]:3d}  share={med(codes,'share_rate')[0]} save={med(codes,'save_rate')[0]} lift={med(codes,'view_lift')[0]}")
