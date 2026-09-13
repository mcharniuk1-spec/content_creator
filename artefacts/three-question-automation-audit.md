# The three-question automation audit

Open one automation and walk through it end to end, live, right now. If you cannot, it is not in production, it is in purgatory. For each flow, agent or "AI project":

1. **Who owns it?** A named person who is paged when it breaks and who decides when it is retired. No owner: kill it or assign one this week.
2. **What is the success metric?** One number it moves, measured before and after (hours, replies, errors, days-to-invoice). No metric: it is a hobby.
3. **Where does it live inside an existing workflow?** Which step it replaces, where its output lands, who reads that output. Output that lands where nobody looks: dead.

Fourth question we added: **whose data does it read, and is that data anyone's job to keep correct?** A flow pointed at a WhatsApp group or a spreadsheet one person owns is pointed at a liability.

Score each flow 0–3 on the first three. Anything under 3 goes on the kill list with a date.
