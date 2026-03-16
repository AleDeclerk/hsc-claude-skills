# HSC Claude Code Skills — Veritas Automata

Domain skills for Claude Code that provide verified regulatory and clinical standards context for the HSC Orchestration Agent at the LSU Stem Cell Lab.

Each skill encapsulates reference material, code generators, and validation logic drawn from authoritative sources (ICCBBA, HL7 International, LOINC, FACT/JACIE, FDA 21 CFR Part 1271). When installed, Claude Code automatically activates the relevant skill based on task context — no manual prompting required.

## Skills

| Skill | Status | Covers |
|-------|--------|--------|
| [isbt-128](./isbt-128/) | ✅ Done | ISBT 128 DIN validation, parsing, check character (ISO 7064 Mod 37,2), FIN structure per ICCBBA spec |
| [hl7-healthcare](./hl7-healthcare/) | ✅ Done | HL7 v2 message generation (ADT^A04, ORM^O01, ORU^R01), MLLP transport, FDA 21 CFR 1271 anonymity checks |
| [loinc-hsc-panel](./loinc-hsc-panel/) | ✅ Done | 31 verified LOINC codes for HSC product test panels, FDA 21 CFR 1271.85 donor screening, default 15-test panel, known bug detection (58410-2 ≠ CD34) |
| [fact-jacie-audit](./fact-jacie-audit/) | ✅ Done | 34-event FACT/JACIE chain of custody (receipt → infusion → disposal), inspector checklist, 10 missing event gap analysis, 5 known bugs with fixes, FDA 21 CFR 1271.55 retention |

## Usage

Each folder is a standalone Claude Code skill. Install by pointing Claude Code at the skill directory:

```bash
# Install a single skill (e.g. isbt-128)
claude skills add /path/to/hsc-claude-skills/isbt-128

# Or clone the repo and install from there
git clone https://github.com/AleDeclerk/hsc-claude-skills.git
claude skills add ./hsc-claude-skills/hl7-healthcare
```

Once installed, Claude Code will automatically detect and activate the skill when your task matches its domain — for example, any mention of DIN validation triggers `isbt-128`, and any HL7 message work triggers `hl7-healthcare`.

## License

MIT
