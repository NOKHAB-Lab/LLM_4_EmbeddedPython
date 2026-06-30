# Dataset License

**Raspberry Pi Hardware-Aware Python Code Dataset**

This dataset has mixed provenance, so licensing is layered. Please read all three parts.

---

## 1. Dataset compilation & original contributions — CC BY 4.0

The following are © the dataset authors and released under
**Creative Commons Attribution 4.0 International (CC BY 4.0)**
<https://creativecommons.org/licenses/by/4.0/>:

- the **compilation, structure, and selection** of the dataset;
- all **prompts** (instruction text);
- all **synthetically generated completions** (records with **no** `provenance.source_repo`,
  i.e. not derived from a third-party repository);
- all **annotations and metadata** (`categories`, `complexity`, `tags`, `provenance`, etc.).

You may share and adapt these with attribution to the dataset authors.

> Alternative: if you prefer a code-style license for the contributed code portions,
> the authors also offer them under the **MIT License** at your option. Pick one.

## 2. Third-party code under open-source licenses — original terms apply

Completions with a `provenance.source_repo` and
`provenance.license_class` = `permissive` are **derived from third-party open-source
repositories** (MIT / BSD / Apache-2.0 / Unlicense). They remain under their original
licenses. The required copyright and license notices are reproduced in
**[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)**.

If you redistribute a completion that contains a substantial part of one of these works,
you **must retain** the corresponding notice from `THIRD_PARTY_NOTICES.md`. Each such record
also carries `provenance.license` and `provenance.source_url`.

> Note: GPL/AGPL/LGPL (copyleft) source code was **removed** from this release and is not included.

## 3. Third-party code with no verified license — not included in this release

Community-sourced completions derived from public repositories that **published no license**
(or whose license could not be verified) are **withheld from this release**. They will be
added in a future version once their licenses are verified or permission is obtained from
the original authors.

**If you are an author of such code and wish it included, removed, or relicensed, contact
Muhammad Saqib Saeed `<musae@sdu.dk>` (or open an issue on this repository).**

Every record distributed in this release is flagged
`metadata.provenance.redistributable = true`.

---

## Disclaimer

This dataset is provided "as is", without warranty of any kind. It contains
machine-generated and third-party code that has not been audited for security or
correctness; do not deploy completions to hardware without review. The dataset authors
are not liable for any use of this data.

This file is guidance, not legal advice. For a public/commercial release, confirm the
licensing with your institution or a qualified professional.

_Maintainer: Muhammad Saqib Saeed `<musae@sdu.dk>`, University of Southern Denmark · Version: 1.0 · See DATASHEET.md for full details._
