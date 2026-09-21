package com.seebus.backend.schedule;

import org.springframework.stereotype.Component;

import java.time.ZonedDateTime;
import java.util.Comparator;
import java.util.List;

@Component
public class DefaultScheduleResolver
{
    public List<ScheduledStop> resolve(SchedulingInput input) {
        return input.defaultSchedule().stream().map(
                entry -> getNextOccurrence(entry, input.now())
        ).sorted(Comparator.comparing(ScheduledStop::arrivalTime)).toList();
    }

    private ScheduledStop getNextOccurrence(
            ScheduleEntry entry,
            ZonedDateTime now
    ) {
        ZonedDateTime arrival = entry.time()
                .atDate(now.toLocalDate())
                .atZone(now.getZone());

        if (arrival.isBefore(now)) {
            arrival = arrival.plusDays(1);
        }

        return new ScheduledStop(
                entry.busId(),
                entry.stationId(),
                arrival
        );
    }
}
