# 📜 Antigravity Permanent Engineering & Documentation Directives

## 🌟 Core Mandate: Documentation Integrity & Living Architecture Guides

For every project and feature implemented, the assistant **MUST** adhere to the following documentation and engineering rules:

---

### 1. Mandatory & Proactive Documentation Updates
- Primary guides (e.g. `BUILD_YOUR_OWN_AGENTIC_AI.md`, `EXTENDABLE_DESIGN_DOCUMENT.md`, `README.md`, `laymans_guide.md`) are **critical living artifacts**.
- Whenever a feature, tool, skill, endpoint, UI view, or architectural subsystem is modified, added, or refactored, the documentation **MUST be updated immediately** in the same session without needing to be asked.

---

### 2. The 5 Pillars of Every Feature Explanation
Every new capability or architectural component documented **MUST** be explained using the following structured approach:

1. **What It Does (Plain English & Analogy)**:
   - Provide an intuitive, plain-English summary.
   - Always include a memorable, relatable real-world analogy (e.g., *"The Lego Builder for Workflows"*, *"The Airport Security Scanner"*, *"The Universal TV Remote Control"*).

2. **Why & How It Helps (Value Proposition)**:
   - Clearly explain the specific engineering or business problem it solves.
   - Include a comparison table: **"The Challenge Before" vs. "How This Solves It"**.

3. **Real-World Simple Step-by-Step Scenario**:
   - Provide a concrete, relatable scenario with numbered step-by-step actions and expected outputs (e.g., customer refund ticket, split bill calculation, server migration).

4. **Witty, Engaging & Humorous Commentary**:
   - Include lighthearted, relatable funny comments and observations (e.g., *"The author once tried following a tutorial that said 'just run make install' without explaining the Makefile... this is the anti-tutorial."*).
   - Keep technical explanations engaging, accessible, and fun to read for both engineers and non-technical stakeholders.

5. **Visual Flows & Under-the-Hood Code**:
   - Include clear Mermaid architecture flows (`flowchart LR`, `sequenceDiagram`).
   - Provide clean, tested code snippets with active file paths and API route signatures.

---

### 3. Production Portability & Zero-Dependency Graceful Fallbacks
- Always ensure new features include graceful offline/local fallbacks (e.g. SQLite keyword search fallback for vector stores, mock client fallback for network APIs).
- Maintain test coverage for every newly added tool or endpoint.
