package com.seebus.backend.api.policy;

import java.util.List;

public record PolicyResponse(
        String activePolicy,
        List<String> availablePolicies
) {
}
