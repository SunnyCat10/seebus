package com.seebus.backend.schedule.policies;

import com.seebus.backend.schedule.*;
import org.springframework.stereotype.Component;

import java.time.Instant;

@Component
public class DefaultPolicy implements SchedulingPolicy {

    private final DefaultScheduleResolver scheduleResolver;

    public DefaultPolicy(DefaultScheduleResolver scheduleResolver) {
        this.scheduleResolver = scheduleResolver;
    }

    @Override
    public CurrentSchedule calculateSchedule(SchedulingInput input) {
        return new CurrentSchedule(
                Instant.now(),
                getName(),
                scheduleResolver.resolve(input)
        );
    }

    @Override
    public String getName() {
        return "default";
    }
}
