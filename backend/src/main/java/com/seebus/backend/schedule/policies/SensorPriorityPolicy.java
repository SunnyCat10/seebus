package com.seebus.backend.schedule.policies;

import com.seebus.backend.reading.StationReading;
import com.seebus.backend.schedule.*;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.time.Instant;
import java.time.ZonedDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Component
public class SensorPriorityPolicy implements SchedulingPolicy {

    private static final double OCCUPANCY_THRESHOLD = 0.5;
    private static final Duration PRIORITY_DURATION = Duration.ofMinutes(1);
    private static final Duration READING_VALIDITY = Duration.ofSeconds(30);

    private final DefaultScheduleResolver scheduleResolver;
    private final ConcurrentHashMap<String, PriorityCommitment> commitments = new ConcurrentHashMap<>();

    public SensorPriorityPolicy(DefaultScheduleResolver scheduleResolver) {
        this.scheduleResolver = scheduleResolver;
    }

    @Override
    public CurrentSchedule calculateSchedule(SchedulingInput input) {

        // Loads the default schedule as a base
        List<ScheduledStop> stops = new ArrayList<>(scheduleResolver.resolve(input));

        removeExpiredCommitments(input.now());

        createCommitments(input, stops);

        applyCommitments(stops);

        stops.sort(Comparator.comparing(ScheduledStop::arrivalTime));

        return new CurrentSchedule(
                Instant.now(),
                getName(),
                List.copyOf(stops)
        );
    }

    private void removeExpiredCommitments(ZonedDateTime now) {
        commitments.forEach((stationId, commitment) -> {
            if (!commitment.arrivalTime().isAfter(now)) {
                commitments.remove(stationId, commitment);
            }
        });
    }

    private void createCommitments(SchedulingInput input, List<ScheduledStop> stops) {
        for (var reading : input.latestReadings().values()) {
            String stationId = reading.stationId();

            // If there is already a bus on route, we don`t need to commit another one
            if (commitments.containsKey(stationId)) {
                continue;
            }

            if (reading.occupancy() < OCCUPANCY_THRESHOLD) {
                continue;
            }

            if (!isFresh(reading, input.now())) {
                continue;
            }

            findNextStopForStation(stationId, stops).ifPresent(stop -> {
                ZonedDateTime priorityArrival = input.now().plus(PRIORITY_DURATION);

                PriorityCommitment commitment = new PriorityCommitment(stop, priorityArrival);

                commitments.putIfAbsent(stationId, commitment);
            });
        }
    }

    private void applyCommitments(List<ScheduledStop> stops) {
        for (var commitment : commitments.values()) {
            ScheduledStop commitedStop = commitment.originalStop();

            for (int i = 0; i < stops.size(); i++) {
                ScheduledStop stop = stops.get(i);

                boolean sameStop = stop.busId().equals(commitedStop.busId()) &&
                        stop.stationId().equals(commitedStop.stationId()) &&
                        stop.arrivalTime().equals(commitedStop.arrivalTime());

                if (!sameStop) {
                    continue;
                }

                stops.set(i, new ScheduledStop(
                        stop.busId(),
                        stop.stationId(),
                        commitment.arrivalTime()
                ));

                break;
            }
        }
    }

    private boolean isFresh(StationReading reading, ZonedDateTime now) {
        return reading.receivedAt().plus(READING_VALIDITY).isAfter(now.toInstant());
    }

    private Optional<ScheduledStop> findNextStopForStation(String stationId, List<ScheduledStop> stops) {
        return stops.stream().filter(stop -> stop.stationId().equals(stationId)).min(Comparator.comparing(ScheduledStop::arrivalTime));
    }

    @Override
    public String getName() {
        return "sensor-priority";
    }
}
