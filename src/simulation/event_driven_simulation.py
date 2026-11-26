"""Event-driven simulation of autonomous agent interactions."""

import random
from datetime import datetime, timedelta
from src.agents.memory_store import MemoryStore
from src.simulation.event_model import SimulationEvent
from src.behaviour.decision_model import choose_action
from src.behaviour.llm_interpreter import (
    generate_message,
    interpret_recipient_message,
    assess_communication_experience,
    MessageGenerationResult,
)
from src.behaviour.communication_model import (
    CommunicationEvent,
    CommunicationEnvironment,
)
from src.behaviour.communication_assessment import (
    assess_acoustic_conditions,
    assess_visual_support,
)

class EventDrivenSimulation:
    """Run a reproducible, event-driven simulation using a population."""

    def __init__(
        self,
        experiment,
        start_time=None,
        random_seed=None,
        memory_path="outputs/event_simulation_memory.db",
        contextual_opportunities=None,
    ):
        self.agents = {
            agent.agent_id: agent
            for agent in experiment.agents
        }

        self.relationships = experiment.relationships
        self.contextual_opportunities = contextual_opportunities or []

        seed = (
            random_seed
            if random_seed is not None
            else experiment.random_seed
        )

        self.random_seed = seed
        self.rng = random.Random(seed)

        self.start_time = start_time or datetime(2026, 1, 1)
        self.current_time = self.start_time
        self.events = []
        self.next_event_id = 1
        self.memory = MemoryStore(memory_path)
        self.opportunity_schedule = {}
        self.schedule_initialised = False

    def advance_time(self, hours=1):
        """Advance the simulated clock by a number of hours."""

        if hours < 0:
            raise ValueError("Time cannot move backwards.")

        self.current_time += timedelta(hours=hours)

        return self.current_time

    def generate_communication_environment(self):
        """Generate illustrative environmental conditions for an exchange."""

        environment = CommunicationEnvironment(
            background_noise=self.rng.uniform(0.0, 0.6),
            distance_metres=self.rng.uniform(0.5, 5.0),
            speaker_face_visible=self.rng.choice([True, False]),
            written_information_available=self.rng.choice([True, False]),
        )

        environment.validate()

        return environment

    def schedule_next_opportunity(self, relationship):
        """Calculate the next contact opportunity for a relationship."""

        if relationship.interactions_per_month < 0:
            raise ValueError(
                "Interaction frequency cannot be negative."
            )

        if relationship.interactions_per_month == 0:
            return None

        mean_interval_days = (
            30.44 / relationship.interactions_per_month
        )

        interval_days = self.rng.expovariate(
            1 / mean_interval_days
        )

        return self.current_time + timedelta(days=interval_days)

    def schedule_next_contextual_opportunity(self, opportunity):
        """Calculate the next random contact opportunity for a contextual encounter."""

        interactions_per_month = opportunity.get("interactions_per_month", 0)

        if interactions_per_month < 0:
            raise ValueError("Interaction frequency cannot be negative.")

        if interactions_per_month == 0:
            return None

        mean_interval_days = 30.44 / interactions_per_month
        interval_days = self.rng.expovariate(1 / mean_interval_days)

        return self.current_time + timedelta(days=interval_days)

    def initialise_opportunity_schedule(self):
        """Schedule the first contact opportunity for relationships and contextual encounters."""

        self.opportunity_schedule = {}

        # Schedule relationship-based opportunities.
        for relationship in self.get_interaction_opportunities():
            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))

            next_time = self.schedule_next_opportunity(relationship)

            if next_time is not None:
                self.opportunity_schedule[pair] = next_time

        # Schedule contextual opportunities independently.
        for index, opportunity in enumerate(self.contextual_opportunities):
            valid_opportunities = self.get_interaction_opportunities(
                [opportunity]
            )

            if opportunity not in valid_opportunities:
                continue

            next_time = self.schedule_next_contextual_opportunity(
                opportunity
            )

            if next_time is not None:
                contextual_key = (
                    "__contextual_opportunity__",
                    index,
                )
                self.opportunity_schedule[contextual_key] = next_time

        self.schedule_initialised = True
        return self.opportunity_schedule

    def get_next_scheduled_opportunity(self):
        """Return the earliest scheduled relationship opportunity."""

        if not self.opportunity_schedule:
            return None

        pair = min(
            self.opportunity_schedule,
            key=self.opportunity_schedule.get,
        )

        return pair, self.opportunity_schedule[pair]

    def process_next_opportunity(self):
        """Process the next scheduled relationship or contextual opportunity."""

        scheduled = self.get_next_scheduled_opportunity()

        if scheduled is None:
            return []

        key, scheduled_time = scheduled
        self.current_time = scheduled_time

        del self.opportunity_schedule[key]

        # Process a contextual encounter.
        if key[0] == "__contextual_opportunity__":
            index = key[1]
            opportunity = self.contextual_opportunities[index]

            events = self.run_interaction_cycle(opportunity)

            next_time = self.schedule_next_contextual_opportunity(
                opportunity
            )

            if next_time is not None:
                self.opportunity_schedule[key] = next_time

            return events

        # Process a relationship-based encounter.
        pair = key

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == pair[0]
                and item.contact_id == pair[1]
                and item.status == "active"
            ),
            None,
        )

        if relationship is None:
            relationship = next(
                (
                    item for item in self.relationships
                    if item.agent_id == pair[1]
                    and item.contact_id == pair[0]
                    and item.status == "active"
                ),
                None,
            )

        if relationship is None:
            return []

        events = self.run_interaction_cycle(relationship)

        next_time = self.schedule_next_opportunity(relationship)

        if next_time is not None:
            self.opportunity_schedule[pair] = next_time

        return events

    def run_until(self, end_time):
        """Process scheduled opportunities until the specified end time."""

        if end_time < self.current_time:
            raise ValueError("End time cannot be before current time.")

        if not self.schedule_initialised:
            self.initialise_opportunity_schedule()

        while True:
            scheduled = self.get_next_scheduled_opportunity()

            if scheduled is None:
                break

            _, scheduled_time = scheduled

            if scheduled_time > end_time:
                break

            self.process_next_opportunity()

        self.current_time = end_time

        return self.events

    def record_event(self, event):
        """Validate and record a simulation event."""

        event.validate()
        self.events.append(event)

        self.next_event_id += 1

        return event

    def get_interaction_opportunities(
        self,
        contextual_opportunities=None,
    ):
        """Return relationship-based and supplied contextual opportunities."""

        opportunities = []
        seen_pairs = set()

        for relationship in self.relationships:
            if relationship.status != "active":
                continue

            if (
                relationship.agent_id not in self.agents
                or relationship.contact_id not in self.agents
            ):
                continue

            pair = tuple(sorted((
                relationship.agent_id,
                relationship.contact_id,
            )))

            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)
            opportunities.append(relationship)

        for opportunity in contextual_opportunities or []:
            agent_id = opportunity["agent_id"]
            contact_id = opportunity["contact_id"]

            if (
                agent_id not in self.agents
                or contact_id not in self.agents
                or agent_id == contact_id
            ):
                continue

            opportunities.append(opportunity)

        return opportunities

    def build_agent_context(
        self,
        agent_id,
        other_agent_id,
        relationship,
        interaction_context=None,
    ):
        """Build private context for one agent's interaction perspective."""

        agent = self.agents[agent_id]
        other_agent = self.agents[other_agent_id]
        relationship_context = None
        return {
            "agent": {
                "agent_id": agent.agent_id,
                "profile": {
                    "age_group": agent.profile.age_group,
                    "hearing_profile": agent.profile.hearing_profile,
                    "auditory_functional_status": (
                        agent.profile.auditory_functional_status
                    ),
                    "geography": agent.profile.geography,
                    "role": agent.profile.role,
                    "communication_profile": (
                        agent.profile.communication_profile.to_dict()
                    ),
                },
                "state": {
                    "communication_confidence": (
                        agent.state.communication_confidence
                    ),
                    "trust_in_services": agent.state.trust_in_services,
                    "perceived_support": agent.state.perceived_support,
                    "help_seeking_intention": (
                        agent.state.help_seeking_intention
                    ),
                    "social_participation": (
                        agent.state.social_participation
                    ),
                    "perceived_loneliness": (
                        agent.state.perceived_loneliness
                    ),
                    "frustration": agent.state.frustration,
                },
                "recent_communication_demand": (
                    self.assess_recent_communication_demand(agent_id)
                ),
                "recent_history": self.memory.get_history(agent_id)[-3:],
            },
            "other_participant": {
                "agent_id": other_agent.agent_id,
                "role": other_agent.profile.role,
            },
            "relationship": relationship_context,
            "interaction_context": interaction_context,
            "simulation_time": self.current_time.isoformat(),
        }

    def build_recipient_interpretation_context(
        self,
        agent_id,
        other_agent_id,
        relationship,
        interaction_context=None,
    ):
        """Build interpretation context without demographic or hearing labels."""

        context = self.build_agent_context(
            agent_id,
            other_agent_id,
            relationship,
            interaction_context,
        )
        agent_context = context.get("agent", {})
        profile = agent_context.get("profile", {})

        if isinstance(profile, dict):
            profile.pop("age_group", None)
            profile.pop("hearing_profile", None)
            profile.pop("auditory_functional_status", None)

        return context

    def generate_initiation_message(self, initiation_event):
        """Generate the initiating agent's message using private context."""

        speaker_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != speaker_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.status == "active"
                and (
                    (
                        item.agent_id == speaker_id
                        and item.contact_id == recipient_id
                    )
                    or (
                        item.agent_id == recipient_id
                        and item.contact_id == speaker_id
                    )
                )
            ),
            None,
        )



        context = self.build_agent_context(
            speaker_id,
            recipient_id,
            relationship,
            initiation_event.decision_basis.get(
                "interaction_context"
            ),
        )

        return generate_message(
            agent_id=speaker_id,
            interaction_context=context,
        )

    def interpret_initiation_message(self, initiation_event, message):
        """Interpret an incoming message from the recipient's perspective."""

        sender_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != sender_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.status == "active"
                and (
                    (
                        item.agent_id == sender_id
                        and item.contact_id == recipient_id
                    )
                    or (
                        item.agent_id == recipient_id
                        and item.contact_id == sender_id
                    )
                )
            ),
            None,
        )


        context = self.build_recipient_interpretation_context(
            recipient_id,
            sender_id,
            relationship,
            initiation_event.decision_basis.get(
                "interaction_context"
            ),
        )

        # Add environmental conditions when they are available.
        environment = getattr(
            self,
            "_current_communication_environment",
            None,
        )

        if environment is not None:
            context["communication_environment"] = {
                "background_noise": environment.background_noise,
                "distance_metres": environment.distance_metres,
                "speaker_face_visible": environment.speaker_face_visible,
                "written_information_available": (
                    environment.written_information_available
                ),
                "message_clarity": environment.message_clarity,
            }

        return interpret_recipient_message(
            recipient_id=recipient_id,
            message=message,
            interaction_context=context,
        )

    def prepare_initiation_communication(self, initiation_event):
        """Generate and interpret the initiating communication."""

        generated = self.generate_initiation_message(initiation_event)

        if generated.status != "generated" or not generated.text:
            initiation_event.decision_basis["message_generation"] = {
                "status": generated.status,
                "model": generated.model,
                "error": generated.error,
            }
            return False

        # Generate the environment before interpreting the message.
        environment = self.generate_communication_environment()
        self._current_communication_environment = environment

        sender_id = initiation_event.initiating_agent_id
        recipient_id = next(
            participant
            for participant in initiation_event.participants
            if participant != sender_id
        )

        communication = CommunicationEvent(
            speaker_id=sender_id,
            listener_id=recipient_id,
            intended_message=generated.text,
            perceived_message=None,
            listener_interpretation=None,
            environment=environment,
        )

        interpreted = self.interpret_initiation_message(
            initiation_event,
            generated.text,
        )

        if interpreted.status == "interpreted":
            communication.perceived_message = interpreted.perceived_message
            communication.listener_interpretation = (
                interpreted.interpretation
            )

        initiation_event.communication = communication

        initiation_event.decision_basis["message_generation"] = {
            "status": generated.status,
            "model": generated.model,
        }
        initiation_event.decision_basis["recipient_interpretation"] = {
            "status": interpreted.status,
            "model": interpreted.model,
            "comprehension_assessment": (
                interpreted.comprehension_assessment
            ),
            "error": interpreted.error,
            "evidence_status": "llm_interpretation_not_verified",
        }

        return True

    def make_initiation_decision(self, opportunity=None):
        """Select an interaction opportunity and decide whether to initiate."""

        if opportunity is None:
            opportunities = self.get_interaction_opportunities()

            if not opportunities:
                return None

            opportunity = self.rng.choice(opportunities)

        if isinstance(opportunity, dict):
            agent_id = opportunity["agent_id"]
            opportunity_contact_id = opportunity["contact_id"]
            interaction_context = opportunity.get("context")
        else:
            agent_id = opportunity.agent_id
            opportunity_contact_id = opportunity.contact_id
            interaction_context = None

        participants = [
            agent_id,
            opportunity_contact_id,
        ]

        initiating_agent_id = self.rng.choice(participants)
        contact_id = next(
            participant
            for participant in participants
            if participant != initiating_agent_id
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == initiating_agent_id
                and item.contact_id == contact_id
                and item.status == "active"
            ),
            None,
        )

        decision = choose_action(
            agent=self.agents[initiating_agent_id],
            available_actions=[
                "initiate_conversation",
                "avoid_interaction",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="initiation",
        )

        return {
            "initiating_agent_id": initiating_agent_id,
            "contact_id": contact_id,
            "relationship": relationship,
            "interaction_context": interaction_context,
            "decision": decision,
        }

    def run_initiation_event(self, opportunity=None):
        """Record a communication initiation when an agent chooses to initiate."""

        result = self.make_initiation_decision(opportunity)

        if result is None:
            return None

        decision = result["decision"]

        if decision["action"] != "initiate_conversation":
            return None

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="communication_initiation",
            participants=[
                result["initiating_agent_id"],
                result["contact_id"],
            ],
            initiating_agent_id=result["initiating_agent_id"],
            action=decision["action"],
            decision_basis={
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
                "interaction_context": result["interaction_context"],
            },
            description="An agent initiated a conversation.",
        )

        return self.record_event(event)

    def make_clarification_decision(self, initiation_event):
        """Let the recipient independently decide whether to clarify."""

        if initiation_event.event_type != "communication_initiation":
            raise ValueError(
                "A communication initiation event is required."
            )

        communication = initiation_event.communication

        if communication is None:
            raise ValueError(
                "Initiation communication is required."
            )

        recipient_id = communication.listener_id
        speaker_id = communication.speaker_id

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == recipient_id
                and item.contact_id == speaker_id
                and item.status == "active"
            ),
            None,
        )

        communication_context = initiation_event.decision_basis.get(
            "recipient_interpretation",
            {},
        )

        decision = choose_action(
            agent=self.agents[recipient_id],
            available_actions=[
                "attempt_clarification",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="clarification",
            communication_context=communication_context,
        )

        communication.clarification_requested = (
            decision["action"] == "attempt_clarification"
        )

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="clarification_decision",
            participants=[speaker_id, recipient_id],
            initiating_agent_id=recipient_id,
            action=decision["action"],
            decision_basis={
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
                "evidence_status": "simulation_assumption",
                "interaction_context": initiation_event.decision_basis.get(
                    "interaction_context"
                ),
            },
            description=(
                "The recipient decided whether to request clarification."
            ),
        )

        return self.record_event(event)

    def make_repair_decision(self, initiation_event):
        """Let the original speaker independently choose a repair action."""

        if initiation_event.event_type != "communication_initiation":
            raise ValueError(
                "A communication initiation event is required."
            )

        communication = initiation_event.communication

        if communication is None:
            raise ValueError(
                "Initiation communication is required."
            )

        if not communication.clarification_requested:
            return None

        speaker_id = communication.speaker_id
        recipient_id = communication.listener_id

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == speaker_id
                and item.contact_id == recipient_id
                and item.status == "active"
            ),
            None,
        )

        decision = choose_action(
            agent=self.agents[speaker_id],
            available_actions=[
                "repeat_information",
                "rephrase_information",
                "provide_written_information",
                "decline_repair",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="repair",
        )

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="repair_decision",
            participants=[speaker_id, recipient_id],
            initiating_agent_id=speaker_id,
            action=decision["action"],
            decision_basis={
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
                "evidence_status": "simulation_assumption",
            },
            description=(
                "The original speaker decided how to respond "
                "to the clarification request."
            ),
        )

        return self.record_event(event)

    def generate_repair_message(self, initiation_event, repair_event):
        """Generate the original speaker's repair message."""

        communication = initiation_event.communication
        speaker_id = communication.speaker_id
        recipient_id = communication.listener_id

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == speaker_id
                and item.contact_id == recipient_id
                and item.status == "active"
            ),
            None,
        )
        context = self.build_agent_context(
            speaker_id,
            recipient_id,
            relationship,
            initiation_event.decision_basis.get(
                "interaction_context"
            ),
        )

        context["communication_repair"] = {
            "original_message": communication.intended_message,
            "recipient_interpretation": (
                communication.listener_interpretation
            ),
            "interpretation_evidence": "llm_interpretation_not_verified",
            "clarification_requested": True,
            "repair_action": repair_event.action,
        }

        return generate_message(
            agent_id=speaker_id,
            interaction_context=context,
        )

    def run_repair_event(self, initiation_event, repair_decision=None):
        """Generate and record a communication repair when selected."""

        if repair_decision is None:
            repair_decision = self.make_repair_decision(initiation_event)
            
        if repair_decision is None:
            return None

        if repair_decision.action not in {
            "repeat_information",
            "rephrase_information",
            "provide_written_information",
        }:
            return None

        communication = initiation_event.communication
        speaker_id = communication.speaker_id
        recipient_id = communication.listener_id

        if repair_decision.action == "repeat_information":
            original_message = communication.intended_message
            response = MessageGenerationResult(
                text=original_message,
                model="deterministic",
                status="generated" if original_message else "failed",
                error=(
                    None if original_message
                    else "Original message unavailable"
                ),
            )
        else:
            response = self.generate_repair_message(
                initiation_event,
                repair_decision,
            )

        environment = self.generate_communication_environment()
        interpreted = None

        if response.status == "generated" and response.text:
            context = self.build_recipient_interpretation_context(
                recipient_id,
                speaker_id,
                None,
                initiation_event.decision_basis.get(
                    "interaction_context"
                ),
            )
            context["communication_repair"] = {
                "original_message": communication.intended_message,
                "repair_message": response.text,
                "repair_action": repair_decision.action,
            }
            interpreted = interpret_recipient_message(
                recipient_id=recipient_id,
                message=response.text,
                interaction_context=context,
            )

        repair_channel = (
            "text"
            if repair_decision.action == "provide_written_information"
            else "speech"
        )

        if repair_channel == "text":
            environment.written_information_available = True

        repair_communication = CommunicationEvent(
            speaker_id=speaker_id,
            listener_id=recipient_id,
            intended_message=(
                response.text if response.status == "generated" else None
            ),
            perceived_message=(
                interpreted.perceived_message
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
            listener_interpretation=(
                interpreted.interpretation
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
            channel=repair_channel,
            environment=environment,
        )

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="communication_repair",
            participants=[speaker_id, recipient_id],
            initiating_agent_id=speaker_id,
            action=repair_decision.action,
            decision_basis={
                "repair_decision_event_id": repair_decision.event_id,
                "message_generation": {
                    "status": response.status,
                    "model": response.model,
                    "error": response.error,
                },
                "recipient_interpretation": {
                    "status": (
                        interpreted.status if interpreted else "not_attempted"
                    ),
                    "model": interpreted.model if interpreted else None,
                    "comprehension_assessment": (
                        getattr(interpreted, "comprehension_assessment", None)
                        if interpreted and interpreted.status == "interpreted"
                        else None
                    ),
                    "error": interpreted.error if interpreted else None,
                    "evidence_status": "llm_interpretation_not_verified",
                },
                "comprehension": "not_assessed",
            },
            description="The original speaker attempted communication repair.",
            communication=repair_communication,
        )

        return self.record_event(event)
    
    def make_response_decision(self, initiation_event, incoming_event=None):
        """Let the current listener independently decide how to respond."""

        if initiation_event.event_type != "communication_initiation":
            raise ValueError(
                "A communication initiation event is required."
            )

        communication_event = incoming_event or initiation_event
        communication = getattr(
            communication_event, "communication", None
        )

        if communication is not None:
            speaker_id = communication.speaker_id
            recipient_id = communication.listener_id
        else:
            speaker_id = initiation_event.initiating_agent_id
            recipient_id = next(
                participant
                for participant in initiation_event.participants
                if participant != speaker_id
            )

        relationship = next(
            (
                item for item in self.relationships
                if item.agent_id == recipient_id
                and item.contact_id == speaker_id
                and item.status == "active"
            ),
            None,
        )

        communication_context = (
            communication_event.decision_basis.get(
                "recipient_interpretation",
                {},
            )
        )

        decision = choose_action(
            agent=self.agents[recipient_id],
            available_actions=[
                "continue_interaction",
                "withdraw",
                "do_nothing",
            ],
            relationship=relationship,
            rng=self.rng,
            context="response",
            communication_context=communication_context,
        )

        return {
            "responding_agent_id": recipient_id,
            "initiating_agent_id": speaker_id,
            "relationship": relationship,
            "interaction_context": initiation_event.decision_basis.get(
                "interaction_context"
            ),
            "decision": decision,
        }

    def generate_response_message(
        self,
        response_result,
        incoming_communication=None,
    ):
        """Generate a response using the agent's own interpretation."""

        speaker_id = response_result["responding_agent_id"]
        recipient_id = response_result["initiating_agent_id"]
        relationship = response_result["relationship"]

        context = self.build_agent_context(
            speaker_id,
            recipient_id,
            relationship,
            response_result["interaction_context"],
        )

        if incoming_communication is not None:
            context["incoming_communication"] = {
                "message": incoming_communication.intended_message,
                "perceived_message": (
                    incoming_communication.perceived_message
                ),
                "interpretation": (
                    incoming_communication.listener_interpretation
                ),
            }

        return generate_message(
            agent_id=speaker_id,
            interaction_context=context,
        )

    def interpret_response_message(
        self,
        response_result,
        message,
        environment=None,
    ):
        """Interpret the response from the original initiator's perspective."""

        recipient_id = response_result["initiating_agent_id"]
        sender_id = response_result["responding_agent_id"]

        relationship = response_result["relationship"]

        context = self.build_recipient_interpretation_context(
            recipient_id,
            sender_id,
            relationship,
            response_result["interaction_context"],
        )

        # Add environmental conditions when they are available.
        if environment is not None:
            context["communication_environment"] = {
                "background_noise": environment.background_noise,
                "distance_metres": environment.distance_metres,
                "speaker_face_visible": environment.speaker_face_visible,
                "written_information_available": (
                    environment.written_information_available
                ),
                "message_clarity": environment.message_clarity,
            }

        return interpret_recipient_message(
            recipient_id=recipient_id,
            message=message,
            interaction_context=context,
        )

    def run_response_event(self, initiation_event, incoming_event=None):
        """Record the recipient's response when an active response occurs."""

        result = self.make_response_decision(
            initiation_event,
            incoming_event,
        )
        decision = result["decision"]

        if decision["action"] != "continue_interaction":
            return None

        communication_event = incoming_event or initiation_event

        response = self.generate_response_message(
            result,
            communication_event.communication,
        )

        environment = self.generate_communication_environment()

        interpreted = None

        if response.status == "generated" and response.text:
            interpreted = self.interpret_response_message(
                result,
                response.text,
                environment=environment,
            )

        communication = CommunicationEvent(
            speaker_id=result["responding_agent_id"],
            listener_id=result["initiating_agent_id"],
            intended_message=(
                response.text if response.status == "generated" else None
            ),
            perceived_message=(
                interpreted.perceived_message
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
            listener_interpretation=(
                interpreted.interpretation
                if interpreted and interpreted.status == "interpreted"
                else None
            ),
            environment=environment,
        )

        communication_assessment = {
            "acoustic_conditions": assess_acoustic_conditions(
                communication.environment,
                communication.channel,
            ),
            "visual_support": assess_visual_support(
                communication.environment,
            ),
            "comprehension": "not_assessed",
        }

        event = SimulationEvent(
            event_id=f"EVENT-{self.next_event_id:06d}",
            timestamp=self.current_time,
            event_type="communication_response",
            participants=[
                result["initiating_agent_id"],
                result["responding_agent_id"],
            ],
            initiating_agent_id=result["responding_agent_id"],
            action=decision["action"],
            decision_basis={
                "interaction_context": result["interaction_context"],
                "probabilities": decision["probabilities"],
                "factors": decision["decision_basis"],
                "communication_assessment": communication_assessment,
                "message_generation": {
                    "status": response.status,
                    "model": response.model,
                    "error": response.error,
                },
                "recipient_interpretation": {
                    "status": (
                        interpreted.status if interpreted else "not_attempted"
                    ),
                    "model": interpreted.model if interpreted else None,
                    "comprehension_assessment": (
                        interpreted.comprehension_assessment
                        if interpreted else None
                    ),
                    "error": interpreted.error if interpreted else None,
                    "evidence_status": "llm_interpretation_not_verified",
                },
            },
            description="The recipient responded to a conversation initiation.",
            communication=communication,
        )

        return self.record_event(event)

    def record_interaction_memories(
        self,
        initiation_event,
        response_event=None,
        clarification_event=None,
        repair_decision_event=None,
        repair_communication_event=None,
    ):
        """Record each participant's individual perspective."""

        month = (
            (self.current_time.year - self.start_time.year) * 12
            + self.current_time.month
            - self.start_time.month
        )

        interaction_id = initiation_event.event_id
        initial = initiation_event.communication
        interaction_context = getattr(
            initiation_event,
            "decision_basis",
            {},
        ).get("interaction_context")

        if initial is None:
            return

        communication_event_metrics = {
            "communication_breakdown": "not_established",
            "understanding_difficulty": "not_established",
            "repetition_required": (
                "1"
                if repair_communication_event is not None
                and repair_decision_event is not None
                and repair_decision_event.action == "repeat_information"
                else "not_established"
            ),
            "clarification_required": (
                "1"
                if clarification_event is not None
                and clarification_event.action == "attempt_clarification"
                else (
                    "0"
                    if clarification_event is not None
                    else "not_established"
                )
            ),
            "conversational_repair": (
                "1"
                if repair_communication_event is not None
                else (
                    "0"
                    if clarification_event is not None
                    else "not_established"
                )
            ),
            "missed_information": "not_established",
            "concentration_demand": "not_established",
        }

        initiator_id = initial.speaker_id
        recipient_id = initial.listener_id

        response = (
            getattr(response_event, "communication", None)
            if response_event is not None
            else None
        )
        response_generation = (
            getattr(response_event, "decision_basis", {}) or {}
        ).get("message_generation", {}) if response_event is not None else {}

        response_generated = bool(
            response is not None and response.intended_message
        )

        relationship = next(
            (
                item for item in self.relationships
                if item.status == "active"
                and (
                    (
                        item.agent_id == initiator_id
                        and item.contact_id == recipient_id
                    )
                    or (
                        item.agent_id == recipient_id
                        and item.contact_id == initiator_id
                    )
                )
            ),
            None,
        )

        interaction = {
            "interaction_id": interaction_id,
            "interaction_context": interaction_context,
            "initiating_message": {
                "speaker_id": initial.speaker_id,
                "listener_id": initial.listener_id,
                "intended_message": initial.intended_message,
                "perceived_message": initial.perceived_message,
                "interpretation": initial.listener_interpretation,
                "initial_outcome": initial.initial_outcome,
                "final_outcome": initial.final_outcome,
                "environment": {
                    "background_noise": (
                        initial.environment.background_noise
                    ),
                    "distance_metres": (
                        initial.environment.distance_metres
                    ),
                    "speaker_face_visible": (
                        initial.environment.speaker_face_visible
                    ),
                    "written_information_available": (
                        initial.environment.written_information_available
                    ),
                    "message_clarity": (
                        initial.environment.message_clarity
                    ),
                },
            },
            "response": (
                {
                    "attempted": True,
                    "occurred": response_generated,
                    "generation_status": response_generation.get(
                        "status",
                        "unknown",
                    ),
                    "speaker_id": response.speaker_id,
                    "listener_id": response.listener_id,
                    "intended_message": response.intended_message,
                    "perceived_message": response.perceived_message,
                    "interpretation": response.listener_interpretation,
                    "initial_outcome": response.initial_outcome,
                    "final_outcome": response.final_outcome,
                    "environment": {
                        "background_noise": (
                            response.environment.background_noise
                        ),
                        "distance_metres": (
                            response.environment.distance_metres
                        ),
                        "speaker_face_visible": (
                            response.environment.speaker_face_visible
                        ),
                        "written_information_available": (
                            response.environment.written_information_available
                        ),
                        "message_clarity": (
                            response.environment.message_clarity
                        ),
                    },
                }
                if response is not None
                else {
                    "attempted": response_event is not None,
                    "occurred": False,
                    "generation_status": (
                        response_generation.get("status", "unknown")
                        if response_event is not None
                        else "not_attempted"
                    ),
                }
            ),
        }


        def event_summary(event):
            if event is None:
                return None

            decision_basis = getattr(event, "decision_basis", {}) or {}

            return {
                "event_id": getattr(event, "event_id", None),
                "event_type": getattr(event, "event_type", None),
                "action": getattr(event, "action", None),
                "decision_basis": decision_basis,
                "evidence_status": decision_basis.get(
                    "evidence_status"
                ),
            }

        repair_decision_basis = (
            getattr(repair_communication_event, "decision_basis", {}) or {}
            if repair_communication_event is not None
            else {}
        )

        repair_interpretation = repair_decision_basis.get(
            "recipient_interpretation",
            {},
        )

        interaction_history = {
            "clarification_decision": event_summary(
                clarification_event
            ),
            "repair_decision": event_summary(
                repair_decision_event
            ),
            "repair_communication": (
                {
                    "event_id": getattr(
                        repair_communication_event, "event_id", None
                    ),
                    "action": getattr(
                        repair_communication_event, "action", None
                    ),
                    "speaker_id": repair_communication_event.communication.speaker_id,
                    "listener_id": repair_communication_event.communication.listener_id,
                    "intended_message": repair_communication_event.communication.intended_message,
                    "perceived_message": repair_communication_event.communication.perceived_message,
                    "interpretation": repair_communication_event.communication.listener_interpretation,
                    "interpretation_status": repair_interpretation.get("status"),
                    "comprehension_assessment": repair_interpretation.get(
                        "comprehension_assessment"
                    ),
                    "interpretation_evidence": repair_interpretation.get(
                        "evidence_status"
                    ),
                    "channel": repair_communication_event.communication.channel,
                }
                if repair_communication_event is not None
                and getattr(repair_communication_event, "communication", None) is not None
                else None
            ),
        }
        assessments = {
            participant_id: {
                "assessment": None,
                "model": "not_run",
                "status": "not_run",
                "error": "assessment_deferred",
            }
            for participant_id in (recipient_id, initiator_id)
        }


        # Record the original recipient's perspective.
        self.memory.record_event(
            agent_id=recipient_id,
            month=month,
            event_type="communication_interaction",
            sender_id=initiator_id,
            recipient_id=recipient_id,
            actual_message=initial.intended_message,
            agent_interpretation=initial.listener_interpretation,
            outcome="not_assessed",
            emotional_appraisal=None,
            additional_details={
                "interaction_id": interaction_id,
                "occurred_at": self.current_time.isoformat(),
                "perspective": "recipient",
                "interaction": interaction,
                "interaction_history": interaction_history,
                "perceived_message": initial.perceived_message,
                "response_sent": (
                    response.intended_message if response else None
                ),
                "interpretation_evidence": (
                    "llm_interpretation_not_verified"
                ),
                "experience_assessment": assessments[recipient_id],
                "communication_event_metrics": (
                    communication_event_metrics
                ),
                "communication_event_metrics_evidence": (
                    "simulation_recorded_events"
                ),
            },
        )

        # Record the original initiator's perspective.
        self.memory.record_event(
            agent_id=initiator_id,
            month=month,
            event_type="communication_interaction",
            sender_id=(
                response.speaker_id if response else None
            ),
            recipient_id=(
                response.listener_id if response else None
            ),
            actual_message=(
                response.intended_message if response else None
            ),
            agent_interpretation=(
                response.listener_interpretation if response else None
            ),
            outcome="not_assessed",
            emotional_appraisal=None,
            additional_details={
                "interaction_id": interaction_id,
                "occurred_at": self.current_time.isoformat(),
                "perspective": "initiator",
                "interaction": interaction,
                "interaction_history": interaction_history,
                "message_sent": initial.intended_message,
                "perceived_response": (
                    response.perceived_message if response else None
                ),
                "interpretation_evidence": (
                    "llm_interpretation_not_verified"
                ),
                "communication_event_metrics": (
                    communication_event_metrics
                ),
                "communication_event_metrics_evidence": (
                    "simulation_recorded_events"
                ),
                "experience_assessment": assessments[initiator_id],
            },
        )

    def run_interaction_cycle(self, opportunity=None):
        """Run one conversation with a maximum of four spoken messages."""

        initiation_event = self.run_initiation_event(opportunity)

        if initiation_event is None:
            return []

        generated_events = [initiation_event]

        if not self.prepare_initiation_communication(initiation_event):
            return generated_events

        clarification_event = None
        repair_decision = None
        repair_communication_event = None

        if initiation_event.communication is not None:
            clarification_event = self.make_clarification_decision(
                initiation_event
            )
            generated_events.append(clarification_event)

            repair_decision = self.make_repair_decision(
                initiation_event
            )

            if repair_decision is not None:
                generated_events.append(repair_decision)

                repair_communication_event = self.run_repair_event(
                    initiation_event,
                    repair_decision,
                )

                if repair_communication_event is not None:
                    generated_events.append(repair_communication_event)

        # Count the opening message and any repair message.
        message_count = 1
        if repair_communication_event is not None:
            message_count += 1

        incoming_event = (
            repair_communication_event
            if repair_communication_event is not None
            else initiation_event
        )
        response_event = None

        while message_count < 4:
            if incoming_event is initiation_event:
                response_event = self.run_response_event(initiation_event)
            else:
                response_event = self.run_response_event(
                    initiation_event,
                    incoming_event=incoming_event,
                )

            if response_event is None:
                break

            generated_events.append(response_event)

            communication = getattr(
                response_event, "communication", None
            )
            if (
                response_event.action != "continue_interaction"
                or communication is None
                or not communication.intended_message
            ):
                break

            message_count += 1
            incoming_event = response_event

        self.record_interaction_memories(
            initiation_event,
            response_event,
            clarification_event=clarification_event,
            repair_decision_event=repair_decision,
            repair_communication_event=repair_communication_event,
        )

        return generated_events

    def summary(self):
        """Return a concise summary of the simulation."""

        return {
            "population_size": len(self.agents),
            "relationship_count": len(self.relationships),
            "event_count": len(self.events),
            "current_time": self.current_time.isoformat(),
            "random_seed": self.random_seed,
        }

    def assess_recent_communication_demand(
        self,
        agent_id,
        window_days=30,
    ):
        """Summarise recorded communication demands over a recent period."""

        if window_days <= 0:
            raise ValueError("Window must be greater than zero days.")

        period_start = self.current_time - timedelta(days=window_days)
        recent_metrics = []

        for record in self.memory.get_history(agent_id):
            if record["event_type"] != "communication_interaction":
                continue

            details = record.get("additional_details", {})
            occurred_at = details.get("occurred_at")

            if not occurred_at:
                continue

            try:
                event_time = datetime.fromisoformat(occurred_at)
            except (TypeError, ValueError):
                continue

            if period_start <= event_time <= self.current_time:
                recent_metrics.append(
                    details.get("communication_event_metrics", {})
                )

        def count_events(metric):
            return sum(
                metrics.get(metric) == "1"
                for metrics in recent_metrics
            )

        return {
            "window_days": window_days,
            "interaction_count": len(recent_metrics),
            "clarification_required_count": count_events(
                "clarification_required"
            ),
            "repetition_required_count": count_events(
                "repetition_required"
            ),
            "conversational_repair_count": count_events(
                "conversational_repair"
            ),
            "communication_breakdown_count": count_events(
                "communication_breakdown"
            ),
            "evidence": "simulation_recorded_events",
            "interpretation": (
                "recorded_communication_demand_not_fatigue"
            ),
        }
