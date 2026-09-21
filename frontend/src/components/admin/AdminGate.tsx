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

export const AdminGate = (props : AdminGateProps) => {
    const {onUnlock} = props;

    const [token, setToken] = useState("");
    const [error, setError] = useState(false);
    const [loading, setLoading] = useState(false);

    const unlock = async () => {
        setLoading(true);
        setError(false);

        try {
            const valid = await verifyAdminToken(token);

            if (!valid) {
                setError(true);
                return;
            }

            sessionStorage.setItem("seebus-admin-token", token);

            onUnlock(token);
        } finally {
            setLoading(false);
        }
    }

    return (
        <Container
            maxW="md"
            py="16"
        >
            <VStack
                gap="5"
                p="8"
                borderWidth="1px"
                borderColor="border"
                borderRadius="2xl"
                bg="bg.panel"
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
                        color="fg.muted"
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
    );
}