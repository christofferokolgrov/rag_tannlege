# Scraper — designvalg

Status: pågående grilling av spec'en `Pr. Go — Raw Schema Spec for Claude Code` (datert 2026-05-05). Dette dokumentet samler beslutningene vi har landet, og åpne spørsmål.

## Bekreftede valg

### 1. Engangs-scrape, ingen tidsserie

- Én kjøring, ett sett output-filer. Ingen `snapshots/YYYY-MM-DD/`-mappe, ingen `latest/`-vy, ingen append-only logg.
- Filer ligger direkte under `data/`: `clinics.csv`, `prices_raw.csv`, `treatments_canonical.yaml`.
- `hentet_dato` er en konstant verdi på tvers av alle rader i kjøringen.
- Test-cases-tabellen i spec § 6 fungerer som golden snapshot for verifisering, ikke som regresjonstest.

### 2. Nullable priser, ingen enhet-normalisering i raw-laget

- `pris_min` og `pris_max` er `integer | null`. Tom celle i CSV når kjeden ikke oppgir tall (f.eks. ren "Etter konsultasjon" uten spread).
- `prisformat`-enum beholdes uendret: `fast`, `fra`, `spread`, `per_halvtime`, `per_dose`, `per_stk`, `etter_konsultasjon`.
- Enheter (`per_dose`, `per_halvtime`, `per_stk`) lagres ærlig — ingen multiplisering eller normalisering i raw-laget.
- Transform-laget bestemmer sammenlignbarhet:
  - Bare `prisformat ∈ {fast, fra, spread}` aggregeres til `prices_canonical_long.pris_fra_min/max`
  - `per_dose` / `per_halvtime` / `per_stk` rapporteres som tillegg eller egne kanoniske IDer (f.eks. `anesthesia_per_dose`)
  - `etter_konsultasjon` med tall behandles som spread; uten tall som `match_kvalitet="n/a"`

### 3. Pseudo-klinikk for sentrale prislister, ikke duplisering

- Spec'ens prosa i § 3 ("dupliseres samme prisrader for hver klinikk") forkastes til fordel for test-cases-modellen i § 6 (`oris_central`, `colosseum_central`).
- `clinics.csv` får én ekstra rad per kjede med sentral prisliste:
  - `colosseum_central`, `kjede=colosseum`, `klinikk_navn="Colosseum (sentral prisliste)"`, `prisliste_struktur=sentral`, `postnummer/by/adresse=null`
  - Tilsvarende `oris_central`.
- Faktiske klinikker (`colosseum_majorstuen`, etc) har:
  - `prisliste_url` peker på den sentrale URL'en
  - **null prisrader** i `prices_raw.csv` med mindre klinikken har egen override-kilde
- HelseSmart-override for spesifikk klinikk: legges som vanlig rad mot den faktiske klinikken med `pris_kilde=helsesmart`.
- Transform-laget gjør LEFT JOIN per kjede: for hver `colosseum_*`-klinikk, trekk priser fra `colosseum_central` UNION egne HelseSmart-rader.
- Begrunnelse: speiler virkeligheten (én prisliste, ikke 25 identiske), single-source-of-truth ved parsing, override-semantikk er eksplisitt.

### 4. Klinikk-discovery via committet manifest

- `data/clinic_discovery.yaml` committet i repo er kilden av sannhet for hvilke klinikker scraperen besøker. Per kjede: liste over (klinikk_navn, klinikk_url, helsesmart_url, kilde).
- Valgfritt discovery-script (kjøres separat, manuelt) scraper kjedenes klinikk-liste-sider og skriver kandidater til `data/clinic_discovery_candidates.yaml`. Diff-es manuelt mot manifestet før commit.
- **Odontia + OC**: discovery kritisk fordi per-klinikk priser. Manifestet må være komplett — fail-hard hvis scraper-target i manifestet ikke kan hentes.
- **Oris**: hopp over JS-rendering. HelseSmart-listen brukes som kandidat-kilde, kryss-sjekkes manuelt mot orisdental.no én gang, resultatet committes til manifestet.
- **Colosseum**: statisk HTML eller HelseSmart, brukes kun til `clinics.csv`-rader (priser kommer fra `colosseum_central`).
- **OralCare AS Trondheim/Tromsø**: ikke prøv å løse via scraping. Flagges i `notes`-kolonnen i `clinics.csv`.
- Begrunnelse: skiller skjør discovery fra kritisk prising, manifestet er auditable, sparer JS-rendering-bryderi for engangs-scope.

### 5. Drop `raw_html_snippet`, cache hele HTML-sider

- Kolonnen `raw_html_snippet` fjernes fra `prices_raw.csv`-skjema.
- Scraperen lagrer hver hentet side til `data/html_cache/<kjede>/<klinikk_slug>.html`. Sentrale prislister: `data/html_cache/<kjede>/_central.html`. HelseSmart-sider: `data/html_cache/helsesmart/<klinikk_slug>.html`.
- Cache committes til repo (~5-10 MB total, engangs-scope).
- Scraperen leser fra cache hvis fil finnes; `--refetch`-flagg tvinger ny henting.
- Begrunnelse: deterministisk re-kjøring uten nettverk, raskere parser-iterasjon, ren CSV uten embedded HTML, full audit-trail.

### 6. `klinikk_id` slug-policy

- Format: `<kjede>__<slug>` (dobbel underscore som separator).
- Kjede-tokens (fastsatt liste): `odontia`, `oris`, `colosseum`, `oc`, `oralcare`, `single`.
- Slug-regler:
  - Lower-case
  - æ→ae, ø→oe, å→aa (norsk konvensjon, beholder leselighet)
  - Andre diakritter strippes (é→e)
  - Mellomrom og bindestrek → `_`
  - Alt ikke-`[a-z0-9_]` strippes
- Eksempler: `odontia__oslo_sentrum`, `odontia__hoenefoss`, `oc__bergen_nord`, `oc__taasen`, `oralcare__linderud`.
- Pseudo-klinikker for sentrale prislister: `oris__central`, `colosseum__central` (slug `central` er reservert).
- `clinic_discovery.yaml`-manifestet har eksplisitt `klinikk_id` per oppføring. Slug-generering er deterministisk hjelpe-funksjon, men endelig ID committes manuelt — kollisjons-håndtering skjer ved authoring (eks. `odontia__oslo_sentrum` vs `odontia__oslo_sentrum_bjorvika`).
- Scraperen validerer ved oppstart: alle IDer unike, alle matcher `^(odontia|oris|colosseum|oc|oralcare|single)__[a-z0-9_]+$`. Brudd = fail-hard.
- **Konsekvens:** test-case-tabellen i spec § 6 må oppdateres. `odontia_oslo-sentrum → odontia__oslo_sentrum` etc. Tabellen er informativ, ikke normativ.

### 7. HelseSmart-fetching: selektiv via konfig + implantat-unntak

- Default: scraperen henter ikke HelseSmart.
- Konfig-fil `data/helsesmart_targets.yaml` lister eksplisitt (klinikk_id, behandlinger, reason). Manuelt kuratert.
- **Implantat-unntak:** for kjeder hvor `treatments_canonical.yaml.implant_with_crown` er tom (Colosseum, OC), forsøk HelseSmart auto-discovery — resultater krever manuell validering før commit.
- `clinics.csv.helsesmart_url` populeres kun når HelseSmart faktisk er brukt som kilde. Ingen speculative URLs.
- HelseSmart-rader merket eksplisitt med `pris_kilde=helsesmart`; aldri blandet med `sentral` eller `klinikk_egen`.
- Cache: én fil per klinikk i `data/html_cache/helsesmart/<klinikk_slug>.html`.
- Begrunnelse: HelseSmart er supplement, ikke primærkilde (spec § 8). Selektivitet hindrer at HelseSmart-spread dominerer min/max-aggregeringer for behandlinger der kjeden selv har klar pris.

### 8. Test-cases-tabellen er informativ baseline med eksplisitt godkjenn-loop

