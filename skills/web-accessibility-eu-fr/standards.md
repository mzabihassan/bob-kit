# Standards and obligations (status: October 2026)

Facts below come from the official texts (W3C, accessibilite.numerique.gouv.fr, Directive (EU) 2019/882, ETSI). Versions move: when the user's decision depends on a date or a citation status, re-check the source. This is engineering guidance, not legal advice; route legal questions to the compliance team.

## Which reference applies

| Context | Mandatory reference | Also required |
| --- | --- | --- |
| French public bodies and the other organisations of article 47 of loi n° 2005-102 (including companies with at least 250 M€ turnover in France) | **RGAA 4.1.2**: 106 criteria in 13 themes, built on WCAG 2.1 AA | Accessibility statement, multi-year plan and annual action plan, link to the statement from every page |
| Products and services covered by the **European Accessibility Act** (Directive (EU) 2019/882): e-commerce, consumer banking, e-books, passenger transport services, electronic communications, access to audiovisual media services; computers, operating systems, smartphones, ATMs, ticketing and check-in terminals, e-readers | EAA accessibility requirements (Annex I); conformity is presumed through the harmonised standard **EN 301 549** (web content: clause 9 = WCAG A + AA) | Information on how the service meets the requirements (Art. 13 and Annex V), public, in written and oral form, kept while the service runs. In France: loi n° 2023-171 and décret n° 2023-931 |
| EU public sector outside France (Web Accessibility Directive 2016/2102) | EN 301 549 through national law | National accessibility statement |
| Anything else (contracts, internal tools) | Usually WCAG 2.1 AA by contract | Recommend WCAG 2.2 AA |

EAA dates: applies since **28 June 2025**. Microenterprises providing services (fewer than 10 persons and annual turnover or balance sheet not above 2 M€) are exempt for those services, never for products. Transition: services may keep using products lawfully used before that date until 28 June 2030; service contracts agreed before 28 June 2025 run until they expire, at most five years; self-service terminals may stay in use until the end of their economic life, at most 20 years.

## Versions in force

- **WCAG 2.2** (W3C Recommendation, 5 October 2023): adds six A/AA criteria and makes 4.1.1 Parsing obsolete. WCAG 2.1 AA stays the basis of RGAA 4.1.2 and EN 301 549 V3.2.1.
- **EN 301 549 V3.2.1**: the version giving presumption of conformity today (WCAG 2.1 AA). **V4.1.1** was published on 2 September 2026 by ETSI, CEN and CENELEC: WCAG 2.2 A/AA plus an EAA mapping. It has legal effect only once cited in the Official Journal of the EU; check that status before calling it mandatory.
- **RGAA 4.1.2** (last updated 18 April 2023) is in force. RGAA 5 is being written, publication planned for the end of 2026 (official site); work done on 4.1.2 stays valid.

## WCAG 2.2 delta (target it now, mandatory once V4.1.1 is cited or RGAA 5 applies)

| Criterion | Level | What to check |
| --- | --- | --- |
| 2.4.11 Focus Not Obscured (Minimum) | AA | The focused element is not entirely hidden by sticky headers, cookie banners, chat widgets |
| 2.5.7 Dragging Movements | AA | Every drag (sliders, sortable lists, maps) has a single-pointer alternative |
| 2.5.8 Target Size (Minimum) | AA | Targets at least 24×24 CSS px, or enough spacing; inline links and essential cases excepted |
| 3.2.6 Consistent Help | A | Help mechanisms (contact, chat, FAQ) in the same relative order across pages |
| 3.3.7 Redundant Entry | A | Information already entered in the same process is pre-filled or selectable |
| 3.3.8 Accessible Authentication (Minimum) | AA | No cognitive test to log in: allow paste and password managers, offer an alternative to puzzles |

RGAA 4.1.2 still contains 8.1 and 8.2 (valid code), mapped to the now-obsolete 4.1.1: for an RGAA audit they remain mandatory.

## Mandatory or recommended

| Item | Status |
| --- | --- |
| WCAG 2.1 A and AA criteria | Mandatory (RGAA, EN 301 549 V3.2.1, EAA) |
| RGAA criteria, including those axe tags `best-practice` + `RGAAv4` (e.g. `region` → 9.2) | Mandatory in an RGAA context |
| WCAG 2.2 new A/AA criteria | Recommended now; mandatory with EN 301 549 V4.1.1 once cited, and expected in RGAA 5 |
| AAA criteria, axe `best-practice` rules without RGAA tag | Recommended |
| Accessibility statement and multi-year plan (France), service information (EAA) | Mandatory where the law applies; produced by the organisation, not by the code |

## RGAA figures (France)

- **Rate** = validated criteria ÷ applicable criteria. A criterion is validated only if it is validated on every page of the sample, and applicable if it applies to at least one page. The average rate is the mean of the page rates.
- **Status**: *totalement conforme* when all criteria are met, *partiellement conforme* from 50 %, *non conforme* below 50 % or without a valid audit.
- **Sample**: at least, when they exist, the home, contact, legal notice, accessibility, sitemap, help and authentication pages, plus randomly chosen pages making up at least 10 % of the sample. Add the key user journeys (search, form, checkout, account).
- The statement is reachable from the home page and every page, updated after a substantial change or redesign and at most three years after publication.
- **Only a manual audit following the RGAA method gives a rate.** An automated scan never yields a compliance status.
