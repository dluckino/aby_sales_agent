# Security Review

Security Review Findings
No vulnerabilities found. A full-codebase audit was performed across main.py, database.py, emailer.py, shopify_client.py, knowledge.py, ingest.py, run_evals.py, judge.py, widget/widget.js, widget/test_page.html, and requirements.txt.

Areas reviewed and confirmed safe:

SQL injection — database.py uses parameterized ? placeholders exclusively
GraphQL injection — shopify_client.py passes search text via GraphQL variables, not string concatenation
XSS — widget.js renders all messages via textContent, never innerHTML
Command injection / RCE / deserialization — no subprocess, os.system, eval, exec, pickle, or YAML parsing anywhere in scope
XXE — ingest.py uses BeautifulSoup's html.parser, not an XML parser
Hardcoded secrets — all credentials load from environment via dotenv; only .env.example with placeholders is tracked
Email header injection — emailer.py sends via Resend's JSON REST API with a hardcoded destination inbox
Path traversal — /widget static files served via Starlette's StaticFiles, which has built-in traversal protection
One candidate (client-supplied session_id used as the chat-history lookup key with no server-issued binding, main.py:170-197 / database.py:45-50) was identified and independently filtered out: the ID is a crypto.randomUUID() (122 bits of entropy, unguessable per review precedent), is never placed in a URL/query string or logged server-side, and the exploit scenario required an unspecified external leakage channel not present in this codebase — making it theoretical hardening advice rather than a concrete, exploitable flaw.

## Verification
Method: scanner output treated as a judge column, not ground truth. Each report
claim was tested against the working tree with predictions registered before
running the check. Scan environment: `.env` and `chat.db` (plus any sidecar
files) were relocated outside the workspace for the scan's duration, with
absence verified beforehand — the review provably had no access to secrets or
customer data. Scope: the first `/security-review` invocation analyzed only the
pending diff (a README skeleton) and was rejected as vacuous; full-repository
scope was forced by explicit instruction, and its genuineness is evidenced by
line-number citations the reviewer produced unprompted (Check 1), confirmed on
disk. All outputs below are terminal transcripts, verbatim; a rendering
artifact in two of them is adjudicated in Check 6.

### Check 1 — cited-line ground truth (fabrication detector)
The report cited `main.py:170-197` and `database.py:45-50` for its one filtered
candidate. Prediction: those ranges contain the session_id request model, the
/chat endpoint, and the history lookup. Anything unrelated = invented specifics.

```
$ sed -n '170,197p' main.py
class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=64)
def format_hits(hits):
    if not hits:
        return "No matching products found."
    return "\n\n---\n\n".join(hit["text"] for hit in hits)
def format_products(products):
    if not products:
        return "No matching products found in the live catalog."
    lines = []
    for p in products:
        lo = p["priceRangeV2"]["minVariantPrice"]["amount"]
        hi = p["priceRangeV2"]["maxVariantPrice"]["amount"]
        price = f"${lo}" if lo == hi else f"${lo} - ${hi}"
        lines.append(f"{p['title']} ({p['vendor']}) - {price}")
        variants = p["variants"]["nodes"]
        if len(variants) > 1:
            for v in variants:
                lines.append(f"  - {v['title']}: ${v['price']}")
    return "\n".join(lines)
@app.post("/chat")
async def chat(req: ChatRequest):
    save_message(req.session_id, "user", req.message)
    messages = get_history(req.session_id)

$ sed -n '45,50p' database.py
def get_history(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BYid",
            (session_id,)
        ).fetchall()
```

**PASS.** Cited ranges contain exactly the described code. The reviewer read
the files; line citations are real, not fabricated.

### Check 2 — SQL confined to the database layer
Prediction: every `execute` call lives in `database.py`.

```
$ grep -n "execute" *.py
database.py:7:        conn.execute("""
database.py:16:        conn.execute("""
database.py:32:        conn.execute(
database.py:39:        conn.execute(
database.py:47:        rows = conn.execute(
```

**PASS.** Five call sites, all in `database.py`, none elsewhere. (This
single-line grep cannot display multi-line SQL bodies; parameterization is
closed by Check 5.)

### Check 3 — XSS claim
Predictions: zero `innerHTML` in the widget; nonzero `textContent` count.

```
$ grep -n "innerHTML" widget/widget.js
(no output)

$ grep -c "textContent" widget/widget.js
8
```

**PASS.** No `innerHTML` anywhere; 8 `textContent` render sites.

### Check 4 — hardcoded-secrets claim
Prediction: no output — key prefixes exist only in the (relocated) `.env`.

```
$ grep -rn "shpat_\|sk-ant" *.py
(no output)
```

**PASS.** Empty output is the success condition. Run while `.env` was outside
the workspace: the tree contained zero key material at scan time.

### Check 5 — parameterization closer
Prediction: the INSERTs at lines 32/39 use `?` placeholders with paired value
tuples; lines 7/16 are `CREATE TABLE` statements (no user input).

```
$ grep -n -A2 "execute" database.py
7:        conn.execute("""
8-            CREATE TABLE IF NOT EXISTS messages(
9-                id INTEGER PRIMARY KEY AUTOINCREMENT,
--
16:        conn.execute("""
17-            CREATE TABLE IF NOT EXISTS leads(
18-                id INTEGER PRIMARY KEY AUTOINCREMENT,
--
32:        conn.execute(
33-            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
34-            (session_id, role, content)
--
39:        conn.execute(
40-            "INSERT INTO leads (session_id, email, question, name, phone, product_interest) VALUES (?, ?, ?, ?, ?, ?)",
41-            (session_id, email, question, name, phone, product_interest)
--
47:        rows = conn.execute(
48-            "SELECT role, content FROM messages WHERE session_id = ? ORDERBY id",
49-            (session_id,)
```

**PASS.** All three user-data statements fully parameterized; both remaining
sites are table creation.

### Check 6 — "ORDER BYid" adjudication (transcript artifact, not a bug)
Two transcripts above render the history query's ORDER BY clause with a
missing space ("ORDER BYid" in Check 1, "ORDERBY id" in Check 5). Resolution:

```
$ grep -n "ORDER BY" database.py
48:            "SELECT role, content FROM messages WHERE session_id = ? ORDERBY id",
```

The pattern `"ORDER BY"` requires the space and matches raw file bytes; it
returned a hit on line 48. A file lacking the space cannot produce this match.
The space therefore exists in the source, and the rendering in the same
output line is a terminal copy artifact: the line exceeds the terminal width,
and a space falling at the wrap boundary is dropped on copy — which is also
why the artifact's position shifted between transcripts with differing line
prefixes. Corroborating: a genuine `ORDERBY` would raise
`sqlite3.OperationalError` on every history retrieval, contradicted by
hundreds of successful multi-turn eval runs. The display self-refuted; match
semantics win. **NO BUG.** Transcripts preserved unedited.

### Disposition
All report claims verified against the working tree; the report is accepted
with its stated scope: zero findings above the tool's confidence/filter bar.
Excluded by the tool's design and covered elsewhere: rate limiting and abuse
(Phase 8 gate — also where the filtered session_id candidate's residual risk
lands), dependency CVEs (separate SCA scan planned pre-deploy), and prompt
injection against the assistant itself (out of scope for any code scanner
here; addressed via system-prompt rules and the 32-case evaluation battery).