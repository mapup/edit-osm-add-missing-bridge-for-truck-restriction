#!/usr/bin/env python3
"""Resolve CycloneDX component licenses to concrete SPDX identifiers.

Dependency-Track resolves a ``licenses[].expression`` only when the expression is
a single SPDX ID. A compound expression such as ``Apache-2.0 OR BSD-3-Clause`` is
stored but left unresolved, and the license report then counts the component as
"No License Metadata". Separately, packages that publish no PEP 639
``License-Expression`` end up with a bare ``licenses[].license.name`` -- either a
trove classifier or nothing at all.

This script runs over the merged bom.json after generation and before upload:

1. Splits SPDX expressions into concrete ``licenses[].license.id`` entries,
   keeping the original expression in the component's ``properties`` so nothing
   is lost for audit.
2. Maps unambiguous trove classifiers onto SPDX IDs via NAME_TO_SPDX.
3. Applies PURL_OVERRIDES for packages whose license cannot be derived from
   their metadata, each justified by a source-of-truth comment. cyclonedx-py
   v7 dropped support for the legacy free-text "License:" header, so packages
   that still rely on it land here until they adopt PEP 639 upstream.

The result is validated against the CycloneDX schema before it is written; if
normalization produced something invalid the changes are discarded and the
original bom.json is left in place, so a bug here can never cost us the scan.

Anything it cannot resolve is reported as a GitHub Actions warning annotation and
left in the BOM untouched. The script does NOT fail the build: the SBOM upload
runs in the same job, and failing here would stop Dependency-Track receiving any
SBOM at all -- strictly worse than uploading one with a few unresolved licenses.
Pass --strict to exit non-zero instead, for a dedicated gate that has nothing
downstream of it.
"""

from __future__ import annotations

import json
import os
import re
import sys

# Trove classifier / license name -> SPDX ID.
#
# cyclonedx-py emits a package's trove classifiers as licenses[].license.name
# when the package has no PEP 639 License-Expression. Dependency-Track cannot
# match those to SPDX, so it mints a synthetic license instead -- the tollmatch
# report currently contains IDs like
# "License----OSI-Approved----Apache-Software-License". Mapping them to real
# SPDX IDs cleans that up.
#
# Rule for adding an entry: the classifier string must determine exactly ONE
# SPDX identifier on its own. Version-ambiguous classifiers are deliberately
# absent and must be handled per package in PURL_OVERRIDES instead:
#   "License :: OSI Approved :: BSD License"          -> BSD-2/3/4-Clause?
#   "License :: OSI Approved :: Apache Software License" -> Apache-1.0/1.1/2.0?
#   "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)"
#                                                     -> LGPL-2.0/2.1/3.0?
# Guessing a version on those would be a legal judgement, not a data fix.
NAME_TO_SPDX = {
    "license :: osi approved :: mit license": "MIT",
    "license :: osi approved :: mit no attribution license (mit-0)": "MIT-0",
    "license :: osi approved :: isc license (iscl)": "ISC",
    "license :: osi approved :: mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "license :: osi approved :: mozilla public license 1.1 (mpl 1.1)": "MPL-1.1",
    # PSF-2.0 is the only Python Software Foundation license SPDX defines.
    "license :: osi approved :: python software foundation license": "PSF-2.0",
    "license :: osi approved :: the unlicense (unlicense)": "Unlicense",
}

