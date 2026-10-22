"""Shared-hub transit domain types and policy interfaces.

The package initializer intentionally avoids importing the SimPy-backed
simulation/experiment modules. This keeps configuration, scenarios, policies,
and sensor models lightweight to import. Simulation entry points live in
``seebus_sim.transit.experiment``.
"""

from seebus_sim.transit.config import RouteConfig, TransitConfig
from seebus_sim.transit.policies import (
    BusObservation,
    DispatchDecision,
    HistoricalPolicy,
    HistoricalPolicyConfig,
    HybridPolicy,
    HybridPolicyConfig,
    PolicyContext,
    RouteObservation,
    SchedulingPolicy,
    SensorPolicy,
    SensorPolicyConfig,
    StationObservation,
    StaticPolicy,
)
from seebus_sim.transit.sensors import NoisyOccupancySensor, SensorConfig

__all__ = [
    "BusObservation",
    "DispatchDecision",
    "HistoricalPolicy",
    "HistoricalPolicyConfig",
    "HybridPolicy",
    "HybridPolicyConfig",
    "NoisyOccupancySensor",
    "PolicyContext",
    "RouteConfig",
    "RouteObservation",
    "SchedulingPolicy",
    "SensorConfig",
    "SensorPolicy",
    "SensorPolicyConfig",
    "StationObservation",
    "StaticPolicy",
    "TransitConfig",
]
