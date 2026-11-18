# Health and Wellbeing Population Simulator

A configurable, agent-based simulation framework for exploring how people interact, communicate, experience health and wellbeing needs, seek support, and navigate services over time.

## Overview

The Health and Wellbeing Population Simulator is a research, educational and scenario-exploration project. It uses synthetic individuals (agents) to explore how personal circumstances, communication, social relationships, health and wellbeing needs, access to services, funding arrangements and interventions may interact over time.

The simulator is designed to be country-agnostic. Country profiles can provide reference settings for population characteristics, geographical contexts, healthcare systems, funding arrangements, service capacity and policy environments.

Simulated populations are hypothetical. They are not representations or estimates of actual populations unless a model has been explicitly calibrated and validated for that purpose.

The project aims to support structured exploration of questions such as:

- How do individual circumstances and experiences influence communication and interaction?
- How might communication barriers affect relationships, participation and access to support?
- How do people recognise needs, seek help and navigate available services?
- How might geographical barriers, workforce availability and service capacity affect access?
- How do funding arrangements and personal contributions influence access to care?
- How could changes to services, technology, community support or policy affect individual and population outcomes?
- How might outcomes differ across population groups and geographical settings?

The project is under active development.

## Foundational model: communication and human interaction

Communication and human interaction provide a foundation for modelling how individuals exchange information, interpret events, respond to other people and develop experiences over time.

The model treats each agent as an individual with its own circumstances, state, history, perspective and decision-making processes.

### Agent interaction cycle

The event-driven communication model is designed around an independent, multi-step interaction:

1. An agent independently decides whether to initiate an interaction.
2. The local LLM generates the initiating agent's message using that agent's own state and relevant history.
3. The receiving agent interprets the message using its own context and perspective.
4. The receiving agent independently decides whether and how to respond.
5. The LLM generates the response using the responding agent's own context and the message it received.
6. The original initiating agent interprets the response from its own perspective.
7. Each participant's experience is recorded separately in their individual memory.

The LLM supports natural-language generation and interpretation. Statistical and rule-based simulation logic remains responsible for decisions, validated experience assessment and numerical changes to agent states and relationships.

An LLM interpretation is not proof of comprehension, agreement or a successful communication outcome.

### Individual memory and social relationships

Each agent maintains an individual interaction history. The memory model distinguishes between:

- Messages received and messages sent
- The agent's own interpretation of received messages
- The other participant's response, where available
- Interaction timing and evidence status

Participants do not share a single interpretation of an interaction. Each agent's record represents its own perspective.

Social relationships are represented separately from individual memories. The longer-term model is intended to explore how repeated interactions and experiences may influence relationships, create new connections and change social support networks over time.

### From individual experiences to population outcomes

The intended model connects individual experiences and decisions with broader population patterns, including:

- Health and wellbeing needs
- Communication and social participation
- Help-seeking and support-seeking behaviour
- Access to services and interventions
- Service availability and workforce capacity
- Funding and affordability
- Individual and population-level outcomes

These areas represent the broader direction of development. Existing implementation and future extensions must remain clearly distinguished.

**Implemented foundations**

- Synthetic population and individual agent profiles
- Individual state and memory representations
- Independent interaction and response decisions
- Local LLM message generation and recipient interpretation
- Event-driven interaction recording
- Separate memory records for each participant
- Population, service, funding and intervention modelling components

**Further development**

- Evidence-based assessment of individual communication experiences
- Validated emotional and experiential responses
- Controlled updates to agent states and relationship attributes
- Dynamic social network growth and change
- More general health and wellbeing needs and support pathways
- Longitudinal analysis of help-seeking, service access and population outcomes
- Feedback between simulation findings and intervention scenarios

These capabilities will be developed incrementally. The intended architecture is broader than the currently implemented model.

## Research and modelling principles

The simulator follows several important principles.

### Individual needs, support and outcomes are distinct

The model should distinguish between:

- Recognition or identification of a need
- An individual's preferences and goals
- Eligibility for available support
- Access to assessment and services
- Suitability of recommended support
- Acceptance or decline of support
- Acquisition or receipt of support
- Actual use and engagement
- Functional effectiveness
- Individual satisfaction
- Longer-term individual outcomes

Access does not automatically imply that support is appropriate or effective. Receiving support does not automatically mean that it is used or beneficial.

### Communication is not determined by a single personal characteristic

An individual's communication experience cannot be reliably inferred from one characteristic or classification.

The model should distinguish personal preferences, capabilities, requirements, environmental conditions, observed events and reported experiences.

