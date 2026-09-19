import {
    Box,
    Flex,
    Heading,
    HStack,
    IconButton,
} from "@chakra-ui/react";
import { Link as RouterLink } from "react-router-dom";
import { LuBusFront, LuSettings } from "react-icons/lu";

export function AppHeader() {
    return (
        <Box
            position="sticky"
            top="0"
            zIndex="20"
            w="100%"
            borderBottomWidth="1px"
            borderColor="whiteAlpha.100"
            bg="rgba(3, 8, 20, 0.94)"
            backdropFilter="blur(14px)"
            boxShadow="0 8px 24px rgba(0,0,0,0.24)"
        >
            <Flex
                w="100%"
                px={{ base: "4", md: "8", lg: "10" }}
                py="3"
                justify="space-between"
                align="center"
            >
                <HStack gap="3">
                    <Box
                        borderWidth="1px"
                        borderColor="teal.500"
                        bg="rgba(34, 199, 184, 0.10)"
                        color="teal.300"
                        borderRadius="lg"
                        px="2"
                        py="2"
                    >
                        <LuBusFront />
                    </Box>

                    <Heading size="xl">
                        SeeBus
                    </Heading>
                </HStack>

                <IconButton
                    asChild
                    aria-label="Settings"
                    size="sm"
                    variant="ghost"
                    borderRadius="full"
                    color="gray.300"
                    borderWidth="1px"
                    borderColor="whiteAlpha.200"
                    bg="whiteAlpha.50"
                    _hover={{
                        color: "teal.300",
                        bg: "whiteAlpha.100",
                        borderColor: "teal.500",
                    }}
                >
                    <RouterLink to="/admin">
                        <LuSettings />
                    </RouterLink>
                </IconButton>
            </Flex>
        </Box>
    );
}