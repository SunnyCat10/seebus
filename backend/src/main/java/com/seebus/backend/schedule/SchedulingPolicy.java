package com.seebus.backend.schedule;

public interface SchedulingPolicy {

    CurrentSchedule calculateSchedule(SchedulingInput input);

    String getName();
}
