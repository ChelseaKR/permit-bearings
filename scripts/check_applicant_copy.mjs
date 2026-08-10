#!/usr/bin/env node

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import vm from "node:vm";
import {fileURLToPath} from "node:url";

const CATALOG_START = "const STRINGS = {";
const CATALOG_END = "\n};\nlet lang";
const ARGUMENT_TOKEN = /⟪ARG_[0-9]+⟫/g;
const PRESERVED_TOKEN = /(⟪ARG_[0-9]+⟫|\{\{[^}]+\}\}|\{[A-Za-z][^}]*\}|%[0-9]*\$?[A-Za-z]|https?:\/\/[^\s]+)/g;
const STATIC_PLACEHOLDER = /\{\{[^{}]+\}\}|\{[A-Za-z][A-Za-z0-9_.-]*\}|%(?:[0-9]+\$)?[A-Za-z]/g;
const OPTION_COLLECTION_PATHS = new Set([
  "STRINGS.types",
  "STRINGS.tri",
  "STRINGS.primaryOptions",
  "STRINGS.aduFormOptions",
]);

function valueKind(value) {
  if (Array.isArray(value)) return "array";
  if (value === null) return "null";
  return typeof value;
}

function occurrences(value, token) {
  return value.split(token).length - 1;
}

function issue(code, catalogPath, message) {
  return {code, path: catalogPath, message};
}

function nonblankFormatterOutput(value, locale, probe, catalogPath, state) {
  if (typeof value !== "string") {
    state.issues.push(issue(
      "function_output_type",
      catalogPath,
      `${locale} formatter returned ${valueKind(value)} for the ${probe} probe.`,
    ));
    return false;
  }
  if (!value.trim()) {
    state.issues.push(issue(
      "blank_function_output",
      catalogPath,
      `${locale} formatter returned blank copy for the ${probe} probe.`,
    ));
    return false;
  }
  return true;
}

export function extractCatalog(sourceText) {
  const start = sourceText.indexOf(CATALOG_START);
  if (start === -1 || sourceText.indexOf(CATALOG_START, start + 1) !== -1) {
    throw new Error("expected exactly one applicant-copy catalog start marker");
  }
  const end = sourceText.indexOf(CATALOG_END, start);
  if (end === -1 || sourceText.indexOf(CATALOG_END, end + 1) !== -1) {
    throw new Error("expected exactly one applicant-copy catalog end marker");
  }
  const catalogSource = `${sourceText.slice(start, end + 3)}\nSTRINGS`;
  const catalog = vm.runInNewContext(catalogSource, Object.create(null), {
    timeout: 1_000,
  });
  if (!catalog || valueKind(catalog) !== "object") {
    throw new Error("applicant-copy catalog did not evaluate to an object");
  }
  return catalog;
}

