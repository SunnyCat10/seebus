package com.seebus.backend.station;

import jakarta.validation.constraints.NotBlank;

public record CreateStationRequest (
    @NotBlank
    String id,

    @NotBlank
    String name
) {

}
