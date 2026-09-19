import { useState } from "react";
import {
    Box,
    Button,
    Container,
    Heading,
    Input,
    Text,
    VStack,
} from "@chakra-ui/react";
import { LuLockKeyhole } from "react-icons/lu";

import { verifyAdminToken} from "../../api/seebusApi.ts";

interface AdminGateProps {
    onUnlock: (token: string) => void;
}

export function AdminGate({
                              onUnlock,
                          }: AdminGateProps) {
    const [token, setToken] = useState("");
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(false);

    async function unlock() {
        setLoading(true);
        setError(false);

        try {
            const valid = await verifyAdminToken(token);

            if (!valid) {
                setError(true);
                return;
            }

            sessionStorage.setItem(
                "seebus-admin-token",
                token,
            );

            onUnlock(token);
        } finally {
            setLoading(false);
        }
    }

    return (
        <Box minH="100vh" bg="#050d20">
            <Container maxW="md" py="24">
                <VStack
                    gap="5"
                    p="8"
                    borderWidth="1px"
                    borderColor="whiteAlpha.200"
                    borderRadius="2xl"
                    bg="rgba(12, 21, 42, 0.92)"
                    align="stretch"
                >
                    <Box
                        color="teal.300"
                        fontSize="2xl"
                    >
                        <LuLockKeyhole />
                    </Box>

                    <Box>
                        <Heading size="lg">
                            SeeBus Admin
                        </Heading>

                        <Text
                            mt="2"
                            color="gray.400"
                        >
                            Enter the administrator token
                            to continue
                        </Text>
                    </Box>

                    <Input
                        type="password"
                        value={token}
                        placeholder="Admin token"
                        onChange={(event) =>
                            setToken(event.target.value)
                        }
                        onKeyDown={(event) => {
                            if (event.key === "Enter") {
                                void unlock();
                            }
                        }}
                    />

                    {error && (
                        <Text
                            color="red.300"
                            fontSize="sm"
                        >
                            Invalid administrator token
                        </Text>
                    )}

                    <Button
                        onClick={() => void unlock()}
                        loading={loading}
                        disabled={!token}
                        colorPalette="teal"
                    >
                        Unlock
                    </Button>
                </VStack>
            </Container>
        </Box>
    );
}