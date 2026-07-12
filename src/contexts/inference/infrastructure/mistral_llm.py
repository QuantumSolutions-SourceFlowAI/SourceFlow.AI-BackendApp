import re

from mistralai.client import Mistral

from contexts.chatbots.domain.enums import Tone
from contexts.inference.application.ports import HistoryTurn

_TONE_INSTRUCTIONS = {
    Tone.FORMAL: "Responde de manera formal y profesional.",
    Tone.FRIENDLY: "Responde de manera cercana y amigable.",
    Tone.SALES: "Responde con orientación comercial, resaltando beneficios.",
}

_TAG_RE = re.compile(r"^\s*SOURCE:\s*(docs|general|chat)\b\s*", re.IGNORECASE)


def _system_prompt(purpose: str) -> str:
    domain = (f"Tu propósito y dominio: {purpose}" if purpose.strip()
              else "Ayudas principalmente sobre el contenido de los documentos proporcionados.")
    return (
        f"Eres un asistente virtual. {domain}\n\n"
        "Sigue esta jerarquía para responder:\n"
        "1. Si el usuario saluda, agradece o pregunta sobre ti (qué haces, de qué temas "
        "sabes), responde con naturalidad y brevedad.\n"
        "2. Si el CONTEXTO de documentos contiene la respuesta, respóndela usando SOLO ese "
        "contexto.\n"
        "3. Si el CONTEXTO no la contiene pero la pregunta está dentro de tu dominio, "
        "respóndela con tu conocimiento general y aclara explícitamente que esa información "
        "no proviene de los documentos.\n"
        "4. Si la pregunta está claramente fuera de tu dominio, declina cortésmente y "
        "reorienta hacia los temas que sí manejas.\n\n"
        "En la PRIMERA línea escribe exactamente una de estas etiquetas de origen:\n"
        "SOURCE: docs   (si usaste el contexto de los documentos)\n"
        "SOURCE: general (si usaste tu conocimiento general)\n"
        "SOURCE: chat   (si fue un saludo, cortesía o pregunta sobre ti)\n"
        "Desde la segunda línea en adelante escribe la respuesta para el usuario. "
        "No menciones la etiqueta en el texto de la respuesta."
    )


def parse_source(raw: str) -> tuple[str, str]:
    """Split an LLM reply into (body, source). Unknown/missing tag → general."""
    m = _TAG_RE.match(raw)
    if m:
        source = m.group(1).lower()
        body = raw[m.end():].strip()
        return (body or raw.strip(), source)
    return (raw.strip(), "general")


class MistralLlmProvider:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Mistral(api_key=api_key)
        self._model = model

    def generate(self, question: str, context_blocks: list[str], tone: Tone,
                 purpose: str, history: list[HistoryTurn]) -> tuple[str, str, int]:
        context = "\n\n".join(f"[Fragmento {i+1}]\n{b}" for i, b in enumerate(context_blocks))
        if not context:
            context = "(sin documentos relevantes)"
        user = (f"{_TONE_INSTRUCTIONS[tone]}\n\nCONTEXTO:\n{context}\n\n"
                f"PREGUNTA: {question}")
        messages = [{"role": "system", "content": _system_prompt(purpose)}]
        messages += [{"role": t.role, "content": t.text} for t in history]
        messages.append({"role": "user", "content": user})
        resp = self._client.chat.complete(
            model=self._model, messages=messages, temperature=0.2)
        raw = resp.choices[0].message.content.strip()
        tokens = getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0
        body, source = parse_source(raw)
        return (body, source, tokens)
