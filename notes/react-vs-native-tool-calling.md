# ReAct vs Native Tool Calling

> Why slide 12 says *"Native tool calling eliminated ~30% failure rate"* — and how to explain it.
> Grounded in this project: the **Cero** agent ([`backend/agents/agent.py`](../backend/agents/agent.py)) migrated from a ReAct text-parsing agent to `create_tool_calling_agent` (native).

---

## TL;DR

Both are ways to let an LLM **use tools** (call your functions). The difference is *how the model tells your code what it wants*:

- **ReAct** → the model writes its decision as **free text** in a strict format (`Thought / Action / Action Input / Observation`), and **your code parses that text** with string matching to figure out which tool to run.
- **Native tool calling** (a.k.a. *function calling*) → the model emits a **structured object** (JSON: function name + arguments) as a first-class field of the API response. **No parsing** — your code reads the fields directly.

Native won because parsing free text is brittle. In this project it broke ~30% of the time **specifically because Cero reasons in Spanish**, and the ReAct format markers (English-centric) came out inconsistently and broke the regex parser. The JSON of native tool calling is language-independent, so the failures vanished.

---

## 1. The problem both patterns solve

An LLM, by itself, only outputs **text**. It cannot run code, hit a database, or call an API.

To build an *agent* that actually **does** things (e.g. "search the transcripts for what Safia said about racism"), you need a protocol:

1. The model signals *"I want to call `search_transcripts` with these arguments."*
2. **Your code** runs the real function and gets a result.
3. The result goes back to the model, which continues or answers.

ReAct and native tool calling are two different implementations of **step 1** — how the model expresses that intent.

---

## 2. ReAct — "Reason + Act" (the 2022 prompting pattern)

ReAct comes from the paper *ReAct: Synergizing Reasoning and Acting in Language Models* (Yao et al., 2022 → ICLR 2023). The idea: prompt the model to **interleave reasoning and actions** in a loop.

The model is instructed to output a strict **text** format:

```
Thought: The user asks what Safia said about racism. I should search the transcripts.
Action: search_transcripts
Action Input: Safia El Aaddam racism
Observation: [chunks returned by the tool...]
Thought: I now have enough to answer.
Final Answer: Safia argues that...
```

Then **your framework parses that text** — it looks for the literal strings `Action:` and `Action Input:` (usually with regex) to extract the tool name and arguments, runs the tool, injects the `Observation:`, and loops.

**The catch:** the contract is *prose*. Nothing guarantees the model writes exactly `Action:` every time. If it writes `Acción:`, or adds a stray line, or merges the thought and action, the parser fails — and the whole turn fails.

---

## 3. Native Tool Calling — "function calling" (the model-native way)

Instead of asking the model to *describe* its action in text, the **provider fine-tunes the model** to emit a **structured tool call** as a dedicated part of the response. You pass tool *declarations* (name + JSON schema of arguments); the model returns something like:

```json
{
  "tool_calls": [
    {
      "name": "search_transcripts",
      "args": { "query": "Safia El Aaddam racism", "top_k": 3 },
      "id": "call_abc123"
    }
  ]
}
```

Your code reads `name` and `args` **directly** — no string parsing, no regex, no ambiguity. The API guarantees the shape. You run the tool, return the result with the same `id`, and the model continues.

