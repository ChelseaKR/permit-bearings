/**
 * Load the shipped `assets/demo.js` under Node so its logic can be unit
 * tested.
 *
 * Why the real file and not a copy: `assets/demo.js` is the second
 * implementation of this product's rule logic. It carries the screening
 * matcher, the staleness rule, the ordinance scanner, and the review clocks,
 * and it is the code a visitor actually runs. A port kept in a test would
 * prove nothing about what is deployed. `tests/test_conformance_browser_parity.py`
 * already makes that argument for the scanner; this module generalises it so
 * the rest of the file can be reached the same way.
 *
 * How: the file is a browser script with top-level DOM access, so it is
 * evaluated in a `node:vm` context holding a deliberately small DOM. The stub
 * is not a DOM implementation and does not try to be. Elements are inert
 * unless a test asks for one by id through `elements`, which is what keeps a
 * test honest about which parts of the page it is standing in for.
 */

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

/** A single stubbed element. Records what the script writes to it. */
export function makeElement(id = "") {
  const listeners = new Map();
  return {
    id,
    value: "",
    checked: false,
    innerHTML: "",
    textContent: "",
    open: false,
    disabled: false,
    hidden: false,
    dataset: {},
    style: {},
    children: [],
    options: [],
    classList: {
      add() {},
      remove() {},
      toggle() {},
      contains: () => false,
    },
    listeners,
    addEventListener(type, handler) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(handler);
    },
    removeEventListener() {},
    /** Run every handler registered for `type`. */
    dispatch(type, event = {}) {
      for (const handler of listeners.get(type) ?? []) handler(event);
    },
    append() {},
    appendChild() {},
    insertAdjacentHTML() {},
    remove() {},
    focus() {},
    click() {
      this.dispatch("click", { target: this });
    },
    scrollIntoView() {},
    setAttribute() {},
    removeAttribute() {},
    getAttribute: () => null,
    closest: () => null,
    matches: () => false,
    querySelector: () => null,
    querySelectorAll: () => [],
  };
}

/**
 * Evaluate `assets/demo.js` and return its global scope.
 *
 * @param {object} options
 * @param {Record<string, object>} options.elements Elements the script should
 *   find by id. Anything not listed resolves to null, exactly as it does on a
 *   page that does not carry that control.
 * @param {string} options.page Value of `document.body.dataset.page`, which
 *   `detectActivePage` reads. `demo.js` gates whole blocks on it.
 * @param {string} options.pathname The page the script believes it is on.
 * @returns {{get: (name: string) => unknown, elements: object,
 *   consoleMessages: {level: string, text: string}[]}} `get` reads any
 *   top-level binding, including the `const` ones a vm context keeps in its
 *   lexical scope rather than on the global object.
 */
export function loadDemo({
  elements = {},
  page = "project",
  pathname = "/check.html",
} = {}) {
  const source = readFileSync(join(ROOT, "assets", "demo.js"), "utf8");
  const inert = makeElement();
  const bodyStub = makeElement("body");
  bodyStub.dataset.page = page;
  const documentStub = {
    documentElement: inert,
    body: bodyStub,
    head: inert,
    title: "",
    readyState: "complete",
    getElementById: (id) => elements[id] ?? null,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => makeElement(),
    addEventListener() {},
    removeEventListener() {},
  };
  const windowStub = {
    addEventListener() {},
    removeEventListener() {},
    location: { search: "", href: `http://localhost${pathname}`, pathname },
    matchMedia: () => ({ matches: false, addEventListener() {} }),
    print() {},
    scrollTo() {},
  };
  const consoleMessages = [];
  const captureConsole = {};
  for (const level of ["log", "info", "warn", "error", "debug"]) {
    captureConsole[level] = (...args) =>
      consoleMessages.push({ level, text: args.map(String).join(" ") });
  }
  const sandbox = {
    document: documentStub,
    window: windowStub,
    location: windowStub.location,
    navigator: { language: "en" },
    console: captureConsole,
    // No unit test may reach the network. `demo.js` catches its own bundle
    // load failure, so this exercises that path rather than skipping it.
    fetch: () => Promise.reject(new Error("no network in unit tests")),
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    crypto: globalThis.crypto,
    setTimeout,
    clearTimeout,
    queueMicrotask,
    Intl,
  };
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;
  const context = vm.createContext(sandbox);
  new vm.Script(source, { filename: "assets/demo.js" }).runInContext(context);
  return {
    elements,
    consoleMessages,
    get(name) {
      return vm.runInContext(name, context);
    },
    /** Evaluate an expression against the loaded scope. */
    evaluate(expression) {
      return vm.runInContext(expression, context);
    },
  };
}

/** Read a committed JSON artifact, so fixtures cite the same data Python does. */
export function readJson(...parts) {
  return JSON.parse(readFileSync(join(ROOT, ...parts), "utf8"));
}
