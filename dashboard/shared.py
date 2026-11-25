from pathlib import Path
import tempfile
import uuid

import streamlit as st

from src.simulation.longitudinal_demo import run_experiment
from src.simulation.population_experiment import run_population_experiment


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "HH-EXP-001.json"
DISTRIBUTION = ROOT / "config" / "population_australia_2025.json"
INTERVENTION = (
    ROOT / "config" / "interventions" / "mobile_hearing_outreach.json"
)


@st.cache_resource(show_spinner="Running four-month interaction experiment...")
def load_longitudinal(enable_llm):
    database_path = (
        Path(tempfile.gettempdir())
        / f"hearing_dashboard_{uuid.uuid4().hex}.db"
    )
    return run_experiment(database_path, enable_llm=enable_llm)


@st.cache_resource(show_spinner="Loading synthetic population...")
def load_population(use_intervention=False):
    intervention_path = str(INTERVENTION) if use_intervention else None

    return run_population_experiment(
        str(CONFIG),
        str(DISTRIBUTION),
        intervention_path,
    )