function validateFunctionPair(english, spanish, catalogPath, state) {
  if (english.length !== spanish.length) {
    state.issues.push(issue(
      "function_arity_mismatch",
      catalogPath,
      `English accepts ${english.length} argument(s); Spanish accepts ${spanish.length}.`,
    ));
    return;
  }

  const argumentsForProbe = Array.from(
    {length: english.length},
    (_, index) => `⟪ARG_${index + 1}⟫`,
  );
  let probeOutputs;
  try {
    probeOutputs = [
      {
        name: "placeholder",
        english: english(...argumentsForProbe),
        spanish: spanish(...argumentsForProbe),
      },
      {
        name: "singular",
        english: english(...argumentsForProbe.map(() => 1)),
        spanish: spanish(...argumentsForProbe.map(() => 1)),
      },
      {
        name: "plural",
        english: english(...argumentsForProbe.map(() => 2)),
        spanish: spanish(...argumentsForProbe.map(() => 2)),
      },
    ];
  } catch (error) {
    state.issues.push(issue(
      "function_probe_failed",
      catalogPath,
      `Catalog formatter failed a deterministic probe: ${error.message}`,
    ));
    return;
  }
  let allOutputsValid = true;
  for (const probe of probeOutputs) {
    allOutputsValid = nonblankFormatterOutput(
      probe.english,
      "English",
      probe.name,
      catalogPath,
      state,
    ) && allOutputsValid;
    allOutputsValid = nonblankFormatterOutput(
      probe.spanish,
      "Spanish",
      probe.name,
      catalogPath,
      state,
    ) && allOutputsValid;
  }
  if (!allOutputsValid) return;

  const englishOutput = probeOutputs[0].english;
  const spanishOutput = probeOutputs[0].spanish;

  for (const token of argumentsForProbe) {
    const englishCount = occurrences(englishOutput, token);
    const spanishCount = occurrences(spanishOutput, token);
    state.placeholderChecks += 1;
    if (englishCount === 0 || spanishCount === 0 || englishCount !== spanishCount) {
      state.issues.push(issue(
        "placeholder_mismatch",
        catalogPath,
        `${token} appears ${englishCount} time(s) in English and ${spanishCount} time(s) in Spanish.`,
      ));
    }
  }
  state.functionCount += 1;
  state.copySamples.push(...probeOutputs.map(probe => probe.english));
}

function placeholderCounts(value) {
  const counts = new Map();
  for (const token of value.match(STATIC_PLACEHOLDER) || []) {
    counts.set(token, (counts.get(token) || 0) + 1);
  }
  return counts;
}

function validateStaticPlaceholders(english, spanish, catalogPath, state) {
  const englishCounts = placeholderCounts(english);
  const spanishCounts = placeholderCounts(spanish);
  const tokens = [...new Set([...englishCounts.keys(), ...spanishCounts.keys()])]
    .sort();
  for (const token of tokens) {
    const englishCount = englishCounts.get(token) || 0;
    const spanishCount = spanishCounts.get(token) || 0;
    state.placeholderChecks += 1;
    if (englishCount !== spanishCount) {
      state.issues.push(issue(
        "static_placeholder_mismatch",
        catalogPath,
        `${token} appears ${englishCount} time(s) in English and ${spanishCount} time(s) in Spanish.`,
      ));
    }
  }
}

function compareOptionCollection(english, spanish, catalogPath, state) {
  if (english.length !== spanish.length) {
    state.issues.push(issue(
      "array_length_mismatch",
      catalogPath,
      `English has ${english.length} option(s); Spanish has ${spanish.length}.`,
    ));
    return;
  }
  english.forEach((englishOption, index) => {
    const spanishOption = spanish[index];
    const optionPath = `${catalogPath}[${index}]`;
    if (!Array.isArray(englishOption) || !Array.isArray(spanishOption)
        || englishOption.length !== 2 || spanishOption.length !== 2
        || typeof englishOption[0] !== "string"
        || typeof spanishOption[0] !== "string") {
      state.issues.push(issue(
        "option_shape_mismatch",
        optionPath,
        "Declared option collections require [stable identifier, localized label] pairs.",
      ));
      return;
    }
    state.identifierChecks += 1;
    if (englishOption[0] !== spanishOption[0]) {
      state.issues.push(issue(
        "option_identifier_mismatch",
        `${optionPath}[0]`,
        `English uses ${JSON.stringify(englishOption[0])}; Spanish uses ${JSON.stringify(spanishOption[0])}.`,
      ));
    }
    compareCatalogValues(
      englishOption[1],
      spanishOption[1],
      `${optionPath}[1]`,
      state,
    );
  });
}

