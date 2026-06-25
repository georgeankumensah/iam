// Client-side WebAuthn helpers: Zitadel returns/accepts credential buffers as
// base64url strings, while the browser WebAuthn API works with ArrayBuffers.
// These convert between the two.

export function b64urlToBuf(value: string): ArrayBuffer {
  const pad = "=".repeat((4 - (value.length % 4)) % 4);
  const b64 = (value + pad).replace(/-/g, "+").replace(/_/g, "/");
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes.buffer;
}

export function bufToB64url(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

type AnyOptions = { publicKey?: Record<string, unknown> } & Record<string, unknown>;

function unwrap(options: AnyOptions): Record<string, unknown> {
  return (options.publicKey as Record<string, unknown>) || options;
}

// Decode a Zitadel assertion (login) options object into the structure
// navigator.credentials.get expects.
export function prepareRequestOptions(options: AnyOptions): PublicKeyCredentialRequestOptions {
  const pk = unwrap(options) as Record<string, unknown>;
  return {
    ...pk,
    challenge: b64urlToBuf(pk.challenge as string),
    allowCredentials: ((pk.allowCredentials as Array<Record<string, unknown>>) || []).map((c) => ({
      ...c,
      id: b64urlToBuf(c.id as string),
    })),
  } as PublicKeyCredentialRequestOptions;
}

// Decode a Zitadel registration (create) options object.
export function prepareCreationOptions(options: AnyOptions): PublicKeyCredentialCreationOptions {
  const pk = unwrap(options) as Record<string, unknown>;
  const user = pk.user as Record<string, unknown>;
  return {
    ...pk,
    challenge: b64urlToBuf(pk.challenge as string),
    user: { ...user, id: b64urlToBuf(user.id as string) },
    excludeCredentials: ((pk.excludeCredentials as Array<Record<string, unknown>>) || []).map((c) => ({
      ...c,
      id: b64urlToBuf(c.id as string),
    })),
  } as PublicKeyCredentialCreationOptions;
}

// Serialize a get() assertion back into Zitadel's credentialAssertionData shape.
export function serializeAssertion(cred: PublicKeyCredential) {
  const r = cred.response as AuthenticatorAssertionResponse;
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      authenticatorData: bufToB64url(r.authenticatorData),
      clientDataJSON: bufToB64url(r.clientDataJSON),
      signature: bufToB64url(r.signature),
      userHandle: r.userHandle ? bufToB64url(r.userHandle) : null,
    },
  };
}

// Serialize a create() credential back into Zitadel's publicKeyCredential shape.
export function serializeCredential(cred: PublicKeyCredential) {
  const r = cred.response as AuthenticatorAttestationResponse;
  return {
    id: cred.id,
    rawId: bufToB64url(cred.rawId),
    type: cred.type,
    response: {
      attestationObject: bufToB64url(r.attestationObject),
      clientDataJSON: bufToB64url(r.clientDataJSON),
    },
  };
}