# purl -> SPDX ID, for packages whose license cannot be derived from their
# metadata: no PEP 639 expression, and either no classifier at all or one that
# is version-ambiguous. The key may include the version or omit it; the
# versionless form is tried second so an entry survives a version bump.
#
# Every entry must be verified against that package's own LICENSE file or
# readme, and must say where it was found.
PURL_OVERRIDES = {
    # Declares only the legacy "License: BSD" header, which cyclonedx-py v7 no
    # longer reads, and ships no LICENSE file in the wheel. antlr/antlr4
    # LICENSE.txt is the three-clause text (retain notice + reproduce notice +
    # no endorsement).
    "pkg:pypi/antlr4-python3-runtime": "BSD-3-Clause",
    # Classifier is the version-ambiguous "GNU Library or Lesser General Public
    # License (LGPL)". psycopg/psycopg2 LICENSE resolves it: "either version 3
    # of the License, or (at your option) any later version", plus an OpenSSL
    # linking exception. This is a genuine weak-copyleft dependency -- resolving
    # it moves it into the Weak Copyleft bucket, it does not make it disappear.
    "pkg:pypi/psycopg2-binary": "LGPL-3.0-or-later",
    "pkg:pypi/psycopg2": "LGPL-3.0-or-later",
    # package.json has no "license" field, the published tarball contains no
    # LICENSE file, and github.com/mrrama/node-bunyan-prettystream 404s. The
    # package's own readme.md carries the full MIT text under a "# License"
    # heading beginning "(The MIT License)".
    "pkg:npm/bunyan-prettystream": "MIT",
    # The rest publish a legacy free-text "License:" header that cyclonedx-py
    # v7 no longer reads, leaving them with no license at all. Each value below
    # is that header cross-checked against the LICENSE file in the wheel.
    "pkg:pypi/asttokens": "Apache-2.0",           # "License: Apache 2.0"; LICENSE is the Apache 2.0 text
    "pkg:pypi/bleach": "Apache-2.0",              # LICENSE: "Licensed under the Apache License, Version 2.0"
    "pkg:pypi/cligj": "BSD-3-Clause",             # "License: BSD"; LICENSE carries the no-endorsement 3rd clause
    "pkg:pypi/multidict": "Apache-2.0",           # "License: Apache License 2.0"
    "pkg:pypi/overrides": "Apache-2.0",           # "License: Apache License, Version 2.0"
    "pkg:pypi/partd": "BSD-3-Clause",             # "License: BSD"; LICENSE.txt carries the no-endorsement 3rd clause
    "pkg:pypi/protobuf": "BSD-3-Clause",          # "License: 3-Clause BSD License"
    "pkg:pypi/setuptools": "MIT",                 # no License header at all; pypa/setuptools LICENSE is the MIT text
    "pkg:pypi/uritemplate": "BSD-3-Clause OR Apache-2.0",  # "License: BSD 3-Clause OR Apache-2.0"; LICENSE offers either
    # These publish only the version-ambiguous trove classifier
    # "License :: OSI Approved :: BSD License". Dependency-Track cannot map that
    # to SPDX, so it mints a synthetic ID such as
    # "License----OSI-Approved----BSD-License" -- resolved, but junk. Each entry
    # below was read off the LICENSE file shipped in that package's own wheel:
    # three clauses (retain notice + reproduce notice + no endorsement) is
    # BSD-3-Clause, two clauses is BSD-2-Clause.
    "pkg:pypi/click-plugins": "BSD-3-Clause",     # LICENSE.txt is headed "New BSD License"
    "pkg:pypi/fiona": "BSD-3-Clause",             # LICENSE.txt carries the no-endorsement 3rd clause
    "pkg:pypi/geopandas": "BSD-3-Clause",         # LICENSE.txt carries the no-endorsement 3rd clause
    "pkg:pypi/jinja2": "BSD-3-Clause",            # LICENSE.txt carries the no-endorsement 3rd clause
    "pkg:pypi/networkx": "BSD-3-Clause",          # LICENSE.txt: "distributed with the 3-clause BSD license"
    # Two clauses only -- no endorsement clause -- so this one is NOT 3-Clause.
    "pkg:pypi/osmium": "BSD-2-Clause",
    "pkg:pypi/pandas": "BSD-3-Clause",            # LICENSE carries the no-endorsement 3rd clause
    # Genuinely dual: LICENSE applies Apache-2.0 to contributions after
    # 2017-12-01 and BSD-3-Clause to the remainder, so both apply at once (AND,
    # not OR -- it is not a choice of license).
    "pkg:pypi/python-dateutil": "Apache-2.0 AND BSD-3-Clause",
    # shapely itself is BSD-3-Clause (LICENSE.txt has the no-endorsement
    # clause). Its wheels also vendor libgeos, whose LICENSE_GEOS is LGPL-2.1;
    # that is a bundled binary, not a separate SBOM component, so it is out of
    # scope here and noted in the PR instead.
    "pkg:pypi/shapely": "BSD-3-Clause",
}

ORIGINAL_EXPRESSION_PROPERTY = "mapup:original-license-expression"

# SPDX IDs are the leaves of an expression once operators and parentheses are
# stripped. "+" (e.g. GPL-2.0+) and "." are part of the identifier grammar.
#
# Operators are matched case-SENSITIVELY and must be surrounded by whitespace.
# SPDX defines AND/OR/WITH as uppercase, and identifiers embed the lowercase
# words: a case-insensitive \bOR\b happily splits "GPL-3.0-or-later" into
# "GPL-3.0-" and "-later", because the hyphens either side of "or" are word
# boundaries. That produced two bogus license IDs and a 400 from
# Dependency-Track's schema validation.
_OPERATORS = re.compile(r"\s+(?:AND|OR)\s+")
_WITH = re.compile(r"\s+WITH\s+")
# Must start and end alphanumeric, so a mis-split leaving a dangling hyphen
# ("GPL-3.0-", "-later") is rejected rather than emitted as a license ID.
_SPDX_ID = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9.+-]*[A-Za-z0-9+])?$")


