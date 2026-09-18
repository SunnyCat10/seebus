package com.seebus.backend.schedule.policies;

import com.seebus.backend.schedule.*;
import org.springframework.stereotype.Component;

import java.time.Instant;
import java.time.LocalDate;
import java.time.ZonedDateTime;
import java.util.Comparator;
import java.util.List;

@Component
public class DefaultPolicy implements SchedulingPolicy {

    @Override
    public CurrentSchedule calculateSchedule(SchedulingInput input) {

        List<ScheduledStop> entries = input.defaultSchedule().stream().map(
                entry -> getNextOccurrence(entry, input.now())).sorted(
                        Comparator.comparing(ScheduledStop::arrivalTime)).toList();

        return new CurrentSchedule(
                Instant.now(),
                getName(),
                entries
        );
    }

    private ScheduledStop getNextOccurrence(ScheduleEntry entry, ZonedDateTime now) {

        ZonedDateTime arrival = entry.time().atDate(now.toLocalDate()).atZone(now.getZone());

        if (arrival.isBefore(now)) {
            arrival = arrival.plusDays(1);
        }

        return new ScheduledStop(
                entry.busId(),
                entry.stationId(),
                arrival
        );
    }

    @Override
    public String getName() {
        return "default";
    }
}
