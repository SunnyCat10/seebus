from seebus_sim.transit.policies.base import PolicyContext, RouteObservation


def nominal_route_headway(context: PolicyContext) -> float:
    """Nominal per-route headway of the static round-robin control."""
    return context.static_dispatch_interval_minutes * len(context.routes)


def headway_limits(
    context: PolicyContext,
    min_headway_factor: float,
    max_headway_factor: float,
) -> tuple[float, float]:
    nominal = nominal_route_headway(context)
    return nominal * min_headway_factor, nominal * max_headway_factor


def elapsed_since_dispatch(route: RouteObservation, max_headway: float) -> float:
    """Treat a route with no dispatch yet today as immediately due."""
    return (
        route.minutes_since_dispatch
        if route.minutes_since_dispatch is not None
        else max_headway
    )


def historical_demand_pressure(
    context: PolicyContext,
    route: RouteObservation,
    *,
    elapsed: float,
    target_load_fraction: float,
) -> tuple[float, float]:
    """Return normalized historical pressure and estimated accumulated demand."""
    if route.predicted_arrivals_next_horizon is None:
        raise RuntimeError(
            "historical demand prediction is required; "
            f"route {route.route_id!r} has none"
        )

    prediction_window = (
        route.prediction_window_minutes
        if route.prediction_window_minutes is not None
        else context.prediction_horizon_minutes
    )
    if prediction_window <= 0:
        return 0.0, 0.0

    predicted_rate = route.predicted_arrivals_next_horizon / prediction_window
    predicted_backlog = predicted_rate * elapsed
    target_passengers = context.bus.capacity * target_load_fraction
    pressure = predicted_backlog / target_passengers
    return pressure, predicted_backlog
