/**
 * IndexedDB-backed keypair store.
 *
 * v0.5 (this file): private keys stored in plaintext in IndexedDB, origin-
 * scoped by the browser. Anyone with access to your browser profile can
 * exfiltrate them. This is the weakest self-custody option but removes the
 * server-side-impersonation risk (R2) that we had with the v0 stub.
 *
 * v1 roadmap: wrap `sk` with a passkey PRF-extension-derived key so IDB
 * ciphertext is useless without a WebAuthn touch.
 */

const DB_NAME = "kindred-keystore";
const STORE = "keypairs";

type Row = { id: string; sk: Uint8Array; pk: Uint8Array };

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      if (!req.result.objectStoreNames.contains(STORE)) {
        req.result.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveKeypair(
  id: string,
  sk: Uint8Array,
  pk: Uint8Array
): Promise<void> {
  const db = await openDB();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).put({ id, sk, pk } satisfies Row);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}

export async function loadKeypair(
  id: string
): Promise<{ sk: Uint8Array; pk: Uint8Array } | null> {
  const db = await openDB();
  try {
    return await new Promise<Row | null>((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).get(id);
      req.onsuccess = () => resolve((req.result as Row | undefined) ?? null);
      req.onerror = () => reject(req.error);
    }).then((row) => (row ? { sk: row.sk, pk: row.pk } : null));
  } finally {
    db.close();
  }
}

export async function listKeypairs(): Promise<string[]> {
  const db = await openDB();
  try {
    return await new Promise<string[]>((resolve, reject) => {
      const tx = db.transaction(STORE, "readonly");
      const req = tx.objectStore(STORE).getAllKeys();
      req.onsuccess = () => resolve(req.result as string[]);
      req.onerror = () => reject(req.error);
    });
  } finally {
    db.close();
  }
}

export async function deleteKeypair(id: string): Promise<void> {
  const db = await openDB();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, "readwrite");
      tx.objectStore(STORE).delete(id);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