This pattern was introduced by **OpenAI in June 2023** and is now standard across **Gemini, Claude, Mistral**, etc. Newer additions (OpenAI *Structured Outputs*, Gemini's *thought signatures*) make the arguments even more reliable.

---

## 4. The core difference, side by side

| | **ReAct** (text parsing) | **Native tool calling** (structured) |
|---|---|---|
| How the model expresses a tool call | Free text in a `Thought/Action/...` format | A structured JSON object (name + args) |
| Who interprets it | **Your code** parses the text (regex/string match) | The API hands you the fields directly |
| Reliability | Brittle — breaks on format drift | High — shape is guaranteed by the model |
| Language sensitivity | **High** — markers are English-centric, drift in other languages | Low — JSON schema is language-independent |
| Token cost | Higher (2–5× — the model narrates every step) | Lower (emits the call directly) |
| Visible reasoning trace | Yes (the `Thought:` lines) | Not by default (reasoning is internal) |
| Where it lives | A prompting technique (works on any text model) | A model capability (needs provider support) |

---

## 5. Why native won — and why ReAct hit ~30% failure *here*

General failure modes of ReAct text-parsing (documented in the state-of-the-art comparisons below):

- **Brittle parsing** — any drift from the exact `Action:` format breaks extraction.
- **Redundant calls** — the model re-issues a tool call it already made.
- **Premature stopping** — it declares a final answer on incomplete intermediate results.
- **Token cost** — narrating Thought/Action/Observation every step burns 2–5× the tokens.

**This project's specific reason (the important one for your talk):**

Cero **reasons and answers in Spanish**. The ReAct format markers (`Thought`, `Action`, `Action Input`) are English-token-centric. When the underlying model thinks in Spanish, it produces those markers **inconsistently** — and the regex parser that depends on them failed on roughly **30% of queries**.

Native tool calling sidesteps this entirely: the structured tool call is **the same JSON regardless of the language the model reasons in**. Switching to `create_tool_calling_agent` made that 30% failure mode disappear. *That* is what slide 12 is claiming.

---

## 6. How Cero uses it (in this codebase)

[`backend/agents/agent.py`](../backend/agents/agent.py):

```python
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Gemini 2.5 Flash — a model with native tool calling
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

# Native tool-calling agent (NOT create_react_agent)
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, max_iterations=10, ...)
```

- **3 tools**: `list_videos`, `get_video_info`, `search_transcripts`.
- One project detail worth knowing: Gemini's native tool calling sometimes returns the final answer as a **list of content parts**, so the code has a small `_normalize_output()` helper to flatten it back to a plain string. That quirk is a *symptom* of using the structured native path.

---

## 7. When ReAct still makes sense (don't over-claim "deprecated")

The deck tag says *"ReAct (deprecated)"* — that's a useful shorthand, but be precise if asked:

- **ReAct-as-text-parsing** (your code regex-matches `Action:`) → effectively superseded for production. This is the part that's "deprecated."
- **ReAct-as-a-loop** (reason → act → observe → repeat) → very much alive. Modern "ReAct agents" (e.g. LangGraph's `create_react_agent`) run that *same loop* but **on top of native tool calling** instead of text parsing.

So ReAct still wins when:
- the model has **no native tool calling** (older or local open-source models);
- you want an **explicit, auditable reasoning trace** for debugging;
- you're doing heavy **multi-hop planning** and want the thoughts visible.

The honest one-liner: *"We didn't abandon the ReAct idea — we kept the reason/act loop but swapped brittle text parsing for the model's native structured tool calls."*

---

## 8. Cómo explicarlo en 30 segundos (guion para la presentación)

> **Analogía:** ReAct es como pedirle al modelo que **escriba una carta** explicando qué quiere hacer ("Pienso que debería buscar X, Acción: buscar[X]"), y vos tenés que **leer e interpretar esa carta** para entender qué función ejecutar. Si la letra cambia o está en otro idioma, te equivocás al interpretarla. El *native tool calling* es como darle un **formulario con casilleros** (nombre de la función + argumentos en JSON): el modelo lo completa y tu código **lee los casilleros directo**, sin interpretar nada.
>
> **Y por qué importa en este proyecto:** Cero razona en español. El formato de texto de ReAct está pensado en inglés, así que cuando el modelo pensaba en español los marcadores salían inconsistentes y el parser fallaba ~30% de las veces. El formulario JSON es igual en cualquier idioma → ese 30% de error desapareció.

---

## References (all verified, June 2026)

**The ReAct paper (primary source)**
- [ReAct: Synergizing Reasoning and Acting in Language Models — arXiv:2210.03629](https://arxiv.org/abs/2210.03629) (Yao et al., ICLR 2023)
- [Google Research blog — ReAct](https://research.google/blog/react-synergizing-reasoning-and-acting-in-language-models/)
- [Reference implementation — github.com/ysymyth/ReAct](https://github.com/ysymyth/ReAct)

**Official function / tool calling docs**
- [Gemini API — Function calling](https://ai.google.dev/gemini-api/docs/function-calling) ← *the provider this project uses*
- [OpenAI — Function calling guide](https://platform.openai.com/docs/guides/function-calling) · [announcement, June 2023](https://openai.com/index/function-calling-and-other-api-updates/)
- [Anthropic (Claude) — How tool use works](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works) · [Tool use overview](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview)

**LangChain (the framework in `agent.py`)**
- [LangChain forum — `create_react_agent` vs `create_tool_calling_agent`](https://forum.langchain.com/t/create-react-agent-vs-create-tool-calling-agent/1014)
- [Understanding LangChain Agents: create_react_agent vs create_tool_calling_agent](https://medium.com/@anil.goyal0057/understanding-langchain-agents-create-react-agent-vs-create-tool-calling-agent-e977a9dfe31e)

**State-of-the-art comparisons (ReAct vs function calling)**
- [LeewayHertz — ReAct agents vs function calling agents](https://www.leewayhertz.com/react-agents-vs-function-calling-agents/)
- [Klu.ai — ReAct Agent Model glossary](https://klu.ai/glossary/react-agent-model)
- [Mercity — Comprehensive guide to ReAct prompting and agentic systems](https://www.mercity.ai/blog-post/react-prompting-and-react-based-agentic-systems/)
- [Vibe Engineering: LangChain's Tool-Calling Agent vs. ReAct Agent](https://medium.com/@dzianisv/vibe-engineering-langchains-tool-calling-agent-vs-react-agent-and-modern-llm-agent-architectures-bdd480347692)
- [AI Function Calling Guide: OpenAI, Anthropic, Google](https://www.digitalapplied.com/blog/ai-function-calling-guide-openai-anthropic-google)
