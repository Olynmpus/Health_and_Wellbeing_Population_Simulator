
import sys
import html
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from dashboard.shared import load_longitudinal, load_population


st.set_page_config(
    page_title="Communication Experiences",
    page_icon="◉",
    layout="wide",
)

# ---------------------------------------------------------
# Page styling
# ---------------------------------------------------------

st.markdown("""
<style>
    .page-intro {
        color: #aab6c8;
        font-size: 1rem;
        margin-bottom: 1.2rem;
    }

    .conversation-context {
        background: #202b3b;
        border: 1px solid #35445a;
        border-radius: 14px;
        padding: 16px 20px;
        margin: 14px 0 22px 0;
    }

    .context-label {
        color: #a9b8cc;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 7px;
    }

    .context-message {
        color: #f1f5f9;
        font-size: 1.05rem;
        line-height: 1.5;
    }

    .chat-row {
        display: flex;
        width: 100%;
        margin: 14px 0;
    }

    .chat-row.person {
        justify-content: flex-end;
    }

    .chat-row.other {
        justify-content: flex-start;
    }

    .chat-bubble {
        max-width: 78%;
        padding: 14px 17px;
        border-radius: 16px;
        line-height: 1.5;
    }

    .chat-bubble.person {
        background: #173b60;
        border: 1px solid #286093;
        border-bottom-right-radius: 4px;
    }

    .chat-bubble.family {
        background: #183e37;
        border: 1px solid #286b58;
        border-bottom-left-radius: 4px;
    }

    .chat-bubble.friend {
        background: #40304f;
        border: 1px solid #70508b;
        border-bottom-left-radius: 4px;
    }

    .chat-bubble.service {
        background: #49391f;
        border: 1px solid #80602c;
        border-bottom-left-radius: 4px;
    }

    .chat-bubble.other {
        background: #303b4b;
        border: 1px solid #4b5b70;
        border-bottom-left-radius: 4px;
    }

    .chat-name {
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 7px;
        color: #d4deeb;
    }

    .chat-text {
        color: #f3f6fa;
        font-size: 0.96rem;
    }

    .chat-detail {
        color: #c3cfdd;
        font-size: 0.87rem;
        margin-top: 10px;
        padding-top: 9px;
        border-top: 1px solid rgba(220,230,245,0.18);
    }

    .chat-tag {
        display: inline-block;
        font-size: 0.7rem;
        font-weight: 700;
        color: #dce6f2;
        background: rgba(255,255,255,0.10);
        padding: 3px 8px;
        border-radius: 20px;
        margin-top: 9px;
    }

    .outcome-label {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 20px;
        background: #303b4b;
        color: #dce6f2;
        font-size: 0.78rem;
        margin-top: 12px;
    }

    .small-note {
        color: #9eacbf;
        font-size: 0.82rem;
        margin-top: 8px;
    }

    div[data-testid="stExpander"] {
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


st.title("Communication experiences")
st.markdown(
    '<div class="page-intro">'
    'Explore how people experience communication across different '
    'everyday situations.'
    '</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Illustrative four-month scenario. These are scripted perspectives, "
    "not recordings or observations of real conversations."
)


# ---------------------------------------------------------
# Load interaction scenario
# ---------------------------------------------------------

enable_llm = st.sidebar.checkbox(
    "Enable local LLM interpretations",
    value=False,
    help="Optional interpretations are model-generated and unverified.",
)

try:
    person, relationships, histories, snapshots = load_longitudinal(enable_llm)
except Exception as error:
    st.error(f"The interaction scenario could not be loaded: {error}")
    st.stop()


# ---------------------------------------------------------
# Build interaction records
# ---------------------------------------------------------

rows = []

for agent_id, agent_events in histories.items():
    for event in agent_events:
        details = event.get("additional_details", {})
        communication = details.get("communication_event", {})
        llm = details.get("llm_interpretation", {})

        perspective_type = details.get("perspective_type", "")

        rows.append({
            "Month": event["month"],
            "Participant": agent_id,
            "Interaction": details.get("interaction_id", ""),
            "Event type": event["event_type"].replace("_", " ").title(),
            "Perspective": perspective_type,
            "Message": event["actual_message"],
            "Observed event": details.get("observed_event"),
            "Participant report": details.get("participant_report"),
            "Interpretation": event["agent_interpretation"],
            "Outcome": event["outcome"].replace("_", " ").title(),
            "Speaker ID": communication.get("speaker_id"),
            "Listener ID": communication.get("listener_id"),
            "Intended message": communication.get("intended_message"),
            "Perceived message": communication.get("perceived_message"),
            "Listener interpretation": communication.get(
                "listener_interpretation"
            ),
            "Channel": communication.get("channel", "Not recorded"),
            "Initial outcome": communication.get(
                "initial_outcome", "not_assessed"
            ),
            "Final outcome": communication.get(
                "final_outcome", "not_assessed"
            ),
            "Clarification requested": communication.get(
                "clarification_requested", False
            ),
            "LLM": llm,
        })

events = pd.DataFrame(rows)

if events.empty:
    st.warning("No interaction records are available.")
    st.stop()


# ---------------------------------------------------------
# Participant labels and colours
# ---------------------------------------------------------

def participant_label(participant_id):
    if not participant_id:
        return "Participant"

    labels = {
        "PERSON": "Person",
        "FAMILY": "Family member",
        "FRIEND": "Friend",
        "SERVICE": "Service representative",
    }

    prefix = participant_id.split("-")[0]
    label = labels.get(prefix, "Participant")

    return f"{label} · {participant_id}"


def participant_style(participant_id):
    if not participant_id:
        return "other"

    prefix = participant_id.split("-")[0]

    styles = {
        "PERSON": "person",
        "FAMILY": "family",
        "FRIEND": "friend",
        "SERVICE": "service",
    }

    return styles.get(prefix, "other")


def display_value(value):
    if value is None or pd.isna(value):
        return None

    value = str(value).strip()

    if not value or value.lower() in ("none", "not_assessed"):
        return None

    return value


# ---------------------------------------------------------
# Interaction selector
# ---------------------------------------------------------

interaction_ids = sorted(
    events["Interaction"].unique(),
    key=lambda interaction_id: int(
        events.loc[
            events["Interaction"] == interaction_id, "Month"
        ].iloc[0]
    ),
)

interaction_labels = {}

for interaction_id in interaction_ids:
    interaction_rows = events[
        events["Interaction"] == interaction_id
    ]
    first = interaction_rows.iloc[0]

    interaction_labels[interaction_id] = (
        f"Month {int(first['Month'])} · {first['Event type']}"
    )

st.subheader("Conversation history")

selected_interaction = st.radio(
    "Choose an interaction",
    interaction_ids,
    format_func=lambda interaction_id: interaction_labels[interaction_id],
    horizontal=True,
    label_visibility="collapsed",
)

selected_events = events[
    events["Interaction"] == selected_interaction
].copy()

first_record = selected_events.iloc[0]

# Put the recipient's perspective first.
selected_events["_order"] = selected_events["Perspective"].map({
    "recipient": 0,
    "other_participant": 1,
}).fillna(2)

selected_events = selected_events.sort_values("_order")


# ---------------------------------------------------------
# Conversation header and scenario context
# ---------------------------------------------------------

st.markdown(
    f"### Month {int(first_record['Month'])} "
    f"· {first_record['Event type']}"
)

speaker_id = first_record["Speaker ID"]
listener_id = first_record["Listener ID"]

st.caption(
    f"Initiating participant: {participant_label(speaker_id)}"
    f"  ·  Listener: {participant_label(listener_id)}"
)

scenario_message = html.escape(str(first_record["Message"]))

st.markdown(
    f"""
    <div class="conversation-context">
        <div class="context-label">Scenario context · What happened</div>
        <div class="context-message">{scenario_message}</div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Chat-style participant perspectives
# ---------------------------------------------------------

st.markdown("#### Participant perspectives")

for _, event in selected_events.iterrows():

    participant_id = event["Participant"]
    style = participant_style(participant_id)
    alignment = "person" if style == "person" else "other"

    name = html.escape(participant_label(participant_id))

    interpretation = display_value(event["Interpretation"])
    observed = display_value(event["Observed event"])
    report = display_value(event["Participant report"])

    # The main bubble represents the participant's recorded perspective.
    main_text = interpretation or "No interpretation has been recorded."
    main_text = html.escape(main_text)

    details_html = ""

    if observed:
        details_html += (
            '<div class="chat-detail"><b>Recorded observation</b><br>'
            + html.escape(observed)
            + '</div>'
        )

    if report:
        details_html += (
            '<div class="chat-detail"><b>Participant report</b><br>'
            + html.escape(report)
            + '</div>'
        )

    perspective_label = (
        "Person's perspective"
        if event["Perspective"] == "recipient"
        else "Other participant's perspective"
    )

    outcome = display_value(event["Outcome"])

    outcome_html = ""
    if outcome and outcome.lower() != "not assigned":
        outcome_html = (
            '<div class="outcome-label">Recorded outcome: '
            + html.escape(outcome)
            + '</div>'
        )

    st.markdown(
        f"""
        <div class="chat-row {alignment}">
            <div class="chat-bubble {style}">
                <div class="chat-name">{name}</div>
                <div class="chat-text">{main_text}</div>
                {details_html}
                <div class="chat-tag">{perspective_label}</div>
                {outcome_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    llm = event["LLM"]

    if isinstance(llm, dict):
        if llm.get("status") == "generated" and llm.get("text"):
            with st.expander(
                f"Optional AI interpretation · {participant_id}"
            ):
                st.write(llm["text"])
                st.caption(
                    f"Model: {llm.get('model')} · "
                    "Unverified; does not change simulation state."
                )


st.caption(
    "The bubbles show recorded participant perspectives and interpretations. "
    "They are not verbatim spoken messages. An interpretation is not "
    "necessarily an independently observed fact."
)


# ---------------------------------------------------------
# Technical details, hidden by default
# ---------------------------------------------------------

with st.expander("Communication mechanics and technical details"):

    mechanics = selected_events.iloc[0]

    col1, col2 = st.columns(2)

    col1.write("**Communication channel**")
    col1.write(str(mechanics["Channel"]).title())

    col2.write("**Clarification requested**")
    col2.write(
        "Yes" if mechanics["Clarification requested"] else "No"
    )

    st.write("**Intended message**")
    st.write(
        display_value(mechanics["Intended message"])
        or "Not recorded"
    )

    st.write("**Perceived message**")
    st.write(
        display_value(mechanics["Perceived message"])
        or "Not recorded"
    )

    st.write("**Listener interpretation**")
    st.write(
        display_value(mechanics["Listener interpretation"])
        or "Not recorded"
    )

    st.write("**Initial outcome**")
    st.write(str(mechanics["Initial outcome"]).replace("_", " ").title())

    st.write("**Final outcome**")
    st.write(str(mechanics["Final outcome"]).replace("_", " ").title())

    st.caption(
        "Initial and final communication outcomes are not currently "
        "assessed in this scenario. Do not infer successful repair, "
        "breakdown or recovery."
    )


# ---------------------------------------------------------
# Compact scenario navigation
# ---------------------------------------------------------

with st.expander("All four months at a glance"):

    for interaction_id in interaction_ids:
        interaction_rows = events[
            events["Interaction"] == interaction_id
        ]

        first = interaction_rows.iloc[0]

        st.markdown(
            f"**Month {int(first['Month'])} · {first['Event type']}**"
        )
        st.write(first["Message"])
        st.divider()


# ---------------------------------------------------------
# Synthetic population explorer - secondary
# ---------------------------------------------------------

with st.expander("Explore the wider synthetic population"):

    st.caption(
        "This is a separate 1,000-person population experiment. "
        "The four-month scripted interactions above are not linked "
        "to these population members."
    )

    try:
        population = load_population(False)
    except Exception as error:
        st.error(f"The population experiment could not be loaded: {error}")
        st.stop()

    agents = sorted(
        population.agents,
        key=lambda agent: agent.agent_id,
    )

    agent_lookup = {
        agent.agent_id: agent
        for agent in agents
    }

    selected_agent_id = st.selectbox(
        "Select a population member",
        [agent.agent_id for agent in agents],
        format_func=lambda agent_id: (
            f"{agent_id} · "
            f"{agent_lookup[agent_id].profile.role.replace('_', ' ').title()}"
        ),
    )

    selected_agent = agent_lookup[selected_agent_id]
    profile = selected_agent.profile

    st.markdown(
        f"**{profile.role.replace('_', ' ').title()}**"
    )

    st.write(
        f"{profile.age_group.replace('_', ' ').title()} · "
        f"{profile.geography.replace('_', ' ').title()}"
    )

    st.caption(
        f"Measured hearing status: "
        f"{profile.measured_hearing_status.replace('_', ' ').title()} | "
        f"Self-reported hearing status: "
        f"{profile.self_reported_hearing_status.replace('_', ' ').title()} | "
        f"Auditory functional status: "
        f"{profile.auditory_functional_status.replace('_', ' ').title()}"
    )

    communication_profile = profile.communication_profile.to_dict()

    specified_preferences = [
        (
            field.replace("_", " ").title(),
            ", ".join(values),
        )
        for field, values in communication_profile.items()
        if values
    ]

    if specified_preferences:
        st.markdown("**Recorded communication preferences**")
        for label, value in specified_preferences:
            st.write(f"**{label}:** {value}")
    else:
        st.caption(
            "No communication preferences or strategies have been specified."
        )

    person_relationships = [
        relationship
        for relationship in population.relationships
        if relationship.agent_id == selected_agent_id
    ]

    st.write(
        f"**Recorded social connections:** {len(person_relationships)}"
    )

    if person_relationships:
        for relationship in person_relationships:
            contact = agent_lookup.get(relationship.contact_id)

            contact_label = (
                contact.profile.role.replace("_", " ").title()
                if contact else "Unknown"
            )

            st.write(
                f"• {relationship.relationship_type.title()} · "
                f"{contact_label}"
            )

    st.caption(
        "Individual communication experience histories have not yet "
        "been simulated for these population members."
    )


