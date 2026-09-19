import {Box, Button, ButtonGroup, Flex, Heading, HStack, Text} from "@chakra-ui/react";
import {LuArrowLeft, LuBusFront} from "react-icons/lu";
import { Link as RouterLink } from "react-router-dom";

export const AdminHeader = () => {
    return (
        <Box
            borderBottomWidth="1px"
            borderColor="whiteAlpha.100"
            bg="rgba(2, 7, 18, 0.97)"
        >
            <Flex
                px="8"
                py="3"
                align="center"
                justify="space-between"
            >
                <HStack gap="3">
                    <Box
                        borderWidth="1px"
                        borderColor="teal.700"
                        borderRadius="lg"
                        color="teal.300"
                        p="2"
                    >
                        <LuBusFront />
                    </Box>

                    <Box>
                        <Heading size="md">
                            SeeBus Admin
                        </Heading>

                        <Text
                            fontSize="xs"
                            color="fg.muted"
                        >
                            Internal configuration
                        </Text>
                    </Box>
                </HStack>

                <ButtonGroup size="sm">
                    <Button
                        asChild
                        variant="ghost"
                    >
                        <RouterLink to="/">
                            <LuArrowLeft />

                            Public view
                        </RouterLink>
                    </Button>
                </ButtonGroup>
            </Flex>
        </Box>
    );
};