function compareCatalogValues(english, spanish, catalogPath, state) {
  const englishKind = valueKind(english);
  const spanishKind = valueKind(spanish);
  if (englishKind !== spanishKind) {
    state.issues.push(issue(
      "value_shape_mismatch",
      catalogPath,
      `English is ${englishKind}; Spanish is ${spanishKind}.`,
    ));
    return;
  }

  if (englishKind === "string") {
    if (!english.trim() || !spanish.trim()) {
      state.issues.push(issue(
        "blank_copy",
        catalogPath,
        "English and Spanish copy must both be nonblank.",
      ));
    }
    validateStaticPlaceholders(english, spanish, catalogPath, state);
    state.stringCount += 1;
    state.copySamples.push(english);
    return;
  }

  if (englishKind === "function") {
    validateFunctionPair(english, spanish, catalogPath, state);
    return;
  }

  if (englishKind === "array") {
    if (OPTION_COLLECTION_PATHS.has(catalogPath)) {
      compareOptionCollection(english, spanish, catalogPath, state);
      return;
    }
    if (english.length !== spanish.length) {
      state.issues.push(issue(
        "array_length_mismatch",
        catalogPath,
        `English has ${english.length} item(s); Spanish has ${spanish.length}.`,
      ));
      return;
    }
    english.forEach((value, index) => {
      compareCatalogValues(
        value,
        spanish[index],
        `${catalogPath}[${index}]`,
        state,
      );
    });
    return;
  }

  if (englishKind === "object") {
    const englishKeys = Object.keys(english);
    const spanishKeys = Object.keys(spanish);
    const allKeys = [...new Set([...englishKeys, ...spanishKeys])];
    for (const key of allKeys) {
      if (!Object.hasOwn(english, key)) {
        state.issues.push(issue(
          "missing_english_key",
          `${catalogPath}.${key}`,
          "Key exists only in Spanish.",
        ));
      } else if (!Object.hasOwn(spanish, key)) {
        state.issues.push(issue(
          "missing_spanish_key",
          `${catalogPath}.${key}`,
          "Key exists only in English.",
        ));
      } else {
        compareCatalogValues(
          english[key],
          spanish[key],
          `${catalogPath}.${key}`,
          state,
        );
      }
    }
    if (englishKeys.join("\u0000") !== spanishKeys.join("\u0000")) {
      state.issues.push(issue(
        "key_order_mismatch",
        catalogPath,
        "English and Spanish keys must use the same order.",
      ));
    }
    return;
  }

  state.issues.push(issue(
    "unsupported_value_type",
    catalogPath,
    `Catalog values cannot use ${englishKind}.`,
  ));
}

const ACCENTS = new Map(Object.entries({
  a: "áa", A: "ÁA", e: "ée", E: "ÉE", i: "íi", I: "ÍI",
  o: "óo", O: "ÓO", u: "úu", U: "ÚU", y: "ýy", Y: "ÝY",
}));

export function pseudoLocalize(value) {
  const parts = value.split(PRESERVED_TOKEN);
  const transformed = parts.map(part => {
    if (part.match(PRESERVED_TOKEN)?.[0] === part) return part;
    return [...part].map(character => ACCENTS.get(character) || character).join("");
  }).join("");
  return `［!! ${transformed} !!］`;
}

function validatePseudoLocalization(copySamples, state) {
  let sourceCharacters = 0;
  let pseudoCharacters = 0;
  let preservedTokens = 0;
  for (const sample of copySamples) {
    const pseudo = pseudoLocalize(sample);
    sourceCharacters += sample.length;
    pseudoCharacters += pseudo.length;
    for (const token of sample.match(ARGUMENT_TOKEN) || []) {
      preservedTokens += 1;
      if (occurrences(pseudo, token) !== occurrences(sample, token)) {
        state.issues.push(issue(
          "pseudolocale_placeholder_changed",
          "pseudolocale",
          `${token} was not preserved by pseudolocalization.`,
        ));
      }
    }
  }
  const expansionRatio = sourceCharacters
    ? pseudoCharacters / sourceCharacters : 0;
  if (expansionRatio < 1.2) {
    state.issues.push(issue(
      "pseudolocale_expansion_too_small",
      "pseudolocale",
      `Aggregate expansion ratio ${expansionRatio.toFixed(3)} is below 1.2.`,
    ));
  }
  return {
    status: state.issues.some(item => item.code.startsWith("pseudolocale_"))
      ? "fail" : "pass",
    strings_checked: copySamples.length,
    placeholders_preserved: preservedTokens,
    generated_catalog: false,
    rendered_layout: false,
    mode: "copy_leaf_expansion_test",
    source_characters: sourceCharacters,
    pseudo_characters: pseudoCharacters,
    expansion_ratio: Number(expansionRatio.toFixed(3)),
  };
}