def split_expression(expression: str) -> list[str]:
    """Return the distinct SPDX IDs in an SPDX license expression.

    Returns an empty list if the expression carries an SPDX exception, or if any
    leaf does not look like an SPDX ID, so that the caller leaves the original
    expression untouched rather than asserting a license the component does not
    actually have.
    """
    ids: list[str] = []
    # Parentheses become whitespace so operator delimiters survive, e.g.
    # "(MIT OR GPL-3.0-or-later)" -> " MIT OR GPL-3.0-or-later ".
    for part in _OPERATORS.split(expression.replace("(", " ").replace(")", " ")):
        part = part.strip()
        if not part:
            continue
        # An SPDX exception materially changes the terms -- "GPL-2.0-only WITH
        # Classpath-exception-2.0" is not "GPL-2.0-only" -- and CycloneDX has no
        # license.id that carries one. Bail out so the caller keeps the original
        # expression verbatim rather than asserting a stricter license than the
        # component actually has.
        if _WITH.search(part):
            return []
        if not _SPDX_ID.match(part):
            return []
        if part not in ids:
            ids.append(part)
    return ids


def validate(bom: dict, spec_version: str) -> str | None:
    """Validate a BOM against the CycloneDX schema. Returns an error, or None.

    Returns None when cyclonedx-python-lib is not importable, so the script
    still works under a bare interpreter -- validation is a safety net, not a
    hard requirement.
    """
    try:
        from cyclonedx.schema import SchemaVersion
        from cyclonedx.validation.json import JsonValidator
    except ImportError:
        return None
    try:
        version = SchemaVersion.from_version(spec_version)
    except Exception:
        return None
    error = JsonValidator(version).validate_str(json.dumps(bom))
    return str(error) if error is not None else None


def lookup_override(purl: str) -> str | None:
    """Resolve a purl against PURL_OVERRIDES, exact match first, then versionless."""
    if not purl:
        return None
    if purl in PURL_OVERRIDES:
        return PURL_OVERRIDES[purl]
    return PURL_OVERRIDES.get(purl.split("@", 1)[0])


def add_property(component: dict, name: str, value: str) -> None:
    properties = component.setdefault("properties", [])
    if not any(p.get("name") == name and p.get("value") == value for p in properties):
        properties.append({"name": name, "value": value})


def normalize_component(component: dict, stats: dict) -> None:
    """Rewrite one component's licenses in place."""
    licenses = component.get("licenses") or []
    normalized: list[dict] = []

    for entry in licenses:
        expression = entry.get("expression")
        if expression:
            ids = split_expression(expression)
            if not ids:
                normalized.append(entry)
                continue
            if len(ids) == 1 and ids[0] == expression.strip():
                # Already a bare SPDX ID; Dependency-Track resolves it as-is,
                # but an explicit license.id is unambiguous.
                normalized.append({"license": {"id": ids[0]}})
            else:
                add_property(component, ORIGINAL_EXPRESSION_PROPERTY, expression)
                stats["expressions_split"] += 1
                for spdx_id in ids:
                    normalized.append({"license": {"id": spdx_id}})
            continue

        license_obj = entry.get("license")
        if not license_obj:
            normalized.append(entry)
            continue
        if license_obj.get("id"):
            normalized.append(entry)
            continue

        name = (license_obj.get("name") or "").strip()
        mapped = NAME_TO_SPDX.get(name.lower())
        if mapped:
            stats["names_mapped"] += 1
            rewritten = {k: v for k, v in license_obj.items() if k != "name"}
            rewritten["id"] = mapped
            add_property(component, "mapup:original-license-name", name)
            normalized.append({**entry, "license": rewritten})
        else:
            normalized.append(entry)

    # Deduplicate while preserving order; splitting an expression that repeats a
    # license, or merging partial SBOMs, can produce duplicates.
    deduped: list[dict] = []
    for entry in normalized:
        if entry not in deduped:
            deduped.append(entry)

    # Apply an override whenever the component has no SPDX ID of its own. A
    # version-ambiguous trove classifier (psycopg2-binary's LGPL) counts as
    # "no SPDX ID" even though Dependency-Track will happily invent a license
    # from it -- the whole point of the override is to replace that guess with
    # a verified identifier.
    if not has_spdx_identifier(deduped):
        override = lookup_override(component.get("purl", ""))
        if override:
            stats["purl_overrides"] += 1
            # An override may be a dual license ("BSD-3-Clause OR Apache-2.0"),
            # so run it through the same splitter as an upstream expression.
            override_ids = split_expression(override)
            if len(override_ids) > 1:
                add_property(component, ORIGINAL_EXPRESSION_PROPERTY, override)
            if override_ids:
                deduped = [{"license": {"id": i}} for i in override_ids]
            else:
                deduped = [{"expression": override}]

    if deduped:
        component["licenses"] = deduped
    else:
        component.pop("licenses", None)


