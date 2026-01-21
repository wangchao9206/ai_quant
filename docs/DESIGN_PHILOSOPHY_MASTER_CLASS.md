# AI Quant Pro: The Master's Design Philosophy
**Version**: 1.0  
**Date**: 2026-01-21  
**Author**: AI Quant Design Lead

## 1. Design Philosophy Deconstruction (设计哲学拆解)

Based on the strategic vision of "Democratizing Alpha", our design philosophy centers on **"Augmented Intelligence, Immersive Clarity" (增强智能，沉浸式清晰)**.

### 1.1 Core Pillars
1.  **AI as a Partner, Not a Tool (AI 即伙伴)**
    *   *Concept*: AI shouldn't just execute commands; it should guide, warn, and educate. It is the "Strategy Doctor" and "Risk Sentinel".
    *   *Design Implication*: AI interfaces (chat, diagnostics) should be persistent, context-aware, and conversational, not hidden in sub-menus.
2.  **Data Storytelling (数据叙事)**
    *   *Concept*: Quantitative data is overwhelming. Our job is to turn rows of numbers into a narrative about risk and reward.
    *   *Design Implication*: Use metaphors (Radars, Heatmaps, Gene Maps) over tables. Prioritize "Why" (Attribution) over "What" (Raw Stats).
3.  **Immersive Flow (沉浸心流)**
    *   *Concept*: Strategy creation is a creative process. Users should enter a "flow state" where tools disappear.
    *   *Design Implication*: Minimize page jumps. Use HUD (Heads-Up Display) layouts. Dark mode by default to reduce eye strain and focus attention on data.
4.  **Trust through Transparency (透明建立信任)**
    *   *Concept*: Black boxes are scary in finance.
    *   *Design Implication*: Explainability is key. "Why did the AI suggest this?" must always be answerable via UI tooltips or dedicated diagnostic panels.

## 2. Design Decision Tree (设计决策树)

When making design choices, follow this logic:

*   **Q1: Does this feature reduce cognitive load?**
    *   *Yes*: Proceed.
    *   *No*: Can AI automate it?
        *   *Yes*: Automate it and show a summary.
        *   *No*: Hide it under "Advanced Settings".

*   **Q2: Is the data actionable?**
    *   *Yes*: Highlight it (Neon color, large font).
    *   *No*: Move to secondary view or remove.

*   **Q3: Does the interaction feel "financial" or "tech"?**
    *   *Goal*: Balance. Too "Financial" = Boring/Complex. Too "Tech" = Unreliable/Gimmicky.
    *   *Verdict*: Use "Sci-Fi Finance" aesthetic (Bloomberg Terminal meets Cyberpunk). Professional but futuristic.

## 3. Design Principles Checklist (设计原则检查表)

- [ ] **AI First**: Is the primary interaction driven by or supported by AI?
- [ ] **Glanceability**: Can the user understand the system status (P&L, Risk) in < 1 second?
- [ ] **Contextual Depth**: Is detailed data available on demand (hover/click) without cluttering the default view?
- [ ] **Feedback Loop**: Does every user action have an immediate visual reaction (micro-interaction)?
- [ ] **Accessibility**: Are colors distinct enough for color-blind users (especially Red/Green for trading)? *Note: Use Orange/Blue or shape indicators as backup.*
- [ ] **Consistency**: Do all "Risk" elements share the same visual language (e.g., Warning Yellow)?

## 4. Visual Language DNA (视觉语言 DNA)

*   **Theme**: "Deep Space & Neon" (深空与霓虹)
*   **Background**: `#000000` (True Black) & `#141414` (Dark Grey) - Creates depth.
*   **Primary Accent**: `#2979FF` (Electric Blue) - Intelligence, Tech.
*   **Secondary Accent**: `#00E676` (Neon Green) - Profit, Safety.
*   **Warning/Error**: `#FF1744` (Neon Red) - Loss, Danger.
*   **Typography**: Monospaced numbers (JetBrains Mono/Roboto Mono) for data; Sans-serif (Inter/SF Pro) for UI.
*   **Texture**: Glassmorphism (Frosted Glass) for floating panels to maintain context.

## 5. Interaction Model (用户心智模型)

*   **The Cockpit Metaphor**: The user is the pilot; the app is the F-35 cockpit.
    *   *Center*: Heads-Up Display (Charts, Real-time Action).
    *   *Left*: Comms/Co-pilot (AI Chat/Log).
    *   *Right*: Systems Status (Parameters, Watchlist).
    *   *Bottom*: Instruments (Risk Radar, Performance Metrics).
