"""Allocation of explicit service demand against planned capacity."""

from dataclasses import asdict, dataclass

from src.agents.agent import Agent
from src.service_capacity.planned_schedule import PlannedServiceSchedule

from .demand import ServiceDemand


@dataclass
class ServiceAllocation:
    """Records the allocation outcome for one service demand."""

    demand_id: str
    agent_id: str
    service_id: str
    service_type: str
    age_group: str
    clinician_id: str
    allocation_status: str
    reason: str

    def validate(self):
        for name in (
            "demand_id",
            "agent_id",
            "service_id",
            "service_type",
            "age_group",
            "clinician_id",
            "reason",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string.")

        if self.allocation_status not in {"allocated", "unallocated"}:
            raise ValueError("Invalid allocation status.")

        return True

    def to_dict(self):
        self.validate()
        return asdict(self)


def allocate_service_demand(
    demands: list[ServiceDemand],
    agents: list[Agent],
    planned_schedule: PlannedServiceSchedule,
    allocation_policy: str = "first_come_first_served",
    random_seed: int | None = None,
    need_priority: list[str] | None = None,
) -> list[ServiceAllocation]:
    """Allocate service demand against planned monthly capacity.

    Supported policies:
    - first_come_first_served
    - need_based
    - random

    Every valid demand receives an allocation outcome. Returned outcomes
    retain the original demand order, regardless of allocation policy.
    """

    import random

    if not isinstance(demands, list):
        raise TypeError("demands must be a list.")

    if not isinstance(agents, list):
        raise TypeError("agents must be a list.")

    if not isinstance(planned_schedule, PlannedServiceSchedule):
        raise TypeError(
            "planned_schedule must be a PlannedServiceSchedule."
        )

    if allocation_policy not in {
        "first_come_first_served",
        "need_based",
        "random",
    }:
        raise ValueError("Invalid allocation_policy.")

    if need_priority is None:
        need_priority = [
            "functional_difficulty_confirmed",
            "difficulty_reported",
            "unknown",
            "no_identified_difficulty",
        ]

    if allocation_policy == "need_based":
        if (
            not isinstance(need_priority, list)
            or len(need_priority) != 4
            or set(need_priority) != {
                "functional_difficulty_confirmed",
                "difficulty_reported",
                "unknown",
                "no_identified_difficulty",
            }
        ):
            raise ValueError("Invalid need_priority configuration.")

    planned_schedule.validate()

    agent_lookup = {}

    for agent in agents:
        if not isinstance(agent, Agent):
            raise TypeError("Every population member must be an Agent.")

        agent.validate()

        if agent.agent_id in agent_lookup:
            raise ValueError(f"Duplicate agent ID: {agent.agent_id}")

        agent_lookup[agent.agent_id] = agent

    demand_ids = set()

    for demand in demands:
        if not isinstance(demand, ServiceDemand):
            raise TypeError("Every demand must be a ServiceDemand.")

        demand.validate()

        if demand.demand_id in demand_ids:
            raise ValueError(f"Duplicate demand ID: {demand.demand_id}")

        demand_ids.add(demand.demand_id)

        if demand.agent_id not in agent_lookup:
            raise ValueError(
                f"No Agent found for demand: {demand.demand_id}"
            )

    eligible = []
    outcomes = {}

    for index, demand in enumerate(demands):
        agent = agent_lookup[demand.agent_id]
        age_group = agent.profile.age_group

        reason = None

        if demand.service_type != planned_schedule.service_type:
            reason = "service_type_not_in_schedule"
        elif age_group != planned_schedule.age_group:
            reason = "age_group_not_in_schedule"

        if reason is not None:
            outcomes[demand.demand_id] = (False, reason)
        else:
            eligible.append((index, demand, agent))

    rng = random.Random(random_seed)

    if allocation_policy == "need_based":
        priority_lookup = {
            status: index
            for index, status in enumerate(need_priority)
        }

        eligible.sort(
            key=lambda item: (
                priority_lookup.get(
                    item[2].profile.auditory_functional_status,
                    priority_lookup["unknown"],
                ),
                rng.random(),
                item[0],
            )
        )

    elif allocation_policy == "random":
        rng.shuffle(eligible)

    capacity = planned_schedule.planned_appointments_per_month

    for position, (_, demand, _) in enumerate(eligible):
        if position < capacity:
            outcomes[demand.demand_id] = (
                True,
                "matching_request_allocated",
            )
        else:
            outcomes[demand.demand_id] = (
                False,
                "planned_appointment_capacity_exhausted",
            )

    allocations = []

    for demand in demands:
        agent = agent_lookup[demand.agent_id]
        allocated, reason = outcomes[demand.demand_id]

        allocations.append(
            ServiceAllocation(
                demand_id=demand.demand_id,
                agent_id=demand.agent_id,
                service_id=planned_schedule.service_id,
                service_type=demand.service_type,
                age_group=agent.profile.age_group,
                clinician_id=planned_schedule.clinician_id,
                allocation_status=(
                    "allocated" if allocated else "unallocated"
                ),
                reason=reason,
            )
        )

    return allocations
