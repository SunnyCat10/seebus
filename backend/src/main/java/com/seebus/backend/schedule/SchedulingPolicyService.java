package com.seebus.backend.schedule;

import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
public class SchedulingPolicyService {

    private final Map<String, SchedulingPolicy> policies;
    private final AtomicReference<String> activePolicy = new AtomicReference<>("default");

    public SchedulingPolicyService(List<SchedulingPolicy> policies) {
        this.policies = policies.stream().collect(Collectors.toMap(SchedulingPolicy::getName, Function.identity()));
    }

    public SchedulingPolicy getActivePolicy() {
        return policies.get(activePolicy.get());
    }

    public String getActivePolicyName() {
        return activePolicy.get();
    }

    public List<String> getAvailablePolicies() {
        return policies.keySet().stream().sorted().toList();
    }

    public void setActivePolicy(String name) {
        if (!policies.containsKey(name)) {
            throw new IllegalArgumentException(
                    "Unknown scheduling policy: " + name
            );
        }

        activePolicy.set(name);
    }
}
