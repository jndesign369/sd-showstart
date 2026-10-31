# San Diego Shows venue coverage audit

Audit date: October 30, 2026. This compares the 36 saved target entries with
the starter kit's registered collectors, parsing rules, source caches, and
merged output. It is an implementation audit, not a fresh scrape or a test of
the user's deployed GitHub site.

The source caches were last collected October 24, 2026. The merged snapshot
was rebuilt October 30, 2026, without network collection. Counts below refer
to that saved snapshot and do not establish complete or current coverage.

## Summary

| Status | Target entries | Meaning |
|---|---:|---|
| Dedicated collector | 6 | A registered collector targets this venue's calendar and has saved listings. |
| Partial cross-listing | 4 | Saved listings exist through Belly Up, not a dedicated venue collector. |
| Parser support only | 1 | Code recognizes this venue, but neither the source cache nor merged snapshot contains its shows. |
| No implemented coverage | 25 | No registered collection path or saved listings establish coverage; includes two Petco Park event-label entries. |
| Total | 36 | All user-supplied entries retained. |

Ten target entries have listings in the saved snapshot. That is not the same
as ten complete calendars. Soda Bar is an additional existing collector
outside the supplied 36-entry list and remains enabled.

## Entry-by-entry assessment

Names below preserve the user's target list. “No collector” means work is
needed before claiming coverage; it does not mean a venue's website is
unscrapable.

| Target entry | Current status | Evidence in the kit | Additional work |
|---|---|---|---|
| 3OZ Dive Club, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Balboa Theatre, SD | Partial cross-listing | Belly Up supplies 1 snapshot listing as “Balboa Theatre - San Diego.” | Add venue/theatre calendar coverage; the saved cross-listed row also has no official venue URL. |
| Belly Up Tavern, Solana Beach | Dedicated collector | `bellyup`: 113 snapshot listings at Belly Up. | Retain and monitor; counts do not prove completeness. |
| Cal Coast Credit Union Open Air Theatre, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Casbah, SD | Partial cross-listing | Belly Up supplies 1 snapshot listing. README records a blocked earlier direct-calendar attempt. | Broader source needed; recheck direct feasibility before choosing an approach. |
| Dia De Los Deftones, Petco Park, SD | No collector; label review | No registered source or saved rows; supplied name includes Petco Park. | Preserve entry, verify whether it should be an event/series under Petco Park, then collect its dates and lineup. |
| Dizzy's Jazz, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Harrah's Resort Southern California, Valley Center | No collector | No registered source or saved venue rows. | Add a collection source. |
| The Holding Company, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| House of Blues, SD | No collector; prior blocker | No registered source or saved venue rows; README records an earlier event-list rendering failure. | Recheck direct feasibility or add an alternate permitted source. |
| Humphreys Backstage Live, SD | No collector | Existing `humphreys` code targets Concerts by the Bay only. | Add separate Backstage Live coverage; do not equate the two calendars. |
| Humphreys Concerts By the Bay, SD | Dedicated collector | `humphreys`: 2 snapshot listings. | Retain and monitor. |
| Jacobs Music Center, SD | Parser support only | `radyshell` explicitly recognizes this venue, with a parser test; no source-cache or snapshot rows. | Check the calendar's actual scope and add/extend collection if it does not expose Jacobs Music Center shows. |
| The Kensington Club, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Lou Lou's, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| The Magnolia, El Cajon | No collector | No registered source or saved venue rows. | Add a collection source. |
| Music Box, SD | Partial cross-listing | Belly Up supplies 38 snapshot listings. | Compare with the venue's full calendar before deciding whether a dedicated scraper is necessary. |
| North Island Credit Union Amphitheatre, Chula Vista | No collector | No registered source or saved venue rows. | Add a collection source. |
| Nova SD, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| The Observatory North Park, SD | Dedicated collector | `observatory`: 22 snapshot listings, plus 3 cross-listed Belly Up rows. | Retain; audit duplicates and conflicting times across sources before expanding imports. |
| Pacific Highlands Ranch, SD | No collector | No registered source or saved venue rows. | Confirm the specific event organizer/location and add its calendar source. |
| Pechanga Arena, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Pechanga Resort & Casino, Temecula | No collector | No registered source or saved venue rows. | Add a collection source; preserve the user's selected Temecula scope. |
| Petco Park, SD | No collector | No registered source or saved venue rows. | Add concert/event coverage and distinguish venue identity from event labels. |
| Quartyard, SD | Dedicated collector | `quartyard`: 21 snapshot listings. | Retain and monitor. |
| Queen Bee's, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| The Rady Shell, SD | Dedicated collector | `radyshell`: 11 snapshot listings as “The Rady Shell at Jacobs Park.” | Retain and monitor. |
| San Diego Civic Theatre, SD | No collector | No registered source or saved venue rows. | Add a collection source; evaluate shared collection with Balboa Theatre after checking source structure. |
| Snapdragon Stadium, SD | No collector | No registered source or saved venue rows. | Add a collection source and filter for music events. |
| SOMA, SD | Dedicated collector | `soma`: 28 snapshot listings as “SOMA San Diego.” | Retain and monitor. |
| The Sound, Del Mar | Partial cross-listing | Belly Up supplies 21 snapshot listings. | Compare with the venue's full calendar before deciding whether a dedicated scraper is necessary. |
| Temper Fest, Petco Park, SD | No collector; label review | No registered source or saved rows; supplied name includes Petco Park. | Preserve entry, verify whether it should be an event/series under Petco Park, then collect its dates and lineup. |
| Til-Two Club, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| The Tower Bar, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Viejas Arena, SD | No collector | No registered source or saved venue rows. | Add a collection source. |
| Whistle Stop, SD | No collector | No registered source or saved venue rows. | Add a collection source. |

## Recommended expansion approach

- **Broad discovery first:** Evaluate the previously supplied ConcertsSD
  reference as an additional discovery collector rather than immediately
  writing one new scraper for every gap. It is not enabled in this release.
  Its band-index links must not become official artist links, and listings
  without verified ticket destinations must not be labeled “buy tickets.”
- **Identity and duplicate handling:** Map venue aliases explicitly while
  preserving original source names. The current merge uses venue, title, date,
  and time; differing titles or conflicting times can leave multiple rows.
  Do not silently merge potentially different performances.
- **Targeted source additions:** Use the uncovered entries above to select
  official calendar collectors for missing shows and ticket enrichment. Treat
  Humphreys Backstage Live separately from Concerts by the Bay, and verify
  Jacobs Music Center coverage rather than assuming parser support is enough.
- **Partial-calendar checks:** Compare Music Box and The Sound with their own
  calendars before adding redundant scrapers. Balboa and Casbah have only
  one saved cross-listed show apiece, so their existing coverage is especially
  limited.
- **Historical blockers:** Casbah's challenge and House of Blues' rendering
  issue are prior observations recorded in the kit, not newly verified
  current limitations. Neither venue has a dedicated enabled collector.
- **Accuracy remains the gate:** Validate show versus doors times, exact
  artist identities, direct ticket destinations, and official venue URLs.
  Unknown artist websites remain plain text.

## Audit inputs and boundaries

Local inputs inspected: `venues.json`, `run.py`, `README.md`, all seven
registered scraper modules, `data/*.json`, `shows.json`, and the Jacobs Music
Center parser test. Local filenames identify audit inputs, not external
citations.

No venue websites were re-scraped for this audit. No API was added, no new
collector was enabled, and neither the public page nor the user's GitHub
repository was changed.
