from enum import Enum


class Sender(str, Enum):
    CUSTOMER = "customer"
    ASSISTANT = "assistant"