export function validateCatalog(catalog) {
  const state = {
    issues: [],
    stringCount: 0,
    functionCount: 0,
    placeholderChecks: 0,
    identifierChecks: 0,
    copySamples: [],
  };
  const localeKeys = Object.keys(catalog);
  if (localeKeys.join("\u0000") !== "en\u0000es") {
    state.issues.push(issue(
      "locale_set_mismatch",
      "STRINGS",
      `Expected exactly en and es; found ${localeKeys.join(", ") || "none"}.`,
    ));
  }
  if (catalog.en && catalog.es) {
    compareCatalogValues(catalog.en, catalog.es, "STRINGS", state);
  }
  const pseudolocalization = validatePseudoLocalization(state.copySamples, state);
  return {
    status: state.issues.length ? "fail" : "pass",
    locales: localeKeys,
    catalog_keys: catalog.en ? Object.keys(catalog.en).length : 0,
    string_values: state.stringCount,
    formatter_values: state.functionCount,
    placeholder_checks: state.placeholderChecks,
    option_identifier_checks: state.identifierChecks,
    pseudolocalization,
    issues: state.issues,
    claim_boundary: {
      semantic_translation_review: "not_evaluated",
      spanish_applicant_readiness: "not_claimed",
      layout_compatibility: "not_evaluated",
    },
  };
}

function parseArguments(argv) {
  const options = {
    source: path.resolve(process.cwd(), "assets/demo.js"),
    json: false,
  };
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--json") {
      options.json = true;
    } else if (argument === "--source") {
      index += 1;
      if (!argv[index]) throw new Error("--source requires a path");
      options.source = path.resolve(argv[index]);
    } else {
      throw new Error(`unknown argument: ${argument}`);
    }
  }
  return options;
}

export function checkApplicantCopy(sourcePath) {
  const sourceText = fs.readFileSync(sourcePath, "utf8");
  const catalog = extractCatalog(sourceText);
  return {
    schema_version: 1,
    source_sha256: `sha256:${crypto.createHash("sha256").update(sourceText).digest("hex")}`,
    ...validateCatalog(catalog),
  };
}

function main() {
  let options;
  let result;
  try {
    options = parseArguments(process.argv.slice(2));
    result = checkApplicantCopy(options.source);
  } catch (error) {
    result = {
      schema_version: 1,
      status: "fail",
      issues: [issue("catalog_load_failed", "STRINGS", error.message)],
      claim_boundary: {
        semantic_translation_review: "not_evaluated",
        spanish_applicant_readiness: "not_claimed",
        layout_compatibility: "not_evaluated",
      },
    };
  }

  if (options?.json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  } else if (result.status === "pass") {
    process.stdout.write(
      `applicant-copy contract: pass (${result.catalog_keys} keys; `
      + `${result.placeholder_checks} placeholders; copy expansion `
      + `${result.pseudolocalization.expansion_ratio}x)\n`,
    );
  } else {
    for (const item of result.issues) {
      process.stderr.write(`${item.code} at ${item.path}: ${item.message}\n`);
    }
  }
  process.exitCode = result.status === "pass" ? 0 : 1;
}

const invokedPath = process.argv[1] ? path.resolve(process.argv[1]) : "";
if (invokedPath === fileURLToPath(import.meta.url)) main();
