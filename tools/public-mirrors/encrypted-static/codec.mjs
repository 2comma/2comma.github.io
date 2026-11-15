/**
 * Synthetic archive format using only WebCrypto primitives.
 * AES-256-GCM for authenticated encryption. PBKDF2-HMAC-SHA-256 for the KDF.
 * This is not a custom cipher and it is not a security audit.
 *
 * A wrong password or any tampering fails the GCM tag. There is no separate
 * password hash. The live Read/Trade gate password must never be used here.
 */

export const MAGIC = "YNWAENC1";
export const VERSION = 1;
export const KDF_PBKDF2_SHA256 = 1;
export const RECOMMENDED_PBKDF2_ITERATIONS = 600_000;
export const DEFAULT_CHUNK_SIZE = 65_536;

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

function bytes(value) {
  return value instanceof Uint8Array ? value : new Uint8Array(value);
}

function concat(parts) {
  const size = parts.reduce((sum, part) => sum + part.length, 0);
  const out = new Uint8Array(size);
  let offset = 0;
  for (const part of parts) {
    out.set(part, offset);
    offset += part.length;
  }
  return out;
}

function u32(value) {
  const out = new Uint8Array(4);
  new DataView(out.buffer).setUint32(0, value);
  return out;
}

function readU32(buffer, offset) {
  return new DataView(buffer.buffer, buffer.byteOffset + offset, 4).getUint32(0);
}

export function pageBase(href) {
  const url = new URL(href);
  if (url.pathname.endsWith("/index.html")) {
    url.pathname = url.pathname.slice(0, -"index.html".length);
  } else if (!url.pathname.endsWith("/")) {
    url.pathname += "/";
  }
  return url;
}

export function chunkUrl(pageHref, fileId, index) {
  return new URL(`blobs/${fileId}.${index}.bin`, pageBase(pageHref)).href;
}

async function deriveKey(password, salt, iterations) {
  const material = await crypto.subtle.importKey(
    "raw",
    textEncoder.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"],
  );
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", salt, iterations, hash: "SHA-256" },
    material,
    { name: "AES-GCM", length: 256 },
    false,
    ["encrypt", "decrypt"],
  );
}

async function seal(key, nonce, data, aad) {
  const encrypted = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: nonce, additionalData: aad },
    key,
    data,
  );
  return new Uint8Array(encrypted);
}

async function open(key, nonce, data, aad) {
  const decrypted = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: nonce, additionalData: aad },
    key,
    data,
  );
  return new Uint8Array(decrypted);
}

function randomBytes(size) {
  const out = new Uint8Array(size);
  crypto.getRandomValues(out);
  return out;
}

function hex(value) {
  return [...value].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function requireProfile(iterations, profile) {
  if (profile === "production" && iterations < RECOMMENDED_PBKDF2_ITERATIONS) {
    throw new Error(
      `production archives require at least ${RECOMMENDED_PBKDF2_ITERATIONS} PBKDF2 iterations`,
    );
  }
  if (!Number.isInteger(iterations) || iterations < 1) {
    throw new Error("iteration count must be a positive integer");
  }
}

export async function encryptArchive(files, password, options = {}) {
  const iterations = options.iterations ?? RECOMMENDED_PBKDF2_ITERATIONS;
  requireProfile(iterations, options.profile ?? "production");
  const chunkSize = options.chunkSize ?? DEFAULT_CHUNK_SIZE;
  const salt = randomBytes(16);
  const key = await deriveKey(password, salt, iterations);
  const entries = [];
  const blobs = new Map();
  for (const file of files) {
    const idBytes = randomBytes(16);
    const id = hex(idBytes);
    const plain = bytes(file.data);
    let index = 0;
    let offset = 0;
    while (index === 0 || offset < plain.length) {
      const slice = plain.subarray(offset, Math.min(plain.length, offset + chunkSize));
      const nonce = randomBytes(12);
      const aad = concat([idBytes, u32(index)]);
      const ciphertext = await seal(key, nonce, slice, aad);
      const part = concat([
        textEncoder.encode(MAGIC),
        Uint8Array.of(VERSION),
        idBytes,
        u32(index),
        nonce,
        u32(ciphertext.length),
        ciphertext,
      ]);
      blobs.set(`${id}.${index}`, part);
      index += 1;
      offset += chunkSize;
      if (plain.length === 0) break;
    }
    entries.push({
      id,
      path: file.path,
      type: file.type || "application/octet-stream",
      size: plain.length,
      chunks: index,
    });
  }
  const manifestNonce = randomBytes(12);
  const manifestPlain = textEncoder.encode(JSON.stringify({ files: entries }));
  const manifestCipher = await seal(key, manifestNonce, manifestPlain, textEncoder.encode("manifest"));
  const manifest = concat([
    textEncoder.encode(MAGIC),
    Uint8Array.of(VERSION, KDF_PBKDF2_SHA256),
    u32(iterations),
    salt,
    manifestNonce,
    u32(manifestCipher.length),
    manifestCipher,
  ]);
  return { manifest, blobs };
}

export async function decryptManifest(manifestBytes, password) {
  const data = bytes(manifestBytes);
  if (textDecoder.decode(data.subarray(0, 8)) !== MAGIC) throw new Error("unrecognized archive");
  if (data[8] !== VERSION || data[9] !== KDF_PBKDF2_SHA256) throw new Error("unsupported archive");
  if (data.length < 42) throw new Error("truncated archive");
  const iterations = readU32(data, 10);
  const salt = data.subarray(14, 30);
  const nonce = data.subarray(30, 42);
  const length = readU32(data, 42);
  const ciphertext = data.subarray(46, 46 + length);
  if (ciphertext.length !== length) throw new Error("truncated archive");
  const key = await deriveKey(password, salt, iterations);
  let plain;
  try {
    plain = await open(key, nonce, ciphertext, textEncoder.encode("manifest"));
  } catch {
    throw new Error("decrypt failed");
  }
  return { key, iterations, manifest: JSON.parse(textDecoder.decode(plain)) };
}

export async function decryptChunk(chunkBytes, key, expectedId, expectedIndex) {
  const data = bytes(chunkBytes);
  if (textDecoder.decode(data.subarray(0, 8)) !== MAGIC) throw new Error("unrecognized blob");
  if (data[8] !== VERSION) throw new Error("unsupported blob");
  if (data.length < 41) throw new Error("truncated blob");
  const idBytes = data.subarray(9, 25);
  const id = hex(idBytes);
  const index = readU32(data, 25);
  if (expectedId && id !== expectedId) throw new Error("blob id mismatch");
  if (expectedIndex !== undefined && index !== expectedIndex) throw new Error("chunk index mismatch");
  const nonce = data.subarray(29, 41);
  const length = readU32(data, 41);
  const ciphertext = data.subarray(45, 45 + length);
  if (ciphertext.length !== length) throw new Error("truncated blob");
  try {
    return await open(key, nonce, ciphertext, concat([idBytes, u32(index)]));
  } catch {
    throw new Error("decrypt failed");
  }
}

export async function decryptFile(blobs, key, file) {
  const parts = [];
  for (let index = 0; index < file.chunks; index += 1) {
    const chunk = blobs.get(`${file.id}.${index}`);
    if (!chunk) throw new Error("truncated blob");
    parts.push(await decryptChunk(chunk, key, file.id, index));
  }
  return concat(parts);
}
