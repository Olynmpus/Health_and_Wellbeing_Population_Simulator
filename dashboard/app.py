from pathlib import Path
from collections import Counter
import sys
import math
import json
import tempfile
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.simulation.population_experiment import (
    run_population_experiment,
    run_population_experiment_repetitions,
    compare_population_experiments,
)
from dashboard.shared import load_longitudinal

CONFIG = ROOT / "config" / "HH-EXP-001.json"
DISTRIBUTION = ROOT / "config" / "population_australia_2025.json"
INTERVENTION = ROOT / "config" / "interventions" / "mobile_hearing_outreach.json"
DEFAULT_POPULATION_SIZE = json.loads(
    CONFIG.read_text(encoding="utf-8")
)["population"]["size"]


st.set_page_config(
    page_title="Health and Wellbeing Population Simulator",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #F8FAFC; color: #172033; }
    [data-testid="stSidebar"] {
        background-color: #F1F5F9;
        border-right: 1px solid #D9E2EC;
    }
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #D9E2EC;
        padding: 16px;
        border-radius: 10px;
    }
    [data-testid="stMetricLabel"] { color: #526176; }
    [data-testid="stMetricValue"] { color: #172033; }
    .hero {
        padding: 28px 32px;
        border: 1px solid #D9E2EC;
        border-radius: 14px;
        background: linear-gradient(115deg, #FFFFFF, #EFF6FF);
        margin-bottom: 20px;
    }
    .hero h1 { margin: 0; color: #172033; font-size: 2rem; }
    .hero p { color: #526176; margin-bottom: 0; }
    .credit {
        color: #64748B;
        text-align: center;
        font-size: 0.82rem;
        padding: 24px 0 10px 0;
    }
    h1, h2, h3, h4 { color: #172033; }
    [data-testid="stTabs"] button { color: #475569; font-weight: 600; }
    [data-testid="stTabs"] button[aria-selected="true"] { color: #1D4ED8; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Running population experiment...")
def load_population(use_intervention, population_size):
    intervention_path = str(INTERVENTION) if use_intervention else None
    return run_population_experiment(
        str(CONFIG),
        str(DISTRIBUTION),
        intervention_path,
        population_size_override=population_size,
    )


def distribution_frame(distribution):
    return pd.DataFrame([
        {"Category": key.replace("_", " ").title(),
         "People": value["count"],
         "Percentage": value["percentage"]}
        for key, value in distribution.items()
    ])

def build_service_pathway(support_records, month_filter, geography_filter):
    """Build a population-level Sankey from linked service records."""

    transitions = Counter()
    people = set()
    request_count = 0
    allocation_counts = Counter()
    delivery_counts = Counter()

    for record in support_records:
        geography = record.agent.profile.geography

        if geography_filter != "All" and geography != geography_filter:
            continue

        allocations = {
            item.demand_id: item for item in record.service_allocations
        }
        deliveries = {
            item.demand_id: item for item in record.service_deliveries
        }

        for demand in record.service_demands:
            if (
                month_filter is not None
                and demand.request_month != month_filter
            ):
                continue

            request_count += 1
            people.add(record.agent_id)

            allocation = allocations.get(demand.demand_id)
            delivery = deliveries.get(demand.demand_id)

            if allocation is None:
                allocation_label = "Allocation not recorded"
            elif allocation.allocation_status == "allocated":
                allocation_label = "Allocated"
            else:
                allocation_label = "Not allocated"

            allocation_counts[allocation_label] += 1

            transitions[
                (("Requests", "Service requests"),
                 ("Allocation", allocation_label))
            ] += 1

            if allocation_label != "Allocated":
                continue

            if delivery is None:
                attendance_label = "Attendance not recorded"
                delivery_label = "Delivery not recorded"
            else:
                attendance_label = {
                    "attended": "Attended",
                    "did_not_attend": "Did not attend",
                    "not_yet_due": "Not yet due",
                    "unknown": "Attendance unknown",
                }.get(
                    delivery.attendance_status,
                    "Attendance unknown",
                )

                delivery_label = {
                    "delivered": "Delivered",
                    "not_delivered": "Not delivered",
                    "unknown": "Delivery unknown",
                }.get(
                    delivery.delivery_status,
                    "Delivery unknown",
                )

            delivery_counts[delivery_label] += 1

            transitions[
                (("Allocation", allocation_label),
                 ("Attendance", attendance_label))
            ] += 1

            transitions[
                (("Attendance", attendance_label),
                 ("Delivery", delivery_label))
            ] += 1

    metrics = {
        "requests": request_count,
        "people": len(people),
        "allocated": allocation_counts["Allocated"],
        "delivered": delivery_counts["Delivered"],
    }

    if not request_count:
        return None, metrics

    stage_order = {
        "Requests": 0,
        "Allocation": 1,
        "Attendance": 2,
        "Delivery": 3,
    }

    node_keys = {
        node
        for source, target in transitions
        for node in (source, target)
    }
    node_keys = sorted(
        node_keys,
        key=lambda node: (stage_order[node[0]], node[1]),
    )
    node_ids = {node: index for index, node in enumerate(node_keys)}

    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(
            label=[label for _, label in node_keys],
            x=[stage_order[stage] / 3 for stage, _ in node_keys],
            pad=18,
            thickness=18,
            line=dict(color="#CBD5E1", width=0.7),
        ),
        link=dict(
            source=[
                node_ids[source]
                for source, target in transitions
            ],
            target=[
                node_ids[target]
                for source, target in transitions
            ],
            value=list(transitions.values()),
            hovertemplate="%{value} requests<extra></extra>",
        ),
    ))

    fig.update_layout(
        height=470,
        margin=dict(l=15, r=15, t=20, b=20),
        paper_bgcolor="#FFFFFF",
        font=dict(color="#243247", size=12),
    )

    return fig, metrics

def outcome_group(outcome):
    if outcome in {
        "negative_communication",
        "misdirected_information",
        "blocked_service_access",
    }:
        return "Negative experience"
    if outcome == "supportive_communication":
        return "Positive experience"
    return "Not classified"


def make_network(relationships, selected_agent, status_filter):
    nodes = {
        "PERSON-001": {
            "label": "Person",
            "role": "Community member",
            "colour": "#38bdf8",
            "x": 0,
            "y": 0,
        },
        "FAMILY-001": {
            "label": "Family",
            "role": "Family member",
            "colour": "#a78bfa",
            "x": -1.2,
            "y": 0.8,
        },
        "FRIEND-001": {
            "label": "Friend",
            "role": "Friend",
            "colour": "#34d399",
            "x": -1.2,
            "y": -0.8,
        },
        "SERVICE-001": {
            "label": "Service",
            "role": "Service representative",
            "colour": "#fbbf24",
            "x": 1.2,
            "y": 0,
        },
    }

    agent_relationships = relationships.get(selected_agent, {})

    status_colours = {
        "active": "#34d399",
        "strained": "#f59e0b",
        "disconnected": "#f87171",
    }

    edge_traces = []

    for contact_id, relationship in agent_relationships.items():
        if status_filter != "All" and relationship.status != status_filter:
            continue

        start = nodes[selected_agent]
        end = nodes[contact_id]
        colour = status_colours.get(relationship.status, "#94a3b8")

        edge_traces.append(go.Scatter(
            x=[start["x"], end["x"]],
            y=[start["y"], end["y"]],
            mode="lines",
            line=dict(width=3, color=colour),
            hovertemplate=(
                f"<b>{selected_agent} → {contact_id}</b><br>"
                f"Relationship: {relationship.relationship_type}<br>"
                f"Trust: {relationship.trust:.2f}<br>"
                f"Perceived support: {relationship.perceived_support:.2f}<br>"
                f"Interactions/month: "
                f"{relationship.interactions_per_month:.2f}<br>"
                f"Status: {relationship.status}<extra></extra>"
            ),
            showlegend=False,
        ))

    visible_nodes = {selected_agent}

    for contact_id, relationship in agent_relationships.items():
        if status_filter == "All" or relationship.status == status_filter:
            visible_nodes.add(contact_id)

    node_trace = go.Scatter(
        x=[nodes[agent_id]["x"] for agent_id in visible_nodes],
        y=[nodes[agent_id]["y"] for agent_id in visible_nodes],
        mode="markers+text",
        text=[nodes[agent_id]["label"] for agent_id in visible_nodes],
        textposition="bottom center",
        customdata=[
            [nodes[agent_id]["role"], agent_id]
            for agent_id in visible_nodes
        ],
        hovertemplate=(
            "<b>%{text}</b><br>%{customdata[0]}"
            "<br>%{customdata[1]}<extra></extra>"
        ),
        marker=dict(
            size=[
                48 if agent_id == selected_agent else 38
                for agent_id in visible_nodes
            ],
            color=[
                nodes[agent_id]["colour"]
                for agent_id in visible_nodes
            ],
            line=dict(width=2, color="#e2e8f0"),
        ),
        showlegend=False,
    )

    fig = go.Figure(data=edge_traces + [node_trace])

    fig.update_layout(
        height=470,
        margin=dict(l=20, r=20, t=25, b=35),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#243247"),
        xaxis=dict(visible=False, range=[-1.8, 1.8]),
        yaxis=dict(visible=False, range=[-1.2, 1.2]),
        hovermode="closest",
    )

    return fig


def make_household_network(agents, relationships, household_id=None):
    """Display one household or the combined population household network."""

    if household_id is None:
        members = list(agents)
    else:
        members = [
            agent for agent in agents
            if agent.household_id == household_id
        ]

    households = {}
    for agent in members:
        key = agent.household_id or agent.agent_id
        households.setdefault(key, []).append(agent)

    positions = {}
    household_keys = sorted(households)
    columns = max(1, math.ceil(math.sqrt(len(household_keys))))

    for index, key in enumerate(household_keys):
        centre_x = (index % columns) * 2.5
        centre_y = -(index // columns) * 2.5
        household = households[key]

        for member_index, agent in enumerate(household):
            angle = 2 * math.pi * member_index / max(len(household), 1)
            radius = 0.38 if len(household) > 1 else 0
            positions[agent.agent_id] = (
                centre_x + radius * math.cos(angle),
                centre_y + radius * math.sin(angle),
            )

    member_ids = set(positions)
    edge_groups = {}
    seen_edges = set()

    relationship_colours = {
        "family": "#a78bfa",
        "friend": "#34d399",
        "community": "#38bdf8",
    }

    for relationship in relationships:
        source = relationship.agent_id
        target = relationship.contact_id

        if source not in member_ids or target not in member_ids:
            continue

        edge = tuple(sorted((source, target)))
        if edge in seen_edges:
            continue

        seen_edges.add(edge)

        relationship_type = relationship.relationship_type
        edge_groups.setdefault(relationship_type, ([], []))

        x1, y1 = positions[source]
        x2, y2 = positions[target]

        edge_x, edge_y = edge_groups[relationship_type]
        edge_x.extend([x1, x2, None])
        edge_y.extend([y1, y2, None])

    fig = go.Figure()

    for relationship_type, (edge_x, edge_y) in edge_groups.items():
        fig.add_trace(go.Scatter(
            x=edge_x,
            y=edge_y,
            mode="lines",
            line=dict(
                width=1.5,
                color=relationship_colours.get(
                    relationship_type, "#64748b"
                ),
            ),
            name=relationship_type.replace("_", " ").title(),
            hoverinfo="skip",
        ))

    geography_colours = {
        "metropolitan": "#38bdf8",
        "regional": "#a78bfa",
        "remote_very_remote": "#f59e0b",
    }

    show_labels = household_id is not None

    for geography, colour in geography_colours.items():
        group = [
            agent for agent in members
            if agent.summary()["geography"] == geography
        ]
        if not group:
            continue

        fig.add_trace(go.Scatter(
            x=[positions[a.agent_id][0] for a in group],
            y=[positions[a.agent_id][1] for a in group],
            mode="markers+text" if show_labels else "markers",
            text=[a.agent_id for a in group] if show_labels else None,
            textposition="bottom center",
            customdata=[
                [
                    a.summary()["age_group"],
                    a.summary()["geography"],
                    a.summary()["measured_hearing_status"],
                    a.summary()["self_reported_hearing_status"],
                    a.summary()["auditory_functional_status"],
                    a.household_id or "No household recorded",
                ]
                for a in group
            ],
            hovertemplate=(
                "<b>%{text}</b><br>" if show_labels else
                "<b>Participant</b><br>"
            ) + (
                "Age group: %{customdata[0]}<br>"
                "Geography: %{customdata[1]}<br>"
                "Measured hearing status: %{customdata[2]}<br>"
                "Self-reported hearing status: %{customdata[3]}<br>"
                "Auditory functional status: %{customdata[4]}<br>"
                "Household: %{customdata[5]}"
                "<extra></extra>"
            ),
            marker=dict(
                size=28 if show_labels else 9,
                color=colour,
                line=dict(width=1, color="#e2e8f0"),
            ),
            name=geography.replace("_", " ").title(),
        ))

    fig.update_layout(
        height=850 if household_id is None else 480,
        margin=dict(l=30, r=30, t=30, b=50),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#243247"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        legend=dict(
            orientation="h",
            y=-0.04,
            font=dict(color="#FFFFFF", size=14),
            bgcolor="#FFFFFF",
        ),
        hovermode="closest",
        )

    return fig, len(seen_edges)

def make_individual_network(agents, relationships, selected_agent_id):
    """Display an individual and their connected social network."""

    direct_contacts = set()

    for relationship in relationships:
        if relationship.agent_id == selected_agent_id:
            direct_contacts.add(relationship.contact_id)
        elif relationship.contact_id == selected_agent_id:
            direct_contacts.add(relationship.agent_id)

    network_ids = direct_contacts | {selected_agent_id}
    contacts = sorted(direct_contacts)

    positions = {selected_agent_id: (0, 0)}

    for index, agent_id in enumerate(contacts):
        angle = 2 * math.pi * index / max(len(contacts), 1)
        positions[agent_id] = (
            1.5 * math.cos(angle),
            1.5 * math.sin(angle),
        )

    relationship_colours = {
        "family": "#a78bfa",
        "friend": "#34d399",
        "community": "#38bdf8",
    }

    fig = go.Figure()
    seen_edges = set()

    for relationship in relationships:
        source = relationship.agent_id
        target = relationship.contact_id

        if source not in network_ids or target not in network_ids:
            continue

        edge = tuple(sorted((source, target)))

        if edge in seen_edges:
            continue

        seen_edges.add(edge)

        x1, y1 = positions[source]
        x2, y2 = positions[target]

        colour = relationship_colours.get(
            relationship.relationship_type, "#64748b"
        )

        fig.add_trace(go.Scatter(
            x=[x1, x2],
            y=[y1, y2],
            mode="lines",
            line=dict(width=2, color=colour),
            hovertemplate=(
                f"{source} ↔ {target}<br>"
                f"Relationship: {relationship.relationship_type}<br>"
                f"Trust: {relationship.trust:.2f}<br>"
                f"Perceived support: {relationship.perceived_support:.2f}<br>"
                f"Interactions/month: "
                f"{relationship.interactions_per_month:.2f}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    agent_lookup = {agent.agent_id: agent for agent in agents}

    for agent_id in network_ids:
        agent = agent_lookup[agent_id]
        x, y = positions[agent_id]
        is_selected = agent_id == selected_agent_id

        fig.add_trace(go.Scatter(
            x=[x],
            y=[y],
            mode="markers+text",
            text=[agent_id],
            textposition="bottom center",
            marker=dict(
                size=38 if is_selected else 28,
                color="#fbbf24" if is_selected else "#38bdf8",
                line=dict(width=2, color="#e2e8f0"),
            ),
            customdata=[[
                agent.summary()["age_group"],
                agent.summary()["geography"],
                agent.summary()["measured_hearing_status"],
                agent.summary()["self_reported_hearing_status"],
                agent.summary()["auditory_functional_status"],
            ]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Age group: %{customdata[0]}<br>"
                "Geography: %{customdata[1]}<br>"
                "Measured hearing status: %{customdata[2]}<br>"
                "Self-reported hearing status: %{customdata[3]}<br>"
                "Auditory functional status: %{customdata[4]}"
                "<extra></extra>"
            ),
            showlegend=False,
        ))

    fig.update_layout(
        height=650,
        margin=dict(l=30, r=30, t=30, b=50),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(color="#243247"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        hovermode="closest",
    )

    return fig, len(seen_edges), len(direct_contacts)


# Sidebar
st.sidebar.markdown("## Reference experiment controls")

population_size = st.sidebar.number_input(
    "Population size",
    min_value=1,
    value=DEFAULT_POPULATION_SIZE,
    step=1000,
    help="Number of synthetic people generated for this experiment.",
)

scenario = st.sidebar.selectbox(
    "Population scenario",
    ["Baseline", "Mobile hearing outreach"],
)

enable_llm = st.sidebar.checkbox(
    "Enable local LLM interpretations",
    value=False,
    help="Uses the configured local Ollama model for the first interaction.",
)

st.sidebar.caption(
    "The population scenario and the four-agent longitudinal demonstration "
    "are separate model runs."
)

use_intervention = scenario == "Mobile hearing outreach"

try:
    population = load_population(use_intervention, population_size)
    summary = population.summary()
    person, relationships, histories, snapshots = load_longitudinal(enable_llm)
except Exception as error:
    st.error(f"The experiment could not be loaded: {error}")
    st.stop()


# Header
st.markdown("""
<div class="hero">
    <h1>Health and Wellbeing Population Simulator</h1>
    <p>Explore population characteristics, service access, individual experiences
    and relationships in a configurable population simulation.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    f"{summary['experiment_name']} · {summary['country_name']} reference framework "
    f"· Evidence status: {summary['evidence_status']}"
)

st.info(
    "This dashboard currently demonstrates the simulator's initial "
    "hearing-support reference implementation. The broader health and "
    "wellbeing model is under development."
)

overview_tab, journeys_tab, analytics_tab, experiment_tab = st.tabs([
    "Overview",
    "Journeys",
    "Analytics",
    "Experiment Lab",
])


# Population overview
with overview_tab:
    st.subheader("Population at a glance")
    st.write(
        "A high-level view of the simulated population and the service "
        "system supporting it."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Simulated people", f"{summary['population_size']:,}")
    c2.metric("Simulation duration", f"{summary['duration_months']} months")
    c3.metric("Support records", f"{summary['support_record_count']:,}")
    c4.metric("Service demands", summary["service_delivery"]["total_demands"])

    st.divider()
    st.markdown("#### Service system performance")
    service = summary["service_delivery"]

    c1, c2, c3 = st.columns(3)
    c1.metric("Allocated", service["allocated"])
    c2.metric("Unallocated", service["unallocated"])
    c3.metric("Total demand", service["total_demands"])

    delivery_left, delivery_right = st.columns(2)

    with delivery_left:
        st.markdown("**Attendance**")
        attendance = pd.DataFrame([
            {"Status": key.replace("_", " ").title(), "Count": value}
            for key, value in service["attendance"].items()
        ])
        if not attendance.empty:
            st.dataframe(attendance, hide_index=True, width="stretch")

    with delivery_right:
        st.markdown("**Delivery outcomes**")
        delivery = pd.DataFrame([
            {"Status": key.replace("_", " ").title(), "Count": value}
            for key, value in service["delivery_outcomes"].items()
        ])
        if not delivery.empty:
            st.dataframe(delivery, hide_index=True, width="stretch")

    st.divider()
    st.markdown("#### Planned service capacity")

    operational = summary["operational_assessment"]
    schedule = operational["planned_schedule"]

    if schedule is not None:
        capacity_col1, capacity_col2, capacity_col3 = st.columns(3)

        capacity_col1.metric(
            "Planned appointments / month",
            schedule["planned_appointments_per_month"],
        )
        capacity_col2.metric(
            "Planned trips / month",
            schedule["planned_trips_per_month"],
        )
        capacity_col3.metric(
            "Maximum deliverable / month",
            schedule["maximum_deliverable_appointments_per_month"],
        )

        st.caption(
            f"{schedule['service_type'].replace('_', ' ').title()} · "
            f"{schedule['planned_clinical_hours_per_month']:g} planned "
            "clinical hours per month · "
            f"Schedule: {schedule['schedule_status']}"
        )

    st.markdown("**Capacity assessment**")
    st.write(
        f"Status: **{operational['capacity_status'].replace('_', ' ').title()}**"
    )

    constraints = operational["capacity_constraints"]
    if constraints:
        st.write(
            "Limiting constraints: "
            + ", ".join(item.replace("_", " ") for item in constraints)
        )
    else:
        st.write("No limiting constraints recorded.")

    if operational["capacity_reasons"]:
        for reason in operational["capacity_reasons"]:
            st.write(f"- {reason}")

    financial_col1, financial_col2 = st.columns(2)

    with financial_col1:
        st.markdown("**Operational costs**")
        st.write("Not configured")

    with financial_col2:
        st.markdown("**Funding assessment**")
        st.write("Not configured")

    st.caption(
        "Capacity describes the configured regional audiology service. "
        "It is not a measure of actual service delivery. Remote outreach "
        "and financial feasibility are not included in this assessment."
    )
    st.caption(
        "The population is hypothetical and generated from simulation "
        "assumptions. It is not an estimate of Australia's population."
    )



# Population journey explorer
with journeys_tab:
    st.subheader("Individual journey map")
    st.caption(
        "Four-month illustrative demonstration. This is separate from "
        "the 1,000-person population experiment."
    )

    journey_participants = list(histories.keys())
    default_person_index = (
        journey_participants.index(person.agent_id)
        if person.agent_id in journey_participants else 0
    )

    selected_participant = st.selectbox(
        "Participant perspective",
        journey_participants,
        index=default_person_index,
        key="journey_participant",
    )

    journey_records = histories[selected_participant]

    if journey_records:
        journey_rows = []

        for record in journey_records:
            details = record.get("additional_details", {})
            event_type = record.get("event_type", "other")
            outcome = record.get("outcome", "not_established")

            if event_type == "family_interaction":
                context = "Family and social context"
            elif event_type == "social_interaction":
                context = "Social and communication"
            elif event_type == "service_interaction":
                context = "Health and support services"
            else:
                context = "Other recorded interaction"

            if outcome in {
                "negative_communication",
                "misdirected_information",
            }:
                experience = "Difficulty / unmet need"
                colour = "#DC6B65"
            elif outcome == "supportive_communication":
                experience = "Supportive experience"
                colour = "#269B79"
            elif outcome == "blocked_service_access":
                experience = "Access barrier"
                colour = "#D99436"
            else:
                experience = "Not established"
                colour = "#94A3B8"

            participants = details.get("participants", [])
            other_participants = [
                item for item in participants
                if item != selected_participant
            ]

            journey_rows.append({
                "record": record,
                "details": details,
                "month": record.get("month", 0),
                "context": context,
                "event_type": event_type,
                "outcome": outcome,
                "experience": experience,
                "colour": colour,
                "other_participant": (
                    ", ".join(other_participants)
                    if other_participants else "Not recorded"
                ),
            })

        journey_rows.sort(key=lambda item: item["month"])

        route_fig = go.Figure()
        route_fig.add_trace(go.Scatter(
            x=[item["month"] for item in journey_rows],
            y=[item["context"] for item in journey_rows],
            mode="lines+markers+text",
            text=[f"Month {item['month']}" for item in journey_rows],
            textposition="top center",
            line={"color": "#64748B", "width": 3},
            marker={
                "size": 19,
                "color": [item["colour"] for item in journey_rows],
                "line": {"color": "#FFFFFF", "width": 2},
            },
            customdata=[
                [
                    item["event_type"].replace("_", " ").title(),
                    item["experience"],
                    item["other_participant"],
                ]
                for item in journey_rows
            ],
            hovertemplate=(
                "%{y}<br>"
                "%{customdata[0]}<br>"
                "%{customdata[1]}<br>"
                "Other participant: %{customdata[2]}"
                "<extra></extra>"
            ),
        ))

        route_fig.update_layout(
            height=390,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font={"color": "#243247", "size": 12},
            margin={"l": 10, "r": 25, "t": 45, "b": 45},
            xaxis={
                "title": "Simulation month",
                "tickmode": "linear",
                "dtick": 1,
                "showgrid": True,
                "gridcolor": "#E2E8F0",
            },
            yaxis={
                "title": "",
                "categoryorder": "array",
                "categoryarray": [
                    "Family and social context",
                    "Social and communication",
                    "Health and support services",
                    "Other recorded interaction",
                ],
                "showgrid": True,
                "gridcolor": "#E2E8F0",
            },
            showlegend=False,
            hovermode="closest",
        )

        st.plotly_chart(route_fig, width="stretch")

        st.caption(
            "The route connects recorded events in chronological order. "
            "It does not imply that unrecorded stages occurred."
        )

        journey_labels = [
            (
                f"Month {item['month']} · "
                f"{item['event_type'].replace('_', ' ').title()}"
            )
            for item in journey_rows
        ]

        selected_event_index = st.selectbox(
            "Explore a recorded event",
            range(len(journey_rows)),
            format_func=lambda index: journey_labels[index],
            key="journey_event",
        )

        selected_event = journey_rows[selected_event_index]
        selected_record = selected_event["record"]
        selected_details = selected_event["details"]

        detail_left, detail_right = st.columns(2)

        with detail_left:
            st.markdown("**Recorded event**")
            st.write(selected_record.get("actual_message") or "Not recorded")
            st.markdown("**Participant interpretation**")
            st.write(
                selected_record.get("agent_interpretation")
                or "Not established"
            )
            st.markdown("**Observed event**")
            st.write(
                selected_details.get("observed_event")
                or "Not recorded"
            )

        with detail_right:
            st.markdown("**Participant report**")
            st.write(
                selected_details.get("participant_report")
                or "No participant report recorded"
            )
            st.markdown("**Other participant**")
            st.write(selected_event["other_participant"])
            st.markdown("**Recorded outcome**")
            st.write(selected_event["outcome"].replace("_", " ").title())

        provenance = selected_details.get(
            "interpretation_provenance", {}
        )
        st.caption(
            "Interpretation provenance: "
            f"{provenance.get('source', 'Not recorded')} · "
            f"{provenance.get('evidence_status', 'Not established')} · "
            f"Verified: {provenance.get('verified', 'Unknown')}"
        )

        st.markdown("**Communication effort and fatigue**")
        st.info(
            "Listening effort, listening fatigue and cognitive fatigue "
            "are not measured in this illustrative journey. They are "
            "not inferred from communication difficulty or interaction "
            "outcomes."
        )
    else:
        st.info("No recorded events are available for this participant.")

with analytics_tab:
    st.subheader("What happens to the population?")
    st.write(
        "Start with everyone in the selected population, then follow "
        "recorded functional status and service-request outcomes."
    )

    geographies = sorted({
        agent.profile.geography for agent in population.agents
    })
    selected_geography = st.selectbox(
        "Population group",
        ["All geographies"] + geographies,
        key="explore_geography",
    )

    selected_records = [
        record for record in population.support_records
        if (
            selected_geography == "All geographies"
            or record.agent.profile.geography == selected_geography
        )
    ]

    selected_agent_ids = {
        record.agent_id for record in selected_records
    }

    need_statuses = [
        "no_identified_difficulty",
        "difficulty_reported",
        "functional_difficulty_confirmed",
        "unknown",
    ]

    person_status = {}
    person_has_request = {}

    for record in selected_records:
        initial_need = next(
            (
                need for need in record.hearing_support_needs
                if need.assessment_month == 0
            ),
            None,
        )
        status = (
            initial_need.functional_difficulty_status
            if initial_need is not None
            else "unknown"
        )
        if status not in need_statuses:
            status = "unknown"

        person_status[record.agent_id] = status
        person_has_request[record.agent_id] = bool(record.service_demands)

    selected_demands = [
        demand
        for record in selected_records
        for demand in record.service_demands
    ]
    selected_demand_ids = {
        demand.demand_id for demand in selected_demands
    }

    allocations_by_demand = {
        allocation.demand_id: allocation
        for record in selected_records
        for allocation in record.service_allocations
        if allocation.demand_id in selected_demand_ids
    }

    deliveries_by_demand = {
        delivery.demand_id: delivery
        for record in selected_records
        for delivery in record.service_deliveries
        if delivery.demand_id in selected_demand_ids
    }

    total_population = len(selected_records)
    functional_counts = Counter(person_status.values())
    people_with_requests = sum(person_has_request.values())
    people_without_requests = total_population - people_with_requests

    allocation_counts = Counter(
        allocation.allocation_status
        for allocation in allocations_by_demand.values()
    )

    allocated = allocation_counts["allocated"]
    unallocated = allocation_counts["unallocated"]
    request_count = len(selected_demands)
    allocation_not_recorded = max(
        0, request_count - len(allocations_by_demand)
    )

    attendance_counts = Counter(
        delivery.attendance_status
        for delivery in deliveries_by_demand.values()
    )
    delivery_counts = Counter(
        delivery.delivery_status
        for delivery in deliveries_by_demand.values()
    )

    attended = attendance_counts["attended"]
    did_not_attend = attendance_counts["did_not_attend"]
    delivered = delivery_counts["delivered"]

    def percentage(numerator, denominator):
        return (
            f"{numerator / denominator * 100:.1f}%"
            if denominator else "—"
        )

    st.markdown("#### 1. Population profile")
    st.caption(
        "Who is included in the selected population? "
        "Bars show the number and percentage of people in each category."
    )

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Population", total_population)
    metric2.metric(
        "People with recorded difficulty",
        functional_counts["difficulty_reported"]
        + functional_counts["functional_difficulty_confirmed"],
    )
    metric3.metric("People generating a request", people_with_requests)
    metric4.metric("Services delivered", delivered)

    profile_labels = [
        "No identified difficulty",
        "Difficulty reported",
        "Functional difficulty confirmed",
        "Unknown functional status",
    ]
    profile_values = [
        functional_counts[status] for status in need_statuses
    ]
    profile_percentages = [
        value / total_population * 100 if total_population else 0
        for value in profile_values
    ]

    if total_population:
        profile_fig = go.Figure(go.Bar(
            x=profile_values,
            y=profile_labels,
            orientation="h",
            marker={
                "color": ["#94A3B8", "#60A5FA", "#2563EB", "#CBD5E1"]
            },
            text=[
                f"{value:,}  ({rate:.1f}%)"
                for value, rate in zip(
                    profile_values, profile_percentages
                )
            ],
            textposition="outside",
            cliponaxis=False,
            hovertemplate=(
                "%{y}<br>%{x} people"
                "<extra></extra>"
            ),
        ))
        profile_fig.update_layout(
            height=290,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font={"color": "#243247", "size": 13},
            margin={"l": 10, "r": 100, "t": 10, "b": 25},
            xaxis={
                "title": "Number of people",
                "rangemode": "tozero",
                "showgrid": True,
                "gridcolor": "#E2E8F0",
            },
            yaxis={
                "title": "",
                "autorange": "reversed",
                "showgrid": False,
            },
            showlegend=False,
        )
        st.plotly_chart(profile_fig, width="stretch")
    else:
        st.info("No people match this population group.")

    st.divider()
    st.markdown("#### 2. Population service pathway")
    st.caption(
        "Each flow represents one recorded service demand. Follow requests "
        "through allocation, attendance and service delivery. Missing records "
        "are shown separately rather than treated as negative outcomes."
    )

    pathway_months = sorted({
        demand.request_month for demand in selected_demands
    })

    selected_request_month = st.selectbox(
        "Service request month",
        ["All months"] + pathway_months,
        format_func=lambda month: (
            month if month == "All months" else f"Month {month}"
        ),
        key="service_pathway_month",
    )

    pathway_demands = [
        demand for demand in selected_demands
        if (
            selected_request_month == "All months"
            or demand.request_month == selected_request_month
        )
    ]
    pathway_demand_ids = {
        demand.demand_id for demand in pathway_demands
    }

    pathway_allocations = {
        demand_id: allocation
        for demand_id, allocation in allocations_by_demand.items()
        if demand_id in pathway_demand_ids
    }
    pathway_deliveries = {
        demand_id: delivery
        for demand_id, delivery in deliveries_by_demand.items()
        if demand_id in pathway_demand_ids
    }

    pathway_request_count = len(pathway_demands)
    pathway_allocation_counts = Counter(
        allocation.allocation_status
        for allocation in pathway_allocations.values()
    )
    pathway_allocated = pathway_allocation_counts["allocated"]
    pathway_unallocated = pathway_allocation_counts["unallocated"]
    pathway_allocation_not_recorded = max(
        0, pathway_request_count - len(pathway_allocations)
    )

    attendance_node = {
        "attended": 4,
        "did_not_attend": 5,
        "unknown": 6,
        "not_yet_due": 7,
    }
    delivery_node = {
        "delivered": 9,
        "not_delivered": 10,
        "unknown": 11,
    }

    sankey_missing_delivery = sum(
        1
        for demand_id, allocation in pathway_allocations.items()
        if (
            allocation.allocation_status == "allocated"
            and demand_id not in pathway_deliveries
        )
    )

    sankey_attendance_counts = Counter()
    sankey_delivery_counts = Counter()
    attendance_delivery_counts = Counter()

    for demand_id, allocation in pathway_allocations.items():
        if allocation.allocation_status != "allocated":
            continue

        delivery = pathway_deliveries.get(demand_id)
        if delivery is None:
            continue

        sankey_attendance_counts[delivery.attendance_status] += 1
        sankey_delivery_counts[delivery.delivery_status] += 1
        attendance_delivery_counts[
            (delivery.attendance_status, delivery.delivery_status)
        ] += 1

    sankey_labels = [
        f"Service requests ({pathway_request_count})",
        f"Allocated ({pathway_allocated})",
        f"Unallocated ({pathway_unallocated})",
        f"Allocation not recorded ({pathway_allocation_not_recorded})",
        f"Attended ({sankey_attendance_counts['attended']})",
        f"Did not attend ({sankey_attendance_counts['did_not_attend']})",
        f"Attendance unknown ({sankey_attendance_counts['unknown']})",
        f"Not yet due ({sankey_attendance_counts['not_yet_due']})",
        f"No delivery record ({sankey_missing_delivery})",
        f"Delivered ({sankey_delivery_counts['delivered']})",
        f"Not delivered ({sankey_delivery_counts['not_delivered']})",
        f"Delivery status unknown ({sankey_delivery_counts['unknown']})",
    ]

    sankey_sources = []
    sankey_targets = []
    sankey_values = []

    def add_sankey_link(source_index, target_index, value):
        if value > 0:
            sankey_sources.append(source_index)
            sankey_targets.append(target_index)
            sankey_values.append(value)

    add_sankey_link(0, 1, pathway_allocated)
    add_sankey_link(0, 2, pathway_unallocated)
    add_sankey_link(0, 3, pathway_allocation_not_recorded)

    for demand_id, allocation in pathway_allocations.items():
        if allocation.allocation_status != "allocated":
            continue

        delivery = pathway_deliveries.get(demand_id)
        if delivery is None:
            add_sankey_link(1, 8, 1)
            continue

        add_sankey_link(
            1,
            attendance_node[delivery.attendance_status],
            1,
        )

    for (attendance_status, delivery_status), count in (
        attendance_delivery_counts.items()
    ):
        add_sankey_link(
            attendance_node[attendance_status],
            delivery_node[delivery_status],
            count,
        )

    if pathway_request_count:
        journey_fig = go.Figure(go.Sankey(
            arrangement="fixed",
            node={
                "label": sankey_labels,
                "x": [
                    0.01,
                    0.34, 0.34, 0.34,
                    0.67, 0.67, 0.67, 0.67, 0.67,
                    0.98, 0.98, 0.98,
                ],
                "y": [
                    0.5,
                    0.15, 0.5, 0.85,
                    0.05, 0.25, 0.45, 0.65, 0.88,
                    0.15, 0.5, 0.85,
                ],
                "pad": 18,
                "thickness": 20,
                "line": {"color": "#FFFFFF", "width": 1},
                "color": [
                    "#64748B",
                    "#0D9488", "#F59E0B", "#CBD5E1",
                    "#0D9488", "#F59E0B", "#CBD5E1", "#CBD5E1",
                    "#94A3B8",
                    "#16A34A", "#F59E0B", "#CBD5E1",
                ],
            },
            link={
                "source": sankey_sources,
                "target": sankey_targets,
                "value": sankey_values,
                "color": "rgba(100, 116, 139, 0.25)",
                "hovertemplate": (
                    "%{value:,} service demands"
                    "<extra></extra>"
                ),
            },
        ))

        journey_fig.update_layout(
            height=540,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font={"color": "#243247", "size": 12},
            margin={"l": 10, "r": 10, "t": 20, "b": 20},
        )
        st.plotly_chart(journey_fig, width="stretch")
    else:
        st.info("No service requests were recorded for this population group.")

    st.caption(
        "Flows count service demands, not unique people. Only allocated "
        "requests receive attendance and delivery records in the current "
        "simulation. Delivery status is currently determined directly by "
        "attendance; it is not an independent clinical outcome."
    )

    st.markdown("#### 3. Recorded service pathway")
    st.caption(
        "Unique people reaching each recorded service checkpoint. "
        "A person is counted once at each checkpoint, even if they have "
        "multiple service demands."
    )

    people_with_allocation = {
        allocation.agent_id
        for allocation in allocations_by_demand.values()
        if allocation.allocation_status == "allocated"
    }
    people_with_attendance = {
        delivery.agent_id
        for delivery in deliveries_by_demand.values()
        if delivery.attendance_status == "attended"
    }
    people_with_delivery = {
        delivery.agent_id
        for delivery in deliveries_by_demand.values()
        if delivery.delivery_status == "delivered"
    }

    journey_stages = [
        ("Population", total_population),
        ("Recorded demand", people_with_requests),
        ("Allocated", len(people_with_allocation)),
        ("Attended", len(people_with_attendance)),
        ("Service delivered", len(people_with_delivery)),
    ]

    journey_fig = go.Figure()

    journey_fig.add_trace(go.Scatter(
        x=list(range(len(journey_stages))),
        y=[0] * len(journey_stages),
        mode="lines",
        line={"color": "#94A3B8", "width": 5},
        hoverinfo="skip",
        showlegend=False,
    ))

    journey_fig.add_trace(go.Scatter(
        x=list(range(len(journey_stages))),
        y=[0] * len(journey_stages),
        mode="markers+text",
        marker={
            "size": [
                max(18, min(54, 18 + value / max(total_population, 1) * 36))
                for _, value in journey_stages
            ],
            "color": ["#64748B", "#3B82F6", "#0D9488", "#0D9488", "#16A34A"],
            "line": {"color": "#FFFFFF", "width": 3},
        },
        text=[
            f"{value:,}<br>{label}"
            for label, value in journey_stages
        ],
        textposition="top center",
        customdata=[
            [label, value, percentage(value, total_population)]
            for label, value in journey_stages
        ],
        hovertemplate=(
            "%{customdata[0]}<br>"
            "%{customdata[1]:,} unique people<br>"
            "%{customdata[2]} of selected population"
            "<extra></extra>"
        ),
        showlegend=False,
    ))

    journey_fig.update_layout(
        height=270,
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font={"color": "#243247", "size": 12},
        margin={"l": 20, "r": 20, "t": 95, "b": 20},
        xaxis={
            "visible": False,
            "range": [-0.35, len(journey_stages) - 0.65],
        },
        yaxis={"visible": False, "range": [-0.5, 1.1]},
        showlegend=False,
    )

    st.plotly_chart(journey_fig, width="stretch")

    st.caption(
        "These checkpoints are not mutually exclusive branches. "
        "People may have multiple requests, and may reach later stages "
        "through different requests. Counts are unique people, not events."
    )

    st.markdown("#### 3. Recorded service pathway")
    st.caption(
        "Follow the recorded service process. Percentages use the "
        "preceding eligible stage as their denominator."
    )

    missing_delivery_records = sum(
        1
        for demand_id, allocation in allocations_by_demand.items()
        if (
            allocation.allocation_status == "allocated"
            and demand_id not in deliveries_by_demand
        )
    )

    request_count = len(selected_demands)

    stage_columns = st.columns(4)

    with stage_columns[0]:
        st.markdown("**1. Service requests**")
        st.metric("Generated", request_count)
        st.caption(
            f"{percentage(request_count, total_population)} "
            "of the selected population"
        )

    with stage_columns[1]:
        st.markdown("**2. Allocation**")
        st.metric("Allocated", allocated)
        st.caption(
            f"{percentage(allocated, request_count)} of requests allocated"
        )
        st.caption(f"Unallocated: {unallocated}")
        if allocation_not_recorded:
            st.caption(f"Allocation not recorded: {allocation_not_recorded}")

    with stage_columns[2]:
        st.markdown("**3. Attendance**")
        st.metric("Attended", attended)
        st.caption(
            f"{percentage(attended, allocated)} of allocated requests"
        )
        st.caption(f"Did not attend: {did_not_attend}")
        if attendance_counts["unknown"]:
            st.caption(
                f"Attendance unknown: {attendance_counts['unknown']}"
            )
        if missing_delivery_records:
            st.caption(
                f"No delivery record: {missing_delivery_records}"
            )

    with stage_columns[3]:
        st.markdown("**4. Service delivery**")
        st.metric("Delivered", delivered)
        st.caption(
            f"{percentage(delivered, allocated)} of allocated requests"
        )
        st.caption(
            f"Not delivered: {delivery_counts['not_delivered']}"
        )
        if delivery_counts["unknown"]:
            st.caption(
                f"Delivery status unknown: {delivery_counts['unknown']}"
            )

    st.caption(
        "These are recorded simulation events, not observed real-world "
        "population rates. 'No request' does not mean a person declined care. "
        "Unknown and missing records are not treated as negative outcomes."
    )


    st.divider()
    st.markdown("#### 4. Hearing support use")
    st.caption(
        "Recorded use of hearing aids and other hearing supports. "
        "These measures are separate from formal service requests "
        "and service delivery."
    )

    selected_support_use_records = [
        support_use
        for record in selected_records
        for support_use in record.support_use_records
    ]

    people_with_support_use = {
        item.agent_id for item in selected_support_use_records
    }
    people_without_support_use = (
        total_population - len(people_with_support_use)
    )

    hearing_aid_records = [
        item for item in selected_support_use_records
        if item.support_type == "hearing_aid"
    ]

    ever_used_statuses = {
        "ever_used",
        "previously_used",
        "currently_using",
    }

    people_ever_used_hearing_aids = {
        item.agent_id
        for item in hearing_aid_records
        if item.use_status in ever_used_statuses
    }
    people_currently_using_hearing_aids = {
        item.agent_id
        for item in hearing_aid_records
        if item.use_status == "currently_using"
    }

    support_columns = st.columns(4)
    support_columns[0].metric(
        "People with recorded support use",
        len(people_with_support_use),
    )
    support_columns[1].metric(
        "No support-use record",
        people_without_support_use,
    )
    support_columns[2].metric(
        "Hearing-aid ever-use",
        len(people_ever_used_hearing_aids),
    )
    support_columns[3].metric(
        "Currently using hearing aids",
        len(people_currently_using_hearing_aids),
    )

    st.caption(
        "No support-use record means use has not been recorded; "
        "it does not mean the person has never used support. "
        "Ever-use includes people recorded as ever used, previously "
        "used or currently using hearing aids."
    )

    support_type_rows = []
    for support_type in sorted({
        item.support_type for item in selected_support_use_records
    }):
        type_records = [
            item for item in selected_support_use_records
            if item.support_type == support_type
        ]
        support_type_rows.append({
            "Support type": support_type.replace("_", " ").title(),
            "People with recorded use": len({
                item.agent_id for item in type_records
            }),
            "Records": len(type_records),
        })

    if support_type_rows:
        st.markdown("**Recorded use by support type**")
        st.dataframe(
            pd.DataFrame(support_type_rows),
            hide_index=True,
            width="stretch",
        )
    else:
        st.info(
            "No support-use records are available for this population group."
        )

    st.caption(
        "Hearing-aid use is calibrated to Australian Eye and Ear Health "
        "Survey 2025 estimates for specified measured impairment groups "
        "aged 50 and over. The displayed counts are simulated results, "
        "not observed Australian population counts. Other support types "
        "are not calibrated where suitable prevalence evidence is absent."
    )

    with st.expander("Explore population characteristics"):
        distributions = summary["population_distributions"]

        left, right = st.columns(2)

        with left:
            st.markdown("#### Measured hearing status")
            frame = distribution_frame(
                distributions["measured_hearing_status"]
            )
            fig = px.bar(
                frame, x="Category", y="People",
                color="Category", text="People",
            )
            fig.update_layout(
                showlegend=False, height=340,
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font_color="#243247",
            )
            st.plotly_chart(fig, width="stretch")

        with right:
            st.markdown("#### Self-reported hearing status")
            frame = distribution_frame(
                distributions["self_reported_hearing_status"]
            )
            fig = px.bar(
                frame, x="Category", y="People",
                color="Category", text="People",
            )
            fig.update_layout(
                showlegend=False, height=340,
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font_color="#243247",
            )
            st.plotly_chart(fig, width="stretch")

        left, right = st.columns(2)

        with left:
            st.markdown("#### Geographic distribution")
            frame = distribution_frame(distributions["geography"])
            fig = px.pie(
                frame, names="Category", values="People", hole=0.55,
            )
            fig.update_layout(
                height=340, paper_bgcolor="#FFFFFF",
                font_color="#243247", legend_title_text="Geography",
            )
            st.plotly_chart(fig, width="stretch")

        left, right = st.columns(2)

        with left:
            st.markdown("#### Age groups")
            frame = distribution_frame(distributions["age_group"])
            fig = px.bar(frame, x="Category", y="People", text="People")
            fig.update_layout(
                height=330, xaxis_tickangle=-25,
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font_color="#243247",
            )
            st.plotly_chart(fig, width="stretch")

        with right:
            st.markdown("#### Auditory functional status")
            frame = distribution_frame(distributions["functional_status"])
            fig = px.bar(
                frame, x="Category", y="People",
                color="Category", text="People",
            )
            fig.update_layout(
                height=330, xaxis_tickangle=-20, showlegend=False,
                paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
                font_color="#243247",
            )
            st.plotly_chart(fig, width="stretch")


# Relationships
with journeys_tab:
    st.subheader("Population household relationships")
    st.write(
        "Explore the simulated social network, including family, friendship "
        "and community connections. These relationships are illustrative "
        "simulation assumptions, not measured real-world relationships."
    )

    household_members = {}
    for agent in population.agents:
        if agent.household_id is not None:
            household_members.setdefault(agent.household_id, []).append(agent)

    household_ids = sorted(household_members)
    unique_connections = {
        (
            tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            ))),
            relationship.relationship_type,
        )
        for relationship in population.relationships
    }

    relationship_counts = {
        relationship_type: sum(
            1 for _, kind in unique_connections
            if kind == relationship_type
        )
        for relationship_type in ("family", "friend", "community")
    }

    connected_people = {
        relationship.agent_id
        for relationship in population.relationships
    }

    isolated_people = len(population.agents) - len(connected_people)

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Population", f"{len(population.agents):,}")
    metric2.metric("Households", f"{len(household_ids):,}")
    metric3.metric("People without connections", isolated_people)

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Family connections", relationship_counts["family"])
    metric2.metric("Friend connections", relationship_counts["friend"])
    metric3.metric("Community connections", relationship_counts["community"])

    household_options = ["All households"] + household_ids

    selected_household = st.selectbox(
        "Network view",
        household_options,
        format_func=lambda value: (
            value if value == "All households"
            else (
                f"{value} ({len(household_members[value])} "
                f"{'member' if len(household_members[value]) == 1 else 'members'})"
            )
        ),
    )

    if selected_household == "All households":
        st.markdown("#### Combined population household network")
        fig, connection_count = make_household_network(
            population.agents,
            population.relationships,
        )
        st.plotly_chart(fig, width="stretch")

        st.caption(
            f"Showing {len(population.agents):,} people across "
            f"{len(household_ids):,} households, with "
            f"{connection_count:,} unique social connections. "
            "Colours distinguish relationship types."
        )

        geography_counts = (
            pd.DataFrame([
                {
                    "Geography": agent.summary()["geography"].replace(
                        "_", " "
                    ).title()
                }
                for agent in population.agents
            ])
            ["Geography"].value_counts().rename_axis("Geography")
            .reset_index(name="People")
        )
        st.markdown("#### Population geography")
        st.dataframe(
            geography_counts,
            hide_index=True,
            width="stretch",
        )

    else:
        selected_members = household_members[selected_household]
        selected_member_ids = {
            agent.agent_id for agent in selected_members
        }

        st.markdown("#### Household relationship network")
        fig, connection_count = make_household_network(
            population.agents,
            population.relationships,
            selected_household,
        )
        st.plotly_chart(fig, width="stretch")

        st.caption(
            f"{len(selected_members)} household members | "
            f"{connection_count} unique family connections"
        )

        st.markdown("#### Household members")
        member_rows = [
            {
                "Participant": agent.agent_id,
                "Age group": agent.summary()["age_group"],
                "Measured hearing status": agent.summary()[
                    "measured_hearing_status"
                ],
                "Self-reported hearing status": agent.summary()[
                    "self_reported_hearing_status"
                ],
                "Auditory functional status": agent.summary()[
                    "auditory_functional_status"
                ],
                "Geography": agent.summary()["geography"],
            }
            for agent in selected_members
        ]
        st.dataframe(
            pd.DataFrame(member_rows),
            hide_index=True,
            width="stretch",
        )

        st.markdown("#### Recorded family connections")
        connection_rows = []
        seen_connections = set()

        for relationship in population.relationships:
            if (
                relationship.agent_id not in selected_member_ids
                or relationship.contact_id not in selected_member_ids
            ):
                continue

            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))
            if pair in seen_connections:
                continue
            seen_connections.add(pair)

            connection_rows.append({
                "Participant": relationship.agent_id,
                "Household member": relationship.contact_id,
                "Relationship": relationship.relationship_type.replace(
                    "_", " "
                ).title(),
                "Trust": relationship.trust,
                "Perceived support": relationship.perceived_support,
                "Interactions per month": relationship.interactions_per_month,
                "Status": relationship.status.replace("_", " ").title(),
            })

        if connection_rows:
            st.dataframe(
                pd.DataFrame(connection_rows),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info(
                "This household has no recorded connections. "
                "It may be a single-person household."
            )

    st.caption(
        "Social relationships are synthetic simulation assumptions. "
        "Trust, perceived support and interaction frequency are initial "
        "model values, not measured real-world characteristics."
    )

    st.divider()
    st.markdown("#### Individual social network")

    agent_ids = sorted(agent.agent_id for agent in population.agents)

    selected_agent_id = st.selectbox(
        "Select participant",
        agent_ids,
        key="individual_network_agent",
    )

    fig, connection_count, contact_count = make_individual_network(
        population.agents,
        population.relationships,
        selected_agent_id,
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        f"{selected_agent_id} has {contact_count} direct contacts and "
        f"{connection_count} unique connections shown. Connections between "
        "direct contacts are included where recorded."
    )
# Timeline and interactions
with journeys_tab:
    st.subheader("Individual experience over time")

    months = [snapshot["month"] for snapshot in snapshots]
    selected_month = st.slider(
        "Select simulation month",
        min_value=min(months),
        max_value=max(months),
        value=max(months),
        step=1,
    )

    selected_snapshot = next(
        snapshot for snapshot in snapshots
        if snapshot["month"] == selected_month
    )

    state = selected_snapshot["state"]

    st.markdown(f"#### Month {selected_month}")

    state_fields = [
        ("Communication confidence", "communication_confidence"),
        ("Trust in services", "trust_in_services"),
        ("Perceived support", "perceived_support"),
        ("Social participation", "social_participation"),
        ("Perceived loneliness", "perceived_loneliness"),
        ("Frustration", "frustration"),
    ]

    columns = st.columns(3)
    for index, (label, key) in enumerate(state_fields):
        columns[index % 3].metric(label, f"{state[key]:.2f}")

    state_rows = []
    for snapshot in snapshots:
        for label, key in state_fields:
            state_rows.append({
                "Month": snapshot["month"],
                "Measure": label,
                "Value": snapshot["state"][key],
            })

    state_frame = pd.DataFrame(state_rows)
    fig = px.line(
        state_frame,
        x="Month",
        y="Value",
        color="Measure",
        markers=True,
    )
    fig.update_layout(
        height=390,
        yaxis=dict(range=[0, 1], title="Modelled value"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font_color="#243247",
    )
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### Recorded interactions")

    event_rows = []
    for agent_id, events in histories.items():
        for event in events:
            details = event.get("additional_details", {})
            event_rows.append({
                "Month": event["month"],
                "Participant": agent_id,
                "Interaction": details.get("interaction_id", ""),
                "Event type": event["event_type"].replace("_", " ").title(),
                "Outcome": event["outcome"].replace("_", " ").title(),
                "Experience": outcome_group(event["outcome"]),
                "Message": event["actual_message"],
                "Interpretation": event["agent_interpretation"],
                "LLM": details.get("llm_interpretation", {}),
            })

    event_frame = pd.DataFrame(event_rows)
    visible_events = event_frame[event_frame["Month"] == selected_month]

    if visible_events.empty:
        st.info("No interaction records for this month.")
    else:
        participant_filter = st.selectbox(
            "Participant perspective",
            ["All participants"] + sorted(visible_events["Participant"].unique()),
        )

        if participant_filter != "All participants":
            visible_events = visible_events[
                visible_events["Participant"] == participant_filter
            ]

        for _, event in visible_events.iterrows():
            with st.expander(
                f"{event['Participant']} · {event['Interaction']} · "
                f"{event['Experience']}"
            ):
                st.write(f"**Event:** {event['Message']}")
                st.write(f"**Participant interpretation:** {event['Interpretation']}")
                st.write(f"**Outcome:** {event['Outcome']}")

                llm = event["LLM"]
                if llm.get("status") == "generated" and llm.get("text"):
                    st.write("**Local LLM interpretation (unverified):**")
                    st.write(llm["text"])
                    st.caption(
                        f"Model: {llm.get('model')} · "
                        "Model-generated, unverified; not used to change state."
                    )
                elif llm.get("status") == "failed":
                    st.caption("Local LLM interpretation failed for this record.")
                else:
                    st.caption("No local LLM interpretation was generated.")



    st.caption(
        "Monthly state values are recorded model outputs. Positive and negative "
        "labels describe the scenario's coded interaction outcomes, not clinical "
        "judgements or measured real-world effects."
    )


# Experiment runner
with experiment_tab:

    st.subheader("Configure and compare population scenarios")

    st.write(
        "Change the population and service assumptions, then compare "
        "baseline and mobile outreach using matching random seeds."
    )

    st.markdown("#### Population and simulation")

    col1, col2, col3 = st.columns(3)

    with col1:
        population_size = st.number_input(
            "Population size",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000,
            help="Number of synthetic people generated in each experiment.",
        )

    with col2:
        duration_months = st.number_input(
            "Simulation duration (months)",
            min_value=1,
            max_value=60,
            value=12,
            step=1,
        )

    with col3:
        repetitions = st.number_input(
            "Number of repetitions",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
            help="Each repetition uses a different sequential random seed.",
        )

    st.markdown("#### Population geography")

    geo1, geo2, geo3 = st.columns(3)

    with geo1:
        metropolitan_pct = st.slider(
            "Metropolitan (%)",
            min_value=0,
            max_value=100,
            value=55,
            step=1,
        )

    with geo2:
        regional_pct = st.slider(
            "Regional (%)",
            min_value=0,
            max_value=100 - metropolitan_pct,
            value=min(35, 100 - metropolitan_pct),
            step=1,
        )

    remote_pct = 100 - metropolitan_pct - regional_pct

    with geo3:
        st.metric("Remote / very remote (%)", remote_pct)

    st.caption(
        "The three geographical percentages always add up to 100%."
    )

    # Read configured service capacity and allocation defaults.
    with CONFIG.open("r", encoding="utf-8") as file:
        experiment_defaults = json.load(file)

    capacity_defaults = experiment_defaults["service_capacity"]
    allocation_defaults = experiment_defaults.get(
        "service_allocation",
        {},
    )

    workforce_defaults = capacity_defaults["workforce"]
    regional_defaults = capacity_defaults["regional_service"]

    appointment_minutes = int(
        workforce_defaults["appointment_duration_minutes"]
    )
    maximum_trips = int(
        regional_defaults["available_travel_hours_per_month"]
        // regional_defaults["round_trip_travel_hours"]
    )
    appointments_per_trip = int(
        regional_defaults["service_delivery_hours_per_trip"]
        * 60 // appointment_minutes
    )
    workforce_appointment_capacity = int(
        workforce_defaults["available_clinical_hours_per_month"]
        * 60 // appointment_minutes
    )
    maximum_appointments = min(
        maximum_trips * appointments_per_trip,
        workforce_appointment_capacity,
    )

    st.markdown("#### Service capacity")

    capacity_col1, capacity_col2, capacity_col3 = st.columns(3)

    with capacity_col1:
        planned_appointments = st.slider(
            "Planned appointments per month",
            min_value=0,
            max_value=maximum_appointments,
            value=min(
                int(regional_defaults["planned_appointments_per_month"]),
                maximum_appointments,
            ),
            step=1,
            help="Monthly appointment capacity, limited by travel, deployment and workforce availability.",
        )

    planned_trips = (
        (planned_appointments + appointments_per_trip - 1)
        // appointments_per_trip
        if planned_appointments > 0 else 0
    )

    planned_clinical_hours = (
        planned_appointments * appointment_minutes / 60
    )

    with capacity_col2:
        st.metric("Required trips per month", planned_trips)

    with capacity_col3:
        st.metric(
            "Planned clinical hours per month",
            f"{planned_clinical_hours:g}",
        )

    st.caption(
        f"Each trip supports up to {appointments_per_trip} appointments. "
        f"Maximum monthly capacity: {maximum_appointments} appointments. "
        "Trips and clinical hours are calculated automatically."
    )

    st.markdown("#### Service allocation policy")

    allocation_policy_options = [
        "first_come_first_served",
        "need_based",
        "random",
    ]

    allocation_policy_labels = {
        "first_come_first_served": "First come, first served",
        "need_based": "Need-based",
        "random": "Random",
    }

    allocation_policy = st.selectbox(
        "Allocation policy",
        options=allocation_policy_options,
        index=allocation_policy_options.index(
            allocation_defaults.get(
                "policy",
                "first_come_first_served",
            )
        ),
        format_func=lambda value: allocation_policy_labels[value],
        help=(
            "Determines how eligible service requests are prioritised "
            "when available appointments are limited."
        ),
    )

    if allocation_policy == "need_based":
        st.caption(
            "Priority: confirmed functional difficulty, reported "
            "difficulty, unknown status, then no identified difficulty. "
            "This is an illustrative simulation assumption, not "
            "a clinically validated triage rule."
        )

    st.markdown("#### Service demand and attendance")

    col1, col2 = st.columns(2)

    with col1:
        demand_probability = st.slider(
            "Annual service request probability",
            min_value=0.0,
            max_value=1.0,
            value=0.07,
            step=0.01,
            help="Configured probability used by the service-demand generator.",
        )

    with col2:
        attendance_probability = st.slider(
            "Appointment attendance probability",
            min_value=0.0,
            max_value=1.0,
            value=0.80,
            step=0.01,
            help="Probability that a person attends an allocated appointment.",
        )

    st.markdown("#### Reproducibility")

    base_seed = st.number_input(
        "Starting random seed",
        min_value=0,
        max_value=2147483647,
        value=42,
        step=1,
    )

    st.caption(
        "Baseline and intervention experiments use the same sequence of "
        "random seeds. This supports paired scenario comparisons."
    )

    st.markdown("#### Configuration summary")

    st.dataframe(
        pd.DataFrame([
            {"Parameter": "Population size", "Value": population_size},
            {"Parameter": "Duration (months)", "Value": duration_months},
            {"Parameter": "Metropolitan (%)", "Value": metropolitan_pct},
            {"Parameter": "Regional (%)", "Value": regional_pct},
            {"Parameter": "Remote / very remote (%)", "Value": remote_pct},
            {"Parameter": "Annual demand probability", "Value": demand_probability},
            {"Parameter": "Attendance probability", "Value": attendance_probability},
            {"Parameter": "Planned trips per month", "Value": planned_trips},
            {"Parameter": "Planned appointments per month", "Value": planned_appointments},
            {"Parameter": "Planned clinical hours per month", "Value": planned_clinical_hours},
            {"Parameter": "Starting random seed", "Value": base_seed},
            {"Parameter": "Repetitions per scenario", "Value": repetitions},
        ]),
        use_container_width=True,
        hide_index=True,
    )

    if st.button(
        "Run baseline and intervention comparison",
        type="primary",
    ):
        temporary_config_path = None

        try:
            with CONFIG.open("r", encoding="utf-8") as file:
                experiment_config = json.load(file)

            experiment_config["population"]["size"] = int(population_size)

            experiment_config["population"]["geography"] = {
                "metropolitan": int(metropolitan_pct),
                "regional": int(regional_pct),
                "remote_very_remote": int(remote_pct),
            }

            experiment_config["simulation"]["duration_months"] = int(
                duration_months
            )

            experiment_config["simulation"]["random_seed"] = int(base_seed)

            experiment_config["demand"]["annual_request_probability"] = (
                float(demand_probability)
            )

            experiment_config["attendance"]["attendance_probability"] = (
                float(attendance_probability)
            )

            regional_service = experiment_config["service_capacity"][
                "regional_service"
            ]
            regional_service["planned_trips_per_month"] = int(planned_trips)
            regional_service["planned_appointments_per_month"] = int(
                planned_appointments
            )
            regional_service["planned_clinical_hours_per_month"] = float(
                planned_clinical_hours
            )

            # Keep the temporary file beside the original configuration.
            # This preserves the relative country-profile path.
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                prefix=".dashboard_experiment_",
                dir=CONFIG.parent,
                encoding="utf-8",
                delete=False,
            ) as temporary_file:
                json.dump(experiment_config, temporary_file, indent=4)
                temporary_config_path = Path(temporary_file.name)

            with st.spinner(
                f"Running {int(repetitions) * 2} population experiments..."
            ):
                baseline_runs = run_population_experiment_repetitions(
                    str(temporary_config_path),
                    str(DISTRIBUTION),
                    repetitions=int(repetitions),
                    base_seed=int(base_seed),
                )

                intervention_runs = run_population_experiment_repetitions(
                    str(temporary_config_path),
                    str(DISTRIBUTION),
                    str(INTERVENTION),
                    repetitions=int(repetitions),
                    base_seed=int(base_seed),
                )

                st.session_state["experiment_comparison"] = (
                    compare_population_experiments(
                        baseline_runs,
                        intervention_runs,
                    )
                )

                st.session_state["experiment_parameters"] = {
                    "population_size": int(population_size),
                    "duration_months": int(duration_months),
                    "metropolitan_pct": int(metropolitan_pct),
                    "regional_pct": int(regional_pct),
                    "remote_pct": int(remote_pct),
                    "demand_probability": float(demand_probability),
                    "attendance_probability": float(attendance_probability),
                    "planned_trips_per_month": int(planned_trips),
                    "planned_appointments_per_month": int(planned_appointments),
                    "planned_clinical_hours_per_month": float(
                        planned_clinical_hours
                    ),
                    "base_seed": int(base_seed),
                    "repetitions": int(repetitions),
                }

            st.success("Experiment comparison completed.")

        except Exception as error:
            st.error(f"The experiment comparison failed: {error}")

        finally:
            if temporary_config_path is not None:
                temporary_config_path.unlink(missing_ok=True)

    comparison = st.session_state.get("experiment_comparison")
    if comparison:
        baseline_results = comparison["baseline"]["metrics"]
        intervention_results = comparison["intervention"]["metrics"]
        differences = comparison[
            "paired_differences_intervention_minus_baseline"
        ]

        st.markdown("#### Scenario comparison")
        st.caption(
            f"{comparison['baseline']['run_count']} repetitions per scenario "
            f"· Seeds {comparison['baseline']['seeds'][0]} to "
            f"{comparison['baseline']['seeds'][-1]}"
        )

        metric_names = [
            "total_demands",
            "allocated",
            "unallocated",
            "attendance.attended",
            "attendance.did_not_attend",
            "delivery_outcomes.delivered",
            "delivery_outcomes.not_delivered",
        ]
        available_metrics = [
            name for name in metric_names
            if name in baseline_results and name in intervention_results
        ]

        comparison_rows = []
        for name in available_metrics:
            comparison_rows.append({
                "Measure": name.replace(".", " · ").replace("_", " ").title(),
                "Baseline mean": baseline_results[name]["mean"],
                "Intervention mean": intervention_results[name]["mean"],
                "Paired difference": differences[name]["mean"],
                "Difference SD": differences[name]["standard_deviation"],
            })

        st.dataframe(
            pd.DataFrame(comparison_rows),
            use_container_width=True,
            hide_index=True,
        )

        selected_metric = st.selectbox(
            "Visualise outcome",
            available_metrics,
            format_func=lambda value: (
                value.replace(".", " · ").replace("_", " ").title()
            ),
        )

        chart_data = pd.DataFrame([
            {
                "Scenario": "Baseline",
                "Mean": baseline_results[selected_metric]["mean"],
                "Standard deviation": baseline_results[selected_metric][
                    "standard_deviation"
                ],
            },
            {
                "Scenario": "Mobile hearing outreach",
                "Mean": intervention_results[selected_metric]["mean"],
                "Standard deviation": intervention_results[selected_metric][
                    "standard_deviation"
                ],
            },
        ])

        st.bar_chart(
            chart_data.set_index("Scenario")[["Mean"]]
        )

        st.dataframe(
            chart_data,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("#### Interpretation")
        st.write(
            "The paired difference is the intervention outcome minus the "
            "baseline outcome for each matching seed, averaged across runs. "
            "Standard deviations describe variation between simulated runs."
        )
        st.warning(
            "These are simulated results under illustrative assumptions. "
            "They do not establish real-world effectiveness or statistical "
            "significance."
        )
    else:
        st.info(
            "Set the repetition count and starting seed, then run the "
            "comparison to see results here."
        )


# Research exploration
with analytics_tab:
    st.subheader("Explore a research question")

    question = st.selectbox(
        "Research question",
        [
            "How are hearing profiles distributed across the population?",
            "How does geography relate to the simulated population?",
            "What service demand and delivery outcomes are recorded?",
            "What changes across the selected intervention scenario?",
        ],
    )

    st.markdown("#### Current scenario")
    st.write(
        "The selected population scenario is **"
        + scenario
        + "**."
    )

    st.info(
        "This first dashboard version runs the configured baseline or mobile "
        "outreach scenario and reports its actual outputs. It does not yet "
        "translate arbitrary free-text questions into new model parameters."
    )

    st.markdown("#### Experiment definition")
    st.write(f"Experiment: {summary['experiment_id']}")
    st.write(f"Population configuration: {summary['distribution_profile_id']}")
    st.write(f"Random seed: {summary['random_seed']}")
    st.write(f"Evidence status: {summary['evidence_status']}")

    if summary["intervention"]:
        st.write(f"Intervention: {summary['intervention']['name']}")
        st.write(
            f"Intervention evidence status: "
            f"{summary['intervention']['evidence_status']}"
        )
    else:
        st.write("Intervention: None (baseline)")


st.markdown("""
<div class="credit">
    Designed and developed by Jorge Mejia<br>
    Health and Wellbeing Population Simulator · Research and Experimental Platform
</div>
""", unsafe_allow_html=True)
