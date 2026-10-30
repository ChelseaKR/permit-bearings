// CQ-49: the public pages are checked against the HTML specification
// (content models, required attributes, nesting) by html-validate's
// `standard` preset. The `recommended` preset adds style preferences on top
// (an uppercase DOCTYPE, native elements over ARIA roles); those are not spec
// conformance, and the pages' ARIA is held by the axe suite instead.
export default {
  extends: ["html-validate:standard"],
};