- Spec § 6-tabellen flyttes til `tests/scraper/parser_validation.yaml` (maskinlesbar fixture, ikke pytest).
- Hver entry har `klinikk_id`, `behandling_navn_raw`, `forventet`-blokk (pris_min, pris_max, prisformat), `observert_dato`, `verifisert_av`.
- Validerings-script `tools/validate_scrape.py` kjører etter scrape:
  - **EKSAKT MATCH** → ok
  - **AVVIK** → print diff, åpne `data/html_cache/<kjede>/<klinikk_slug>.html`, krev menneskelig avgjørelse: scraper-bug (fix kode) eller pris-endret (oppdater YAML)
  - **MANGLER** → forventet rad finnes ikke i output. Definitivt scraper- eller manifest-bug.
- Akseptkriterium for "ferdig scrape":
  - Alle 14 fixture-rader gir EKSAKT MATCH eller eksplisitt-godkjent AVVIK med oppdatert forventet
  - Ingen MANGLER
  - `scrape_log.csv` har `status=ok` for alle klinikker i manifestet
- Avvik-godkjenninger committes med klar melding (eks. `chore: parser_validation 1595→1597, verifisert mot HTML 2026-05-08`).
- Alle test-IDer oppdateres til `<kjede>__<slug>`-format fra Q6 før første kjøring.

### 9. Topp-nivå `scraper/`-pakke parallelt med `tannhelse/`

- Mappestruktur:
  ```
  scraper/
    __init__.py, cli.py, config.py, manifest.py, fetch.py,
    slug.py, prisformat.py, log.py, output.py
    parsers/{odontia,oris,colosseum,oc,oralcare,helsesmart}.py
  tools/
    validate_scrape.py
  data/
    clinic_discovery.yaml, helsesmart_targets.yaml, html_cache/
    # output: clinics.csv, prices_raw.csv, treatments_canonical.yaml
  tests/scraper/
    parser_validation.yaml
    test_slug.py, test_prisformat.py, test_manifest.py    # pure helpers TDD
    test_parser_<kjede>_smoke.py                          # smoke mot html_cache
  ```
- `pyproject.toml`: legg til `httpx>=0.27`, `selectolax>=0.3` til deps; `packages = ["tannhelse", "scraper"]`.
- Ingen kryss-imports mellom `tannhelse/` og `scraper/`. Felles `common/` opprettes først hvis noe faktisk skal deles.
- CLI: `uv run python -m scraper {discover,run,validate}`, `--refetch`-flagg ignorerer cache.
- Testing-disciplin: TDD pure helpers (slug, prisformat, manifest-validering); smoke-test parsers mot committed HTML-cache; ikke TDD HTTP-fetch eller end-to-end.
- Begrunnelse: RAG-pakken forblir ren uten scraper-deps; clear cognitive separation; entydige importer; engangs men disciplinert.

### 10. Robots.txt hard gate, identifisert user-agent, ingen ToS-sjekk

- Robots.txt-håndtering i `scraper/fetch.py`:
  - Før første request til et domene, hent `https://<domain>/robots.txt`, parse med `urllib.robotparser`
  - Per URL: hvis eksplisitt `Disallow` på vår path → fail-hard for klinikken, loggføres `status=blocked_robots` i `scrape_log.csv`, scraperen fortsetter med øvrige
  - 404 på robots.txt = ikke disallowed → fortsett
  - `Crawl-delay` overstyrer default 1-req/sec
- User-agent + From-header settes eksplisitt:
  ```
  User-Agent: tannhelse-research-bot/0.1 (+https://github.com/christofferokolgrov/rag_tannlege; ck@drivkapital.no)
  From: ck@drivkapital.no
  ```
- Rate limit: 1 req/sec per domene, eksplisitt `time.sleep` mellom requests (enkelt og åpenbart respektfullt). Respekter `Crawl-delay` om høyere.
- ToS sjekkes ikke. Vi scraper offentlig publisert prisinformasjon med markedsanalytisk formål, engangs, lavt volum — robots.txt + identifiserbar user-agent er tilstrekkelig signal-respekt.
- `scrape_log.csv` per kjøring: klinikk_id, url, status (`ok`, `blocked_robots`, `http_error`, `parse_fail`), responskode, timing.
- Akseptkriterium: ingen `blocked_robots`-rader uten manuelt verifisert overstyring.

