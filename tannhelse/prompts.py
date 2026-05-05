import re

SYSTEM_PROMPT = """\
Du er en assistent som svarer på spørsmål om norsk tannhelseregulering, \
utelukkende basert på dokumentene som leveres i KONTEKST-blokken.

Regler du må følge strengt:

1. Svar kun på norsk.
2. Bruk kun informasjon fra KONTEKST. Du skal ikke trekke inn allmennkunnskap eller \
   informasjon utenfor de leverte tekstutdragene.
3. Etter hver påstand som er hentet fra KONTEKST, sett inn et tall i hakeparentes \
   som peker til riktig kilde, f.eks. [1] eller [3]. Tallene må samsvare nøyaktig \
   med [N]-numrene i KONTEKST.
4. Hvis spørsmålet ikke kan besvares basert på KONTEKST, svar nøyaktig denne setningen \
   og ingenting annet: "Dette finner jeg ikke i de tilgjengelige dokumentene."
5. Ta gjerne med korte ordrette sitater fra kildene når det styrker svaret.
"""


def _format_kontekst_block(chunks) -> str:
    if not chunks:
        return "KONTEKST: (ingen relevante utdrag)"
    body = "\n".join(f"[{i}] {chunk.text}" for i, chunk in enumerate(chunks, start=1))
    return f"KONTEKST: {body}"


def build_messages(
    history: list[dict], kontekst_chunks: list, query: str
) -> list[dict]:
    kontekst = _format_kontekst_block(kontekst_chunks)
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *history[-6:],
        {"role": "user", "content": f"{kontekst}\n\nSPØRSMÅL: {query}"},
    ]


def parse_citations(answer, chunks):
    markers = sorted({int(m) for m in re.findall(r"\[(\d+)\]", answer)})
    valid = [n for n in markers if 1 <= n <= len(chunks)]
    if not valid:
        return ""
    lines = ["Kilder:"]
    for n in valid:
        chunk = chunks[n - 1]
        lines.append(f"[{n}] {chunk.document}, {chunk.section_label}")
    return "\n".join(lines)
