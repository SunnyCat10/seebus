package com.seebus.backend.config;

import com.seebus.backend.station.CreateStationRequest;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;

import java.util.List;

public record AdminConfigRequest(

        @NotNull
        List<@Valid CreateStationRequest> stations,

        @NotNull
        List<@Valid BusConfigRequest> buses,

        @NotNull
        List<@Valid ScheduleEntryRequest> defaultSchedule
) {
}
