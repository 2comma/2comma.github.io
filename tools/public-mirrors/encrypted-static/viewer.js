import { chunkUrl, decryptChunk, decryptManifest, pageBase } from "./codec.mjs";

const passwordInput = document.querySelector("#password");
const form = document.querySelector("#unlock");
const status = document.querySelector("#status");
const listing = document.querySelector("#listing");
const preview = document.querySelector("#preview");
let currentUrl = "";

function revokeCurrent() {
  if (currentUrl) {
    URL.revokeObjectURL(currentUrl);
    currentUrl = "";
  }
}

function fail(error) {
  revokeCurrent();
  listing.replaceChildren();
  preview.replaceChildren();
  status.textContent = error && error.message === "decrypt failed"
    ? "Could not decrypt. The password is wrong or the archive was changed."
    : "Could not open the archive.";
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  revokeCurrent();
  listing.replaceChildren();
  preview.replaceChildren();
  const password = passwordInput.value;
  passwordInput.value = "";
  status.textContent = "Working…";
  try {
    const response = await fetch(new URL("manifest.blob", pageBase(location.href)));
    if (!response.ok) throw new Error("missing");
    const manifestBytes = new Uint8Array(await response.arrayBuffer());
    const opened = await decryptManifest(manifestBytes, password);
    status.textContent = "Unlocked in this tab only. Nothing is saved in the browser.";
    for (const file of opened.manifest.files) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = file.path;
      button.addEventListener("click", async () => {
        revokeCurrent();
        preview.replaceChildren();
        try {
          const parts = [];
          for (let index = 0; index < file.chunks; index += 1) {
            const blobResponse = await fetch(chunkUrl(location.href, file.id, index));
            if (!blobResponse.ok) throw new Error("missing");
            const encrypted = new Uint8Array(await blobResponse.arrayBuffer());
            parts.push(await decryptChunk(encrypted, opened.key, file.id, index));
          }
          const plain = new Blob(parts, { type: file.type });
          const objectUrl = URL.createObjectURL(plain);
          currentUrl = objectUrl;
          if (file.type.startsWith("image/")) {
            const image = document.createElement("img");
            image.alt = file.path;
            image.src = objectUrl;
            preview.append(image);
          } else {
            const link = document.createElement("a");
            link.href = objectUrl;
            link.download = file.path.split("/").pop();
            link.textContent = `Download ${file.path}`;
            preview.append(link);
          }
        } catch (error) {
          fail(error);
        }
      });
      listing.append(button);
    }
  } catch (error) {
    fail(error);
  }
});

window.addEventListener("pagehide", revokeCurrent);
