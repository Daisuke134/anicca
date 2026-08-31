"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const HASH = /^[0-9a-f]{64}$/;
const OBJECT_REF = /^object:\/\/sha256\/([0-9a-f]{64})$/;

function sha256File(filePath) {
  const hash = crypto.createHash("sha256");
  const file = fs.openSync(filePath, "r");
  const buffer = Buffer.allocUnsafe(1024 * 1024);
  try {
    let bytes;
    while ((bytes = fs.readSync(file, buffer, 0, buffer.length, null)) > 0) {
      hash.update(buffer.subarray(0, bytes));
    }
  } finally {
    fs.closeSync(file);
  }
  return hash.digest("hex");
}

function requiredObjectDir(options) {
  const objectDir = path.resolve(String(options && options.objectDir || ""));
  if (!path.isAbsolute(objectDir) || objectDir === path.parse(objectDir).root) {
    throw new Error("content object directory is invalid");
  }
  return objectDir;
}

function objectRef(digest) {
  const hash = String(digest || "").toLowerCase();
  if (!HASH.test(hash)) throw new Error("content object hash is invalid");
  return `object://sha256/${hash}`;
}

function parseObjectRef(ref) {
  const match = OBJECT_REF.exec(String(ref || ""));
  if (!match) throw new Error("content object reference is invalid");
  return match[1];
}

function objectPath(digest, options) {
  const objectDir = requiredObjectDir(options);
  return path.join(objectDir, "sha256", digest);
}

function resolveContentObject(ref, options) {
  const digest = parseObjectRef(ref);
  const stored = objectPath(digest, options);
  if (!fs.statSync(stored, { throwIfNoEntry: false })?.isFile()) {
    throw new Error("content object is unavailable");
  }
  if (sha256File(stored) !== digest) {
    throw new Error("content object integrity verification failed");
  }
  return stored;
}

function importContentObject(sourcePath, options) {
  const source = path.resolve(String(sourcePath || ""));
  const stat = fs.statSync(source, { throwIfNoEntry: false });
  if (!stat?.isFile() || stat.size < 1) {
    throw new Error("content object source must be a non-empty file");
  }
  const digest = sha256File(source);
  const destination = objectPath(digest, options);
  fs.mkdirSync(path.dirname(destination), { recursive: true, mode: 0o700 });
  if (!fs.existsSync(destination)) {
    const temporary = `${destination}.tmp-${process.pid}-${crypto.randomUUID()}`;
    fs.copyFileSync(source, temporary, fs.constants.COPYFILE_EXCL);
    fs.chmodSync(temporary, 0o600);
    if (sha256File(temporary) !== digest) {
      fs.unlinkSync(temporary);
      throw new Error("content object integrity verification failed during import");
    }
    try {
      fs.renameSync(temporary, destination);
    } catch (error) {
      if (error.code !== "EEXIST") throw error;
      fs.unlinkSync(temporary);
    }
  }
  const resolved = resolveContentObject(objectRef(digest), options);
  return Object.freeze({
    ref: objectRef(digest),
    sha256: digest,
    size_bytes: fs.statSync(resolved).size,
  });
}

function createContentObjectStore(options) {
  return Object.freeze({
    import: (sourcePath) => importContentObject(sourcePath, options),
    resolve: (ref) => resolveContentObject(ref, options),
  });
}

module.exports = {
  createContentObjectStore,
  importContentObject,
  objectRef,
  parseObjectRef,
  resolveContentObject,
  sha256File,
};