def has_spdx_identifier(licenses: list[dict]) -> bool:
    """True if any entry carries a real SPDX ID or expression."""
    return any(
        entry.get("expression") or (entry.get("license") or {}).get("id")
        for entry in licenses
    )


def has_any_license(licenses: list[dict]) -> bool:
    """True if the component declares a license in any form Dependency-Track can use.

    Deliberately looser than has_spdx_identifier: Dependency-Track resolves a
    bare licenses[].license.name too (it synthesizes a license from trove
    classifier strings such as "License :: OSI Approved :: Apache Software
    License"). Those are not what gets reported as "No License Metadata", so
    warning about them would be crying wolf on packages that already work.
    """
    return any(
        entry.get("expression")
        or (entry.get("license") or {}).get("id")
        or (entry.get("license") or {}).get("name")
        for entry in licenses
    )


def walk(components, stats):
    """Yield every component, including nested ones."""
    for component in components or []:
        yield component
        yield from walk(component.get("components"), stats)


def main(argv: list[str]) -> int:
    args = [a for a in argv[1:] if not a.startswith("-")]
    strict = "--strict" in argv[1:]
    if len(args) != 1:
        print(f"usage: {argv[0]} [--strict] <bom.json>", file=sys.stderr)
        return 2
    path = args[0]

    with open(path, encoding="utf-8") as handle:
        bom = json.load(handle)

    stats = {"expressions_split": 0, "names_mapped": 0, "purl_overrides": 0}
    components = list(walk(bom.get("components"), stats))

    before = sum(1 for c in components if not has_any_license(c.get("licenses") or []))
    spdx_before = sum(1 for c in components if not has_spdx_identifier(c.get("licenses") or []))
    for component in components:
        normalize_component(component, stats)
    unresolved = [c for c in components if not has_any_license(c.get("licenses") or [])]
    no_spdx = [c for c in components if not has_spdx_identifier(c.get("licenses") or [])]

    # Never hand a BOM we broke to the upload step. Dependency-Track validates
    # against the CycloneDX schema and answers 400 for anything malformed, which
    # would drop the whole scan -- so if normalization produced something
    # invalid, throw our changes away and leave the original bom.json in place.
    schema_error = validate(bom, bom.get("specVersion", ""))
    if schema_error is not None:
        sys.stdout.flush()
        print("")
        print("::error title=SBOM normalization produced an invalid BOM::"
              "discarding changes, uploading the original bom.json")
        print(f"   {schema_error[:1500]}", file=sys.stderr)
        return 1 if strict else 0

    # Write-then-rename: a partial write (disk full, interrupted run) must not
    # leave a truncated bom.json behind, because the step is continue-on-error
    # and the upload runs regardless. os.replace is atomic within a filesystem.
    temporary_path = f"{path}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as handle:
        json.dump(bom, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary_path, path)

    print(f"🔧 Normalized licenses in {path}")
    print(f"   components                    : {len(components)}")
    print(f"   no license at all, before     : {before}")
    print(f"   no SPDX id, before            : {spdx_before}")
    print(f"   compound expressions split    : {stats['expressions_split']}")
    print(f"   legacy license names mapped   : {stats['names_mapped']}")
    print(f"   purl overrides applied        : {stats['purl_overrides']}")
    print(f"   no license at all, after      : {len(unresolved)}")
    print(f"   no SPDX id, after             : {len(no_spdx)} (name-only; Dependency-Track still resolves these)")

    if unresolved:
        print("")
        print(f"⚠️  {len(unresolved)} component(s) declare no license at all:")
        for component in unresolved:
            purl = component.get("purl") or f"{component.get('name')}@{component.get('version')}"
            declared = json.dumps(component.get("licenses") or [], separators=(",", ":"))
            print(f"   - {purl}  declared={declared}")
            # Surfaces in the Actions run summary without failing the job.
            print(f"::warning title=Unlicensed SBOM component::{purl} declares no license")
        print("")
        print(
            "These are uploaded as-is; Dependency-Track will report them as missing license\n"
            "metadata. To fix one, determine its license from the package's own LICENSE file\n"
            "or readme, then add it to NAME_TO_SPDX (legacy license name) or PURL_OVERRIDES\n"
            "(no upstream metadata) in .github/scripts/normalize_sbom_licenses.py, with a\n"
            "comment recording where the license was found."
        )
        # Deliberately not a failure. The Dependency-Track upload runs later in
        # this same job; failing here would mean no SBOM is uploaded at all,
        # which is worse than an SBOM with a few unresolved licenses.
        return 1 if strict else 0

    print("✅ Every component declares a license.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