### Unknown information remains unknown

Missing information is not automatically interpreted as a negative outcome or absence of need.

The model should distinguish between information that is known, unknown, not assessed, not applicable or declined.

### Evidence and assumptions are distinguished

Model information and relationships should be classified using evidence-status concepts, including:

- Evidence-supported
- Simulation assumption
- Not yet established

Synthetic population characteristics and illustrative assumptions must not be interpreted as measured population estimates.

### Individual and population outcomes remain distinct

Population-level patterns should not be used to assume an individual's needs, preferences, experiences or outcomes. Individual records and aggregate results must preserve their respective evidence and limitations.

## Country configuration

The project includes an initial country-profile configuration layer.

The initial reference profile is:

`config/countries/australia_reference.json`

It records basic configuration information, including:

- Country identity and profile type
- Evidence status
- Currency
- Funding pathways
- Geographic service contexts
- Configuration notes

The country profile is currently loaded by the population experiment runner and its identifying information is included in the experiment summary.

**Important:** The country profile is a foundation for future configurability. It does not yet control every population, funding, policy or service-delivery parameter. Country-specific rules and assumptions require further implementation and evidence.

Country-specific evidence and simulation assumptions must remain distinguishable.

## Main components

| Component | Purpose |
|---|---|
| Population | Generates synthetic individuals and integrates population records. |
| Agents | Represents individual profiles, states, relationships and memory. |
| Communication | Models communication environments, events and interaction experiences. |
| Behaviour | Represents individual decisions, experiences and relationship changes. |
| Support pathways | Represents support needs, funding arrangements, service access and individual pathways. |
| Service capacity | Represents workforce, geographical access, costs, funding and operational capacity. |
| Service delivery | Models service demand, allocation, assessment and delivery. |
| Interventions | Loads and represents configurable interventions. |
| Country configuration | Loads and validates country reference profiles. |
| Simulation | Runs longitudinal demonstrations and population experiments. |

## Optional local language-model integration

The project includes an experimental local LLM module for communication generation and interpretation.

It uses Ollama to access a locally installed language model.

Current characteristics:

- LLM integration is optional.
- The current default model is `qwen3:1.7b`.
- Individual participant requests are handled separately.
- Generated interpretations are explicitly marked as unverified.
- LLM output does not directly modify authoritative agent states, relationships, clinical status or simulation outcomes.
- The simulation remains controlled by Python logic.

The LLM integration is experimental. Structurally valid model output should not be interpreted as factually or clinically validated.

Language interpretation remains separate from authoritative simulation logic. AI may assist with interpreting messages and explaining results, but it must not invent simulation outcomes or silently change model parameters.

## Technology

- Python 3.11+
- SQLite for simulation memory and event storage
- `pytest` for automated testing
- Ollama for optional local language-model experimentation

## Project structure

```text
Health_and_Wellbeing_Population_Simulator/
├── config/
│   ├── countries/
│   ├── interventions/
│   └── population and experiment configurations
├── dashboard/
├── documentation/
├── outputs/
├── src/
│   ├── agents/
│   ├── behaviour/
│   ├── communication/
│   ├── interventions/
│   ├── population/
│   ├── service_capacity/
│   ├── service_delivery/
│   └── simulation/
└── tests/
```

The source tree contains additional implementation modules and domain-specific components that will be generalised incrementally.

## Installation

Clone the repository:

```bash
git clone git@github.com:Olynmpus/Health_and_Wellbeing_Population_Simulator.git
cd Health_and_Wellbeing_Population_Simulator
```

Create a virtual environment:

```bash
python3.11 -m venv .venv
```

Activate it on Linux or WSL:

```bash
source .venv/bin/activate
```

Install the test dependency:

```bash
python -m pip install pytest
```

## Running the tests

From the project root:

```bash
python -m pytest -q
```

The automated test suite covers population generation, agents, communication, relationships, support pathways, funding, service access, service capacity, service delivery, interventions, country configuration and simulation integration.

## Running the longitudinal demonstration

The longitudinal demonstration can be started with:

```bash
python -m src.simulation.longitudinal_demo
```

By default, the demonstration writes to:

```text
outputs/HH-EXP-001-longitudinal-demo-v2.db
```

The application protects existing databases and stops if the selected output database already exists. Use a new output path when running another experiment rather than overwriting previous results.

## Development status

The project is actively evolving. The current implementation provides population, service and interaction foundations. Broader health and wellbeing domains, evidence-based experience assessment and integrated longitudinal outcomes remain areas for further development.