### 11. Per-klinikk completeness — A+D automatisert, C manuell for fixture

- `tests/scraper/parser_validation.yaml` utvides med `forventet_min_rader` per klinikk (manuelt observert i HTML-cache):
  ```yaml
  - klinikk_id: odontia__oslo_sentrum
    forventet_min_rader: 40
    priser:
      - behandling_navn_raw: ...
        forventet: { pris_min: 1595, pris_max: 1595, prisformat: fast }
  ```
- **A — antall-rader baseline:** validerings-script feiler hvis `len(prices_raw rader)` < `forventet_min_rader * 0.9` (10% slack).
- **D — HTML-vs-CSV diff:** for hver klinikk telles regex-matches på pris-mønstre i HTML-cache, sammenlignes mot CSV-rader. Stort avvik (>20%) gir advarsel i `scrape_log.csv`. Rough proxy, ikke autoritativ.
- **C — manuell visuell sjekk for de 14 fixture-klinikkene:** åpne HTML-cache og CSV side-by-side, sign-off i commit-melding. ~5 min × 14 klinikker.
- Klinikker utenfor fixture får kun A+D, stoler på parser-konsistens etablert via fixture-klinikker.
- Akseptkriterium utvides: Q8-kriteriene + alle klinikker passerer A + D-advarsler under 20% + 14 fixture-klinikker har manuell sign-off.

### 12. Treatment canonical YAML — scraper-emitter-observert + transform-emitter-coverage + manuell mapping mellom

- **`data/treatments_observed.yaml`** auto-genereres av scraper (en pass over `prices_raw.csv`):
  ```yaml
  odontia:
    - "Årlig kontroll hos tannlege"  (forekomst: 12 klinikker)
    - "Plastfylling, liten"  (forekomst: 1 klinikk)   # synonym-avvik
  ```
  Forekomst-telling avdekker synonymer og per-klinikk-avvik.
- **`data/treatments_canonical.yaml`** manuelt vedlikeholdt. Spec § 4-utkastet committes som v1. Etter første scrape: review `treatments_observed.yaml` → oppdater canonical med synonymer / nye behandlinger. Endringer committes med klar melding.
- Canonical YAML utvides med metadata:
  ```yaml
  meta:
    versjon: 1
    sist_oppdatert: 2026-05-08
    scope: "kurven for prissammenligning fase 1"
    ikke_kanonisk_men_scrapes:
      - "Bedøvelse (per_dose tillegg)"
      - "Forbruksvarer (per_stk tillegg)"
  ```
  `ikke_kanonisk_men_scrapes` hvitlister behandlinger som ikke skal flagges som "uncovered" i transform.
- **Transform-laget produserer `data/transform_coverage_report.txt`:** matchet/uncovered per kanonisk × klinikk og per `behandling_navn_raw`. Manuell TODO-liste for å forbedre canonical YAML.
- **Scraper bryr seg ikke om mapping.** `prices_raw.csv` er rå navn. Holder scrape-logikken ren.
- Akseptkriterium utvides:
  - `treatments_observed.yaml` idempotent (samme input → samme output)
  - Transform coverage >90% match for `lag=1` kanoniske behandlinger på tvers av klinikker
  - Uncovered-listen reviewes manuelt før prissammenligning publiseres — mappe eller hvitliste
- Begrunnelse: skiller "hva publiserte kjeden" fra "hva er sammenlignbart"; forekomst-telling avdekker synonymer elegant; manuelt + maskinassistert riktig blanding for one-shot.

## Status

Alle hoved-grenene i designtreet er løst. Spec'en er klar for nedbryting i implementerings-issues (anbefalt: tracer-bullet vertikale slices, slik som den eksisterende RAG-pipelinen).

Neste steg: bryte denne spec'en + design-beslutninger ned i issues på `christofferokolgrov/rag_tannlege` (skill `to-issues`), eller skrive en eksplisitt PRD før det (skill `to-prd`).
