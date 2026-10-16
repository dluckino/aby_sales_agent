# American Backyard AI Sales Assistant

## 1. Overview


## 2. System Architecture


## 3. The Knowledge Base


## 4. The Evaluation System


## 5. What the Evals Caught
The suite grew from 17 invented cases to 32 cases mined from real customer questions, and the score moved from 14 pass / 1 partial / 2 fail to a 30/32 close — but the number matters less than the four failure families it caught.

### Epistemic hedging
Before the fix, the bot would say that it couldn't find hot tubs among the product in its knowledge base. It would then say that this does not mean that American Backyard doesn't sell hot tubs and that a customer should call the store to clarify, which was incorrect because the bot should be able to know that the store does not sell hot tubs. 
By adding the What we sell and what we don't sell section we could add into the bot's knowledge base that there are no times where American Backyard sells hot tubs. This paired with a change to the System Prompt allowed the bot to start answering correctly when asked about hot tubs.

### Retrieval composition bugs
The bot was looking for specific products in the product knowledge. When asked about a specific manufacturer product that isn't in our product knowledge, the bot would say we didn't sell that product, which was bad because it ignored System Prompts that told it that any product from our listed manufacturers is product that we sell to customers. 
It would get worse in cases such as Lloyd Flanders where you may query the bot asking about Mackinac Catalog products, and the AI would return Grand Traverse in its internal product search, then say that there were no Mackinac products found.
These problems were fixed through the use of 

### Constraint violations
> QUESTION: What did the bot recommend to the customer who said "no mgp or hdpe"? What was misleading about how it justified it?
> QUESTION: One run after the fix, which second brand slipped through, and where was the knowledge that should have stopped it?
> QUESTION: What fixed it (exclusion rule + glossary), and what's the honest status of this case on the closing board?

### Fabrications
> QUESTION: Describe the Ebel answer: which products were real, which were invented, and why did the mix make it convincing?
> QUESTION: How was it caught — what did the judge suspect, and what did your catalog check prove?
> QUESTION: What rule was added, and what grade did you give your own bot?


## 6. What the Instrument Caught About Its Operators
The judge was built to grade the bot. Four times, it graded me instead.

### The rubber-stamp incidents
> QUESTION: What did your grading notes have in common in all four incidents, and how did the judge expose them?
> QUESTION: Why does one false note matter more than one wrong grade? (the worst-note principle)

### The observations-first protocol
> QUESTION: State the rule you now grade by, and show the difference with one before/after note example.

### Rubric rot
> QUESTION: What happened to the hot-tub rubrics when the What-We-Sell section shipped? What's the standing law now (content changes → ?)
> QUESTION: What is a planned-rot case — use photo-reference and its expiration condition as the example.

### The canary saga — the verifier gets verified
> QUESTION: Tell the green-egg grep story: what did the mentor's verification string search for, what did your file actually say, and how many false alarms did it cause?
> QUESTION: State the doctrine that came out of it (quote the world, not the plan).

### The finale: one heuristic, two verdicts
> QUESTION: Describe how the judge's same suspicion flagged Ebel (correctly) and Shademaker (incorrectly), and what only the human could see in each case.
> QUESTION: What does that establish about the division of labor between an automated judge and a human grader?


## 7. Security & Compliance Posture


## 8. Known Limitations


## 9. Roadmap


## 10. Numbers & Receipts
commit 7afc884 — 30/32 human-graded on evals mined from real customer questions, judge agreement 27/32, every disagreement adjudicated in writing, two failures caught and characterized rather than hidden.