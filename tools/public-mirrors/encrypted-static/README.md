# Synthetic encrypted archive

This is a research prototype. It is not a Read or Trade mirror, it is not deployed at `/read/` or `/trade/`, and it does not contain private comics, briefs, or a live gate password.

`codec.mjs` uses WebCrypto only: PBKDF2-HMAC-SHA-256 and AES-256-GCM. A production profile refuses fewer than 600,000 iterations. The test archive uses 10,000 iterations so the check stays fast, and it says so in the file header. The password in `synthetic-password.mjs` is a labeled fake. A real password must stay out of this repository and must not be the Read or Trade gate password.

The viewer keeps the key in memory for the tab, does not remember it, and does not install a service worker. Blob URLs are revoked when the page is left. Each ciphertext chunk is its own file, small enough to stay under GitHub's 100MB file limit. Direct fetches of those files are not images or PDFs. A wrong password, a flipped byte, or a short file fails the GCM tag or the length check.

GitHub Pages on `2comma.github.io` still serves every file to the public. This format does not make the page resistant to someone who can edit the public JavaScript.
