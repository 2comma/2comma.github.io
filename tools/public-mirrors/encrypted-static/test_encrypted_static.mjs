import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  DEFAULT_CHUNK_SIZE,
  RECOMMENDED_PBKDF2_ITERATIONS,
  chunkUrl,
  decryptChunk,
  decryptFile,
  decryptManifest,
  encryptArchive,
  pageBase,
} from "./codec.mjs";
import { SYNTHETIC_PASSWORD } from "./synthetic-password.mjs";

const here = dirname(fileURLToPath(import.meta.url));
const png = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
  "base64",
);
const pdf = Buffer.from(
  "%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\nsynthetic-marker\n",
  "utf8",
);

function assertFails(promise) {
  return promise.then(
    () => assert.fail("expected failure"),
    (error) => {
      assert.equal(error.message, "decrypt failed");
    },
  );
}

const archive = await encryptArchive(
  [
    { path: "assets/sample.png", type: "image/png", data: png },
    { path: "docs/sample.pdf", type: "application/pdf", data: pdf },
    { path: "assets/wide.bin", type: "application/octet-stream", data: new Uint8Array(DEFAULT_CHUNK_SIZE + 100) },
  ],
  SYNTHETIC_PASSWORD,
  { profile: "synthetic-test", iterations: 10_000, chunkSize: DEFAULT_CHUNK_SIZE },
);

assert.equal(RECOMMENDED_PBKDF2_ITERATIONS >= 600_000, true);
await assert.rejects(
  () => encryptArchive([{ path: "a.txt", type: "text/plain", data: new Uint8Array() }], "x", {
    profile: "production",
    iterations: 10_000,
  }),
  /production archives require/,
);

const opened = await decryptManifest(archive.manifest, SYNTHETIC_PASSWORD);
assert.deepEqual(opened.manifest.files.map((file) => file.path), [
  "assets/sample.png",
  "docs/sample.pdf",
  "assets/wide.bin",
]);
const pngOut = await decryptFile(archive.blobs, opened.key, opened.manifest.files[0]);
const pdfOut = await decryptFile(archive.blobs, opened.key, opened.manifest.files[1]);
const wideOut = await decryptFile(archive.blobs, opened.key, opened.manifest.files[2]);
assert.equal(Buffer.from(pngOut).equals(png), true);
assert.equal(Buffer.from(pngOut.subarray(0, 8)).toString("hex"), "89504e470d0a1a0a");
assert.equal(Buffer.from(pdfOut.subarray(0, 5)).toString("utf8"), "%PDF-");
assert.equal(Buffer.from(pdfOut).includes(Buffer.from("synthetic-marker")), true);
assert.equal(wideOut.length, DEFAULT_CHUNK_SIZE + 100);

await assertFails(decryptManifest(archive.manifest, "wrong-password"));
const tampered = new Uint8Array(archive.manifest);
tampered[tampered.length - 2] ^= 0xff;
await assertFails(decryptManifest(tampered, SYNTHETIC_PASSWORD));
await assert.rejects(
  () => decryptManifest(archive.manifest.subarray(0, archive.manifest.length - 8), SYNTHETIC_PASSWORD),
  /truncated archive/,
);

const pngFile = opened.manifest.files[0];
const blob = archive.blobs.get(`${pngFile.id}.0`);
assert.equal(Buffer.from(blob).includes(Buffer.from("synthetic-marker")), false);
assert.equal(Buffer.from(blob.subarray(0, 8)).toString("hex") === "89504e470d0a1a0a", false);
assert.equal(Buffer.from(blob).includes(Buffer.from(SYNTHETIC_PASSWORD)), false);
assert.equal(Buffer.from(archive.manifest).includes(Buffer.from("assets/sample.png")), false);
const flipped = new Uint8Array(blob);
flipped[flipped.length - 3] ^= 0xff;
await assertFails(decryptChunk(flipped, opened.key, pngFile.id, 0));
await assert.rejects(
  () => decryptChunk(blob.subarray(0, blob.length - 10), opened.key, pngFile.id, 0),
  /truncated blob/,
);
const wide = opened.manifest.files[2];
assert.equal(wide.chunks, 2);
for (const part of archive.blobs.values()) {
  assert.ok(part.length < 100 * 1024 * 1024);
  assert.ok(part.length <= DEFAULT_CHUNK_SIZE + 64);
  assert.equal(Buffer.from(part).includes(Buffer.from("%PDF")), false);
  assert.equal(Buffer.from(part).includes(Buffer.from("synthetic-marker")), false);
}

assert.equal(pageBase("https://2comma.github.io/read/").pathname, "/read/");
assert.equal(pageBase("https://2comma.github.io/read").pathname, "/read/");
assert.equal(pageBase("https://2comma.github.io/read/index.html").pathname, "/read/");
assert.equal(chunkUrl("https://2comma.github.io/read/", "abc", 0), "https://2comma.github.io/read/blobs/abc.0.bin");
assert.equal(chunkUrl("https://2comma.github.io/trade/index.html", "abc", 1), "https://2comma.github.io/trade/blobs/abc.1.bin");

const viewer = readFileSync(join(here, "viewer.js"), "utf8");
const page = readFileSync(join(here, "viewer.html"), "utf8");
for (const banned of ["localStorage", "sessionStorage", "indexedDB", "serviceWorker", "document.cookie", SYNTHETIC_PASSWORD]) {
  assert.equal(viewer.includes(banned), false, banned);
  assert.equal(page.includes(banned), false, banned);
}
assert.match(page, /worker-src 'none'/);
assert.match(page, /script-src 'self'/);

console.log("encrypted-static tests passed");
