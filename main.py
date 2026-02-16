import logfire
import streamlit as st
import asyncio
from dataclasses import dataclass, field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

logfire.configure()
logfire.instrument_pydantic_ai()

# --- 1. STATE MANAGEMENT ---
if "ui_state" not in st.session_state:
    st.session_state.ui_state = {
        "phase": "idle",
        "logs": [],
        "anchors": {"second": "?", "penultimate": "?"},
        "comparisons": {"5th_vs_2nd": "?", "10th_vs_penultimate": "?"},
        "guessed_so_far": "",
        "total_guesses": 0,
        "correct_guesses": 0,
        "reconstructed": "",
    }


def add_log(msg: str):
    st.session_state.ui_state["logs"].append(msg)


# --- 2. GAME STATE & MODEL ---
@dataclass
class GameState:
    text: str
    current_pos: int = 0
    anchor_2nd: str = ""
    anchor_penultimate: str = ""
    cmp_5th_vs_2nd: str = ""
    cmp_10th_vs_penultimate: str = ""
    guessed_so_far: list = field(default_factory=list)
    wrong_guesses: list = field(default_factory=list)
    total_guesses: int = 0


provider = OpenAIProvider(base_url="http://localhost:8095/v1")
model = OpenAIChatModel(model_name="llama3", provider=provider)


# --- 3. PHASE 1: DETERMINISTIC AGENTS ---
def anchor_agent(text: str) -> dict:
    result = {"second": text[1] if len(text) > 1 else "?",
              "penultimate": text[-2] if len(text) > 1 else "?"}
    st.session_state.ui_state["anchors"] = result
    add_log(f"Anchor Agent: 2nd='{result['second']}', penultimate='{result['penultimate']}'")
    return result


def compare_agent_a(text: str, anchor_2nd: str) -> str:
    if len(text) < 5:
        return "N/A"
    fifth = text[4]
    result = "same" if fifth == anchor_2nd else "different"
    add_log(f"Compare Agent A: 5th letter '{fifth}' is {result} as 2nd '{anchor_2nd}'")
    return result


def compare_agent_b(text: str, anchor_penultimate: str) -> str:
    if len(text) < 10:
        return "N/A"
    tenth = text[9]
    result = "same" if tenth == anchor_penultimate else "different"
    add_log(f"Compare Agent B: 10th letter '{tenth}' is {result} as penultimate '{anchor_penultimate}'")
    return result


def retrieval_agent(text: str, position: int) -> str:
    return text[position]


# --- 4. GUESSER AGENT (LLM) ---
guesser_agent = Agent(
    model,
    output_type=str,
    deps_type=GameState,
    system_prompt=(
        "You are a text completion assistant. "
        "You will see a partially revealed text with _ for missing letters. "
        "Your job is to figure out what the missing letter is based on the surrounding words and context. "
        "Reply with ONLY a single character. Nothing else."
    ),
    retries=2,
)


@guesser_agent.instructions
def build_game_context(ctx: RunContext[GameState]) -> str:
    gs = ctx.deps
    # Show text with current position marked as ? and future as _
    chars = list(gs.guessed_so_far)
    remaining = len(gs.text) - len(chars)
    if remaining > 0:
        chars.append("?")  # current position
        chars.extend(["_"] * (remaining - 1))
    display = "".join(chars)

    lines = [
        f"Complete this text: {display}",
        f"The ? at position {gs.current_pos + 1} is the letter you must fill in.",
        f"Look at the surrounding words and figure out what letter belongs there.",
    ]
    if gs.wrong_guesses:
        lines.append(f"It is NOT any of these: {', '.join(gs.wrong_guesses)}")
    return "\n".join(lines)


# --- 5. GAME LOOP ---
MAX_WRONG = 5


async def run_game(text: str, progress_bar, status_text):
    st.session_state.ui_state["phase"] = "phase1"
    add_log("--- Phase 1: Analyzing text structure ---")

    anchors = anchor_agent(text)
    cmp_a = compare_agent_a(text, anchors["second"])
    cmp_b = compare_agent_b(text, anchors["penultimate"])
    st.session_state.ui_state["comparisons"] = {
        "5th_vs_2nd": cmp_a, "10th_vs_penultimate": cmp_b
    }

    st.session_state.ui_state["phase"] = "phase2"
    add_log("--- Phase 2: Letter guessing ---")

    gs = GameState(
        text=text,
        anchor_2nd=anchors["second"],
        anchor_penultimate=anchors["penultimate"],
        cmp_5th_vs_2nd=cmp_a,
        cmp_10th_vs_penultimate=cmp_b,
    )

    correct_count = 0

    for pos in range(len(text)):
        gs.current_pos = pos
        gs.wrong_guesses = []

        while True:
            gs.total_guesses += 1
            result = await guesser_agent.run("What letter replaces the ?", deps=gs)
            guessed = result.output.strip()
            guessed = guessed[0] if guessed else "?"

            actual = retrieval_agent(text, pos)

            if guessed == actual:
                gs.guessed_so_far.append(actual)
                correct_count += 1
                add_log(f"Pos {pos + 1}: '{guessed}' CORRECT")
                break
            else:
                gs.wrong_guesses.append(guessed)
                add_log(f"Pos {pos + 1}: '{guessed}' WRONG (actual='{actual}')")
                if len(gs.wrong_guesses) >= MAX_WRONG:
                    gs.guessed_so_far.append(actual)
                    add_log(f"Pos {pos + 1}: Revealed '{actual}'")
                    break

        pct = (pos + 1) / len(text)
        progress_bar.progress(pct, text=f"Position {pos + 1} of {len(text)}")
        display = "".join(gs.guessed_so_far) + "_" * (len(text) - len(gs.guessed_so_far))
        status_text.code(display)

    reconstructed = "".join(gs.guessed_so_far)
    st.session_state.ui_state["phase"] = "done"
    st.session_state.ui_state["reconstructed"] = reconstructed
    st.session_state.ui_state["total_guesses"] = gs.total_guesses
    st.session_state.ui_state["correct_guesses"] = correct_count
    add_log(f"DONE! Reconstructed: '{reconstructed}'")
    return reconstructed


# --- 6. UI ---
st.set_page_config(page_title="Letter Guessing Game", layout="wide")
st.title("Multi-Agent Letter Guessing Game")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader("Upload a text file", type=["txt"])

    if uploaded_file:
        raw = uploaded_file.getvalue()
        for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
            try:
                content = raw.decode(enc).strip()
                break
            except (UnicodeDecodeError, LookupError):
                continue

        st.text(f"Loaded: {len(content)} characters")

        if st.button("Start Game"):
            progress_bar = st.progress(0, text="Starting...")
            status_text = st.empty()

            with st.spinner("Agents are playing..."):
                asyncio.run(run_game(content, progress_bar, status_text))

            st.success("Game Complete!")

    ui = st.session_state.ui_state
    if ui["phase"] == "done":
        st.subheader("Reconstructed Text")
        st.code(ui["reconstructed"])
        c1, c2 = st.columns(2)
        c1.metric("Total Guesses", ui["total_guesses"])
        c2.metric("Correct First Try", ui["correct_guesses"])

    st.subheader("Phase 1 Analysis")
    st.json(ui["anchors"])
    st.json(ui["comparisons"])

with col2:
    st.subheader("Agent Activity Log")
    for log in reversed(st.session_state.ui_state["logs"][-50:]):
        st.caption(log)
