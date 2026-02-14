import streamlit as st
import asyncio
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# --- 1. STATE MANAGEMENT ---
if 'ui_state' not in st.session_state:
    st.session_state.ui_state = {
        "summary": "No analysis performed yet.",
        "logs": [],
        "anchors": {"second": "?", "penultimate": "?"}
    }

def add_log(msg: str):
    st.session_state.ui_state["logs"].append(msg)

# --- 2. SCHEMAS & MODELS ---
class ConfirmationVerdict(BaseModel):
    approved: bool = Field(description="True if the logic is sound")
    reason: str = Field(description="Explanation of the verdict")

# Connect to local llama-server
provider = OpenAIProvider(base_url='http://localhost:8080/v1')
model = OpenAIChatModel(model_name='llama3', provider=provider)

# --- 3. AGENTS ---
# Main Agent (The Orchestrator)
orchestrator = Agent(model, deps_type=str)

# Confirmation Agent (Transient Specialist)
confirm_agent = Agent(model, output_type=ConfirmationVerdict)

# --- 4. TOOLS ---
@orchestrator.tool
def get_anchor_letters(ctx: RunContext[str]) -> dict:
    """Extracts 2nd and 2nd-to-last letters."""
    text = ctx.deps
    res = {"second": text[1], "penultimate": text[-2]}
    st.session_state.ui_state["anchors"] = res
    return res

@orchestrator.tool
async def verify_logic(ctx: RunContext[str], proposal: str) -> str:
    """Summons a Confirmation Agent to double-check the Orchestrator's plan."""
    add_log(f"Summoning Confirmation Agent for: {proposal}")

    # This agent runs and then 'unspawns' when the function returns
    verdict = await confirm_agent.run(f"Verify this proposal: {proposal}")

    status = "APPROVED" if verdict.output.approved else "REJECTED"
    add_log(f"Verdict: {status} - {verdict.output.reason}")

    # Update global summary state
    st.session_state.ui_state["summary"] = f"Last Check: {status}. {verdict.output.reason}"
    return status

# --- 5. UI LAYOUT ---
st.set_page_config(page_title="Company Doc AI", layout="wide")
st.title("Agentic Document Editor")

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_file = st.file_uploader("Upload Document", type=['txt', 'xlsx'])
    if uploaded_file:
        content = uploaded_file.getvalue().decode("utf-8")

        if st.button("Start Multi-Agent Analysis"):
            with st.spinner("Agents are thinking..."):
                add_log("Starting Orchestrator...")
                # Run the async logic
                asyncio.run(orchestrator.run(
                    "Identify the anchor letters and verify if they form a valid pattern.",
                    deps=content
                ))
            st.success("Analysis Complete")

    st.subheader("Document Summary")
    st.info(st.session_state.ui_state["summary"])

with col2:
    st.subheader("Agent Activity Log")
    for log in reversed(st.session_state.ui_state["logs"]):
        st.caption(log)

    st.subheader("Extracted Anchors")
    st.json(st.session_state.ui_state["anchors"])
