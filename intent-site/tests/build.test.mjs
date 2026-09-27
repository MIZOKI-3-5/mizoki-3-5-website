import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const output = new URL("../../intent-dist/index.html", import.meta.url);
const LINK_TAG = /<link(?=[\s/>])[^>]*>/gi;
const ATTRIBUTE = /(?:^|\s)([^\s"'<>/=]+)\s*=\s*(["'])(.*?)\2/g;
const RAW_TEXT_ELEMENT =
  /<(script|style|template|noscript|textarea|title|xmp|iframe|noembed)(?=[\s/>])[^>]*>[\s\S]*?(?:<\/\1\s*>|$)/gi;

function activeMarkup(html) {
  return html
    .replace(/<!--[\s\S]*?(?:-->|$)/g, "")
    .replace(RAW_TEXT_ELEMENT, "");
}

function attributes(tag) {
  const found = [];
  for (const match of tag.matchAll(ATTRIBUTE)) {
    found.push([match[1].toLowerCase(), match[3]]);
  }
  return found;
}

function assertIntentCanonical(html) {
  const canonicalLinks = (activeMarkup(html).match(LINK_TAG) ?? [])
    .map((tag) => ({ tag, attrs: attributes(tag) }))
    .filter(({ attrs }) =>
      attrs.some(
        ([name, value]) =>
          name === "rel" && value.toLowerCase().split(/\s+/).includes("canonical"),
      ),
    );

  assert.equal(
    canonicalLinks.length,
    1,
    "build must contain exactly one canonical link",
  );
  assert.equal(
    canonicalLinks[0].attrs.filter(([name]) => name === "rel").length,
    1,
    "canonical link must contain exactly one rel",
  );
  assert.equal(
    canonicalLinks[0].attrs.filter(([name]) => name === "href").length,
    1,
    "canonical link must contain exactly one href",
  );
  assert.equal(
    canonicalLinks[0].attrs.find(([name]) => name === "href")?.[1],
    "https://mizoki3.com/intent",
    "canonical link must point exactly to https://mizoki3.com/intent",
  );
}

test("canonical URL must belong to the canonical link", () => {
  assert.throws(() =>
    assertIntentCanonical(
      '<link rel="canonical" href="https://wrong.example/">' +
        '<a href="https://mizoki3.com/intent">decoy</a>',
    ),
  );
});

test("duplicate canonical links are rejected", () => {
  assert.throws(() =>
    assertIntentCanonical(
      '<link rel="canonical" href="https://mizoki3.com/intent">' +
        '<link href="https://mizoki3.com/intent" rel="canonical">',
    ),
  );
});

test("duplicate canonical attributes are rejected", () => {
  assert.throws(() =>
    assertIntentCanonical(
      '<link rel="canonical" href="https://wrong.example/" ' +
        'href="https://mizoki3.com/intent">',
    ),
  );
  assert.throws(() =>
    assertIntentCanonical(
      '<link rel="stylesheet" rel="canonical" ' +
        'href="https://mizoki3.com/intent">',
    ),
  );
});

test("canonical attributes may be reordered and use single quotes", () => {
  assert.doesNotThrow(() =>
    assertIntentCanonical(
      "<link href='https://mizoki3.com/intent' rel='canonical'>",
    ),
  );
});

test("prefixed attributes and non-link tags cannot impersonate a canonical", () => {
  assert.throws(() =>
    assertIntentCanonical(
      '<link data-rel="canonical" data-href="https://mizoki3.com/intent">' +
        '<linkage rel="canonical" href="https://mizoki3.com/intent">',
    ),
  );
});

test("comments and raw-text elements cannot provide the canonical", () => {
  assert.throws(() =>
    assertIntentCanonical(
      '<!-- <link rel="canonical" href="https://mizoki3.com/intent"> -->' +
        '<script>"<link rel=\\"canonical\\" href=\\"https://mizoki3.com/intent\\">"</script>',
    ),
  );
  assert.throws(() =>
    assertIntentCanonical(
      '<script>"<link rel=\\"canonical\\" href=\\"https://mizoki3.com/intent\\">"',
    ),
  );
});

test("build is isolated to the /intent path", async () => {
  const html = await readFile(output, "utf8");

  // Keep the contract resilient to quote choice and harmless whitespace or
  // formatter changes in generated HTML.
  assertIntentCanonical(html);
  assert.match(html, /(?:src|href)\s*=\s*["']\/intent\/assets\//i);
  assert.doesNotMatch(html, /codex-preview/i);
  assert.doesNotMatch(
    html,
    /\bhref\s*=\s*["']\/favicon\.ico(?:[?#][^"']*)?["']/i,
  );
});
