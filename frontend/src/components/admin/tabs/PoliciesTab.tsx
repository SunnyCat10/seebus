import {useEffect, useState} from "react";

import {
    Badge,
    Box,
    createListCollection,
    Heading,
    Portal,
    Select,
    Spinner,
    Stack,
    Text,
} from "@chakra-ui/react";

import {getPolicy, updatePolicy} from "../../../api/seebusApi";

import type {PolicyInfo} from "../../../types/policy";

interface PoliciesTabProps {
    adminToken: string;
    onCountChange?: (count: number) => void;
}

export const PoliciesTab = (props : PoliciesTabProps) => {
    const {adminToken, onCountChange} = props;

    const [policyInfo, setPolicyInfo] = useState<PolicyInfo | null>(null);
    const [updating, setUpdating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let cancelled = false;

        const loadPolicies = async () => {
            try {
                const info =
                    await getPolicy(adminToken);

                if (cancelled) {
                    return;
                }

                setPolicyInfo(info);

                onCountChange?.(
                    info.availablePolicies.length,
                );

                setError(null);
            } catch (error) {
                if (cancelled) {
                    return;
                }

                setError(
                    error instanceof Error
                        ? error.message
                        : "Could not load policies",
                );
            }
        };

        void loadPolicies();

        return () => {
            cancelled = true;
        };
    }, [adminToken, onCountChange]);

    const changePolicy = async (
        policy: string,
    ) => {
        if (
            !policyInfo ||
            policy === policyInfo.activePolicy
        ) {
            return;
        }

        setUpdating(true);
        setError(null);

        try {
            const updated =
                await updatePolicy(
                    policy,
                    adminToken,
                );

            setPolicyInfo(updated);

            onCountChange?.(
                updated.availablePolicies.length,
            );
        } catch (error) {
            setError(
                error instanceof Error
                    ? error.message
                    : "Could not update policy",
            );
        } finally {
            setUpdating(false);
        }
    };

    if (!policyInfo) {
        return (
            <Box
                mt="6"
                p="6"
            >
                <Spinner
                    colorPalette="teal"
                />
            </Box>
        );
    }

    const policyCollection =
        createListCollection({
            items:
                policyInfo.availablePolicies.map(
                    (policy) => ({
                        label: policy,
                        value: policy,
                    }),
                ),
        });

    return (
        <Box
            mt="6"
            borderWidth="1px"
            borderRadius="lg"
            p="6"
        >
            <Stack gap="5">
                <Box>
                    <Heading size="md">
                        Scheduling policy
                    </Heading>

                    <Text
                        color="fg.muted"
                        mt="1"
                    >
                        Select the scheduling strategy used
                        by the SeeBus scheduler
                    </Text>
                </Box>

                <Box>
                    <Text
                        fontSize="sm"
                        fontWeight="medium"
                        mb="2"
                    >
                        Active policy
                    </Text>

                    <Badge
                        colorPalette="teal"
                        variant="subtle"
                        mb="4"
                    >
                        {policyInfo.activePolicy}
                    </Badge>

                    <Select.Root
                        collection={policyCollection}
                        value={[
                            policyInfo.activePolicy,
                        ]}
                        disabled={updating}
                        maxW="400px"
                        onValueChange={(details) => {
                            const policy =
                                details.value[0];

                            if (policy) {
                                void changePolicy(
                                    policy,
                                );
                            }
                        }}
                    >
                        <Select.HiddenSelect />

                        <Select.Control>
                            <Select.Trigger>
                                <Select.ValueText
                                    placeholder="Select policy"
                                />
                            </Select.Trigger>

                            <Select.IndicatorGroup>
                                <Select.Indicator />
                            </Select.IndicatorGroup>
                        </Select.Control>

                        <Portal>
                            <Select.Positioner>
                                <Select.Content>
                                    {policyCollection.items.map(
                                        (policy) => (
                                            <Select.Item
                                                key={policy.value}
                                                item={policy}
                                            >
                                                <Select.ItemText>
                                                    {policy.label}
                                                </Select.ItemText>

                                                <Select.ItemIndicator />
                                            </Select.Item>
                                        ),
                                    )}
                                </Select.Content>
                            </Select.Positioner>
                        </Portal>
                    </Select.Root>

                    {updating && (
                        <Text
                            color="fg.muted"
                            fontSize="sm"
                            mt="2"
                        >
                            Updating policy...
                        </Text>
                    )}
                </Box>

                {error && (
                    <Text
                        color="red.400"
                        fontSize="sm"
                    >
                        {error}
                    </Text>
                )}
            </Stack>
        </Box>
    );
};