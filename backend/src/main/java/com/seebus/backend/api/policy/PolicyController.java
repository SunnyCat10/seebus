package com.seebus.backend.api.policy;

import com.seebus.backend.schedule.SchedulingPolicyService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/admin/policy")
public class PolicyController {

    private final SchedulingPolicyService policyService;

    public PolicyController(SchedulingPolicyService policyService) {
        this.policyService = policyService;
    }

    @GetMapping
    public PolicyResponse getPolicy() {
        return new PolicyResponse(
                policyService.getActivePolicyName(),
                policyService.getAvailablePolicies()
        );
    }

    @PutMapping PolicyResponse setPolicy(@RequestBody SetPolicyRequest request) {
        policyService.setActivePolicy(request.policy());

        return new PolicyResponse(
                policyService.getActivePolicyName(),
                policyService.getAvailablePolicies()
        );
    }
}
