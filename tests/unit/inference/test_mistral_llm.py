from contexts.inference.infrastructure.mistral_llm import parse_source


def test_parse_docs_tag():
    body, source = parse_source("SOURCE: docs\nEl precio es 100 soles.")
    assert source == "docs"
    assert body == "El precio es 100 soles."


def test_parse_general_tag_case_insensitive():
    body, source = parse_source("source: GENERAL\nGit es un control de versiones.")
    assert source == "general"
    assert body == "Git es un control de versiones."


def test_parse_chat_tag():
    body, source = parse_source("SOURCE: chat\n¡Hola! ¿En qué te ayudo?")
    assert source == "chat"
    assert body == "¡Hola! ¿En qué te ayudo?"


def test_missing_tag_defaults_to_general():
    body, source = parse_source("No hay etiqueta aquí.")
    assert source == "general"
    assert body == "No hay etiqueta aquí."


def test_unrecognized_tag_defaults_to_general():
    body, source = parse_source("SOURCE: banana\nTexto raro.")
    assert source == "general"
    # whole reply kept as body since the tag was not a valid one
    assert body == "SOURCE: banana\nTexto raro."
