# Known Issues

Issues found in `data/dataset_clean.jsonl` after the v1.1 release, and what was done
about them in v1.2. Anyone reproducing the paper's results should read this: **the
published corpus differs from the corpus the models were trained on.** The differences
are listed below.

## 1. Off-domain records carrying a third-party credential (removed)

All records sourced from `stijojoseph/AI-JARVIS-PERSONAL-ASSISTANT` (files `api.py` and
`api1.py`) were removed. They were a small set of distinct programs, each present with
several reworded prompts.

Two independent problems:

- **Off-domain.** They are Google Custom Search / BeautifulSoup web-scraping tasks with
  no hardware element, in a corpus of Raspberry Pi hardware-interface code. Most of them
  contained no hardware-related token at all — by far the highest such ratio of any source
  repository in the corpus.
- **Credential residue.** Many of them carried the upstream author's real Google Custom
  Search Engine ID (`cx`) in the prompt, the completion, or both. The redaction pass that
  replaced the adjacent API key with `YOUR_API_KEY` did not replace the `cx` on the
  following line. The upstream code is MIT-licensed and redistributable, but that licence
  does not extend to the author's account identifier.

No live API key was ever present in the released file or in any commit in this
repository's history (verified with `git grep` across all revisions).

The attribution entry for this repository was removed from `THIRD_PARTY_NOTICES.md`.

Removed record ids:

  `llm4ep-583bffa53873`  `llm4ep-6c29ac229c67`  `llm4ep-caa6512e5192`
  `llm4ep-416c01dee625`  `llm4ep-f5d75c648f43`  `llm4ep-6fadea32de6b`
  `llm4ep-884f0d067949`  `llm4ep-1b85fd54406c`  `llm4ep-881b74103864`
  `llm4ep-fdcd50ef159c`  `llm4ep-e9e87981fb52`  `llm4ep-35e775d8a387`
  `llm4ep-a83642091cbf`  `llm4ep-bc1d606e2d85`  `llm4ep-56128ca8b787`
  `llm4ep-1b68e703558b`  `llm4ep-9baa9dc5ad39`  `llm4ep-ba558076afbd`
  `llm4ep-cc4723b46398`  `llm4ep-a8bd9f335667`  `llm4ep-d917595a358f`
  `llm4ep-5a7904e837fc`  `llm4ep-810e15a4aa11`  `llm4ep-00a92bbf08a6`
  `llm4ep-81717be0a595`  `llm4ep-8260be91a72d`  `llm4ep-2d87ff4557db`
  `llm4ep-6805f21e9e5e`  `llm4ep-5e53614f1dc9`  `llm4ep-b8d2dbef39b3`
  `llm4ep-4cd8fdea44dd`  `llm4ep-4d1e9639e13d`  `llm4ep-b5f4a7cdae38`
  `llm4ep-cd6f891ce0b2`  `llm4ep-489180541f42`  `llm4ep-f61e5ecb24eb`
  `llm4ep-179db74cb963`  `llm4ep-bbf888ce0b6d`  `llm4ep-35882022e0fc`
  `llm4ep-4d25e6955fbe`  `llm4ep-67b595936ae8`  `llm4ep-e22c43c34dac`
  `llm4ep-518e1f7bc982`  `llm4ep-9b7f0430a96f`  `llm4ep-ec78fa0dc28d`
  `llm4ep-c77999eeaeb2`  `llm4ep-11597c980c49`  `llm4ep-f2dc81d6164d`
  `llm4ep-04a2d250851a`  `llm4ep-0e5eb98202c9`  `llm4ep-e22d24ba02d6`
  `llm4ep-b3f4eae26f80`  `llm4ep-e85547a32610`  `llm4ep-e9bd7366c33a`
  `llm4ep-19480e9b6f9f`  `llm4ep-94b9ebd1810c`  `llm4ep-57ce6f2a7669`
  `llm4ep-0c937c1a238f`  `llm4ep-31ced87e2b6b`  `llm4ep-1494fcdf9c38`
  `llm4ep-15af34a4d70e`  `llm4ep-a8d0e99beed5`  `llm4ep-b02b1f2f1385`
  `llm4ep-f6832f2a2f5c`  `llm4ep-7017ef55153d`  `llm4ep-2d4db016851a`
  `llm4ep-b3c3dc51eeb9`  `llm4ep-cbf43b2108cf`  `llm4ep-db32937c6da2`
  `llm4ep-8b806c215950`  `llm4ep-46b0d44d5693`  `llm4ep-c1dfacaaa47e`

## 2. Broken `task` metadata on community-sourced records (set to `null`)

The community-ingest step asked a model to describe each scraped source file and parsed a
title out of a Markdown response such as `**Task Description:**\nThis project...`. The parser
kept the literal `**` marker. It failed three ways:

| Value | Outcome |
|---|---|
| `**` alone, description lost | set to `null` |
| `**` followed by an intact description | prefix stripped, text kept |
| other asterisk- or whitespace-only values | set to `null` |

The lost descriptions are not recoverable from the released file, and no title was
fabricated to replace them. Affected records now have `task: null`. `categories` is
populated on every record and is the field to filter on.

Synthetic records were unaffected — they get their titles from a template in
`pipeline/code_generator.py`, not from a parsed model response. The community-ingest
script is not part of this repository.

## 3. Redundant `tags` field (removed)

`tags` was empty on every community-sourced record and inconsistent on the rest. It
duplicated `categories`, which is populated on all records with a controlled label set.
The field was removed from every record rather than backfilled.

## 4. Inconsistent `complexity` vocabulary (normalised)

The field used seven overlapping values. It now takes exactly one of three:

| Was | Now |
|---|---|
| `beginner`, `beginner_basic`, `basic` | `basic` |
| `medium`, `intermediate` | `intermediate` |
| `high`, `advanced` | `advanced` |

## 5. Attribution entries for repositories contributing no records (removed)

`THIRD_PARTY_NOTICES.md` listed three repositories with no records in the released file:
`anooshd7/DrugDispenser`, `calapsss/face_detection_tutorial` and
`adafruit/Adafruit_Python_ADXL345`. These predate v1.2 and were removed. The file now
lists only repositories that are actually present in the data.

## Not changed

- `prompt` and `completion` — the training fields — were not modified by any of the above,
  other than by the removal of the records in issue 1.
