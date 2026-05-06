import re
from pathlib import Path

SYSTEM_PROMPT = """\
Du er en assistent som svarer på spørsmål om norsk tannhelseregulering, \
utelukkende basert på dokumentene som leveres i KONTEKST-blokken.

Regler du må følge strengt:

1. Svar kun på norsk.
2. Faktagrunnlaget skal komme utelukkende fra KONTEKST. Du skal ikke trekke inn \
   allmennkunnskap, antakelser eller informasjon utenfor de leverte tekstutdragene.
3. Du kan og bør gjerne syntetisere, sammenstille og oppsummere på tvers av flere \
   utdrag — for eksempel når brukeren spør om temaer, risiko, usikkerhet, \
   konsekvenser, uenigheter mellom aktører eller utvikling fremover. Hver \
   konkrete påstand må fortsatt være forankret i KONTEKST.
4. Etter hver påstand som er hentet fra KONTEKST, sett inn et tall i hakeparentes \
   som peker til riktig kilde, f.eks. [1] eller [3]. Tallene må samsvare nøyaktig \
   med [N]-numrene i KONTEKST. Du kan sitere flere kilder etter samme påstand, \
   f.eks. [1][3].
5. Hvis kildene er uklare eller delvis dekker spørsmålet, svar med det du finner \
   dekning for, og si tydelig hva som ikke fremgår av kildene — i stedet for å \
   avvise hele spørsmålet.
6. Bruk avvisningssetningen "Dette finner jeg ikke i de tilgjengelige dokumentene." \
   kun når KONTEKST ikke inneholder noe relevant materiale i det hele tatt. Da skal \
   du svare nøyaktig den setningen og ingenting annet.
7. Ta gjerne med korte ordrette sitater fra kildene når det styrker svaret.
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


def _format_pages(chunk) -> str:
    start = getattr(chunk, "page_start", None)
    end = getattr(chunk, "page_end", None)
    if start is None or end is None:
        return ""
    return f"s. {start}" if start == end else f"s. {start}–{end}"


def parse_citations(answer, chunks, urls: dict[str, str] | None = None) -> str:
    """Render the bibliography block under an answer.

    `urls` maps PDF filename (basename of source_path) → public URL. When a
    chunk's source PDF has a known URL, the document title is rendered as a
    Markdown link so the reader can jump to the original.
    """
    urls = urls or {}
    markers = sorted({int(m) for m in re.findall(r"\[(\d+)\]", answer)})
    valid = [n for n in markers if 1 <= n <= len(chunks)]
    if not valid:
        return ""
    lines = ["**Kilder:**"]
    for n in valid:
        chunk = chunks[n - 1]
        source_path = getattr(chunk, "source_path", None)
        filename = Path(source_path).name if source_path else None
        url = urls.get(filename) if filename else None
        title = f"[{chunk.document}]({url})" if url else chunk.document
        pages = _format_pages(chunk)
        suffix = f" ({pages})" if pages else ""
        lines.append(f"[{n}] {title} — {chunk.section_label}{suffix}")
    return "\n".join(lines)
