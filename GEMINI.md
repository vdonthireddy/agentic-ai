# 📜 Antigravity Engineering & Documentation Directives

## 🌟 Core Directives

### 1. On-Demand Documentation (No Proactive Updates)
- Do **NOT** proactively read, search, or update documentation files on every change.
- Update documentation **ONLY when explicitly requested by the user**.
- This avoids unnecessary token usage and latency during feature implementation and debugging.

---

### 2. The 5 Pillars of Feature Explanation (When Requested by User)
When the user explicitly asks to document a capability or architectural component, use the following structured approach:

1. **What It Does (Plain English & Analogy)**:
   - Provide an intuitive, plain-English summary with a memorable, relatable real-world analogy.

2. **Why & How It Helps (Value Proposition)**:
   - Clearly explain the specific engineering or business problem it solves.
   - Include a comparison table: **"The Challenge Before" vs. "How This Solves It"**.

3. **Real-World Simple Step-by-Step Scenario**:
   - Provide a concrete, relatable scenario with numbered step-by-step actions and expected outputs.

4. **Witty, Engaging & Humorous Commentary**:
   - Keep technical explanations engaging, accessible, and fun to read for both engineers and non-technical stakeholders.

5. **Visual Flows & Under-the-Hood Code**:
   - Include clear Mermaid architecture flows (`flowchart LR`, `sequenceDiagram`).
   - Provide clean, tested code snippets with active file paths and API route signatures.

---

### 3. Production Portability & Zero-Dependency Graceful Fallbacks
- Always ensure new features include graceful offline/local fallbacks (e.g. SQLite keyword search fallback for vector stores, mock client fallback for network APIs).
- Maintain test coverage for every newly added tool or endpoint.
