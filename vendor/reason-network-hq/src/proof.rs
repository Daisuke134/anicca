//! Reason sign-in proofs: a statement signed by Reason that a machine's key (its endpoint id) belongs to a Reason
//! account, and the name that account goes by. A compact JWS (RS256: RSASSA-PKCS1-v1_5 with SHA-256, from Reason's
//! cloud-access issuer), checked here against Reason's public keys, which are compiled in: verifying one never calls
//! Reason. Every machine checks every proof it is shown itself.

use anyhow::{Result, anyhow, bail};
use data_encoding::BASE64URL_NOPAD;
use iroh::EndpointId;
use ring::signature::{RSA_PKCS1_2048_8192_SHA256, RsaPublicKeyComponents};
use serde::{Deserialize, Serialize};

const ISSUER: &str = "https://reasonmachines.com/network";
const AUDIENCE: &str = "reason-network";
const TYPE: &str = "reason-network-proof";
/// Refused before decoding. A proof Reason signs with a 4096-bit key is at most about 1.6 KB: the signature is 512
/// bytes (683 in base64url), the header with a 64-character key id about 130, and the claims (a 40-character name, an
/// email of at most 254, the 64-digit endpoint) at most about 790. Even an 8192-bit key, the most `ring` takes, stays
/// under 2.3 KB.
const MAX_LEN: usize = 4096;
/// A proof issued further ahead than this is refused (a broken clock, or worse).
const MAX_SKEW_SECS: i64 = 86_400;
/// The smallest RSA key trusted, in bits.
const MIN_BITS: usize = 2048;

/// Reason's proof-signing public keys: key id, then the RSA modulus `n` and exponent `e` in base64url (as in a JWK). In
/// debug builds `REASON_NETWORK_TRUST_KEYS` (a JWKS) adds keys, for tests.
///
/// Never remove a key, even a retired one: who holds a name in a team rests on proofs' signatures (expired proofs
/// included), so a build without a key that signed some would drop machines that every other build keeps. Add the
/// new key next to it instead.
///
/// The cloud-access issuer's KMS key (`https://oidc.reasonmachines.com`, which signs proofs as `iss`
/// `https://reasonmachines.com/network`), from https://oidc.reasonmachines.com/.well-known/jwks.json on 2026-10-20.
/// Only that one: proofs come only from KMS (the issuer refuses rather than falling back to its env key,
/// `reason-oidc-prod-2026-10-07`, which isn't trusted here). `the_production_keys_are_pinned` pins it to a hash of its
/// modulus.
const KEYS: &[(&str, &str, &str)] = &[(
    "reason-oidc-kms-2026-10",
    "s5x90QSBmHGl4adzvrjLvQ1ZRiwkDZGJ3pZs7CzPCxjKOBjoPoV6INAi4b8c3F4fMHH1T2BCXH9jX4wQjOCCzZBmB-E9Ch395WiqbLhyY2pH9V-ksbL9DGibS8xCoTT7EySB3FECzd_mHq-kQBCGxKnmBU0uETiPJLV276MzoBFsA8-s0PhsKqiQnUD3AKxHdDX-sWyI145QZasjZIT30Z8ixdRfrcUrLBMtWDhIqsOSP58i3_-3U-2gz_yG-7usgpyTcxCEU1IQGQtKBcJEVwd5QrbGgGE0w_uLxm2anfpT_eCZqOS_TWGYivVZ7TuqnxZgtON6kQgMNctSwprMDQ",
    "AQAB",
)];

/// What a proof says.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Proof {
    /// The Reason account.
    pub sub: String,
    /// The account's name in teams: 1 to 40 of `a-z`, `0-9` and `-`.
    pub name: String,
    pub email: String,
    /// The machine's endpoint id, as the engine prints it.
    pub endpoint: String,
    /// Issued and expires, in seconds since the epoch.
    pub iat: i64,
    pub exp: i64,
}

/// Exactly these fields: anything else, `crit` included, is refused (RFC 7515: a `crit` not understood must be).
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    alg: String,
    kid: String,
    typ: String,
}

#[derive(Deserialize)]
struct Claims {
    iss: String,
    aud: String,
    #[serde(flatten)]
    proof: Proof,
}

#[cfg(any(test, debug_assertions))]
#[derive(Deserialize)]
struct Jwks {
    keys: Vec<Jwk>,
}

#[cfg(any(test, debug_assertions))]
#[derive(Deserialize)]
struct Jwk {
    kty: String,
    kid: String,
    n: String,
    e: String,
}

type Key = RsaPublicKeyComponents<Vec<u8>>;

/// An RSA public key from its base64url modulus and exponent, if it is one of at least `MIN_BITS`.
fn key(n: &str, e: &str) -> Option<Key> {
    let decode = |v: &str| BASE64URL_NOPAD.decode(v.trim_end_matches('=').as_bytes()).ok();
    let strip = |v: Vec<u8>| v.into_iter().skip_while(|b| *b == 0).collect::<Vec<u8>>();
    let (n, e) = (strip(decode(n)?), strip(decode(e)?));
    let bits = n.first().map_or(0, |b| n.len() * 8 - b.leading_zeros() as usize);
    (bits >= MIN_BITS && !e.is_empty()).then_some(RsaPublicKeyComponents { n, e })
}

/// The keys a proof may be signed with: the compiled-in ones and, in debug builds, those in
/// `REASON_NETWORK_TRUST_KEYS` (release builds trust only the compiled-in keys), and in tests a test key.
fn trusted() -> &'static [(String, Key)] {
    static KEYS_: std::sync::OnceLock<Vec<(String, Key)>> = std::sync::OnceLock::new();
    KEYS_.get_or_init(|| {
        #[allow(unused_mut)]
        let mut out: Vec<(String, Key)> =
            KEYS.iter().filter_map(|(kid, n, e)| Some((kid.to_string(), key(n, e)?))).collect();
        #[cfg(any(test, debug_assertions))]
        if let Some(jwks) = std::env::var_os("REASON_NETWORK_TRUST_KEYS")
            && let Ok(jwks) = serde_json::from_str::<Jwks>(&jwks.to_string_lossy())
        {
            out.extend(
                jwks.keys.into_iter().filter(|k| k.kty == "RSA").filter_map(|k| Some((k.kid, key(&k.n, &k.e)?))),
            );
        }
        #[cfg(test)]
        out.push((tests::KID.into(), tests::public(tests::signer())));
        out
    })
}

/// Checks `jws` for the machine `endpoint`: Reason's signature, issuer, audience, expiry, and that it names this
/// machine.
pub fn verify(jws: &str, endpoint: &EndpointId) -> Result<Proof> {
    verify_with(jws, endpoint, crate::util::now_ms() / 1000, trusted(), true)
}

/// The same, except that a proof that expired still counts: for who may hold a name in the team, which mustn't change
/// as time passes (or differ between machines whose clocks do). Only "verified" goes by `verify`.
pub fn verify_ignoring_expiry(jws: &str, endpoint: &EndpointId) -> Result<Proof> {
    verify_with(jws, endpoint, crate::util::now_ms() / 1000, trusted(), false)
}

fn verify_with(jws: &str, endpoint: &EndpointId, now: i64, keys: &[(String, Key)], expiry: bool) -> Result<Proof> {
    let claims: Claims = serde_json::from_slice(&signed_claims(jws, TYPE, "sign-in proof", MAX_LEN, keys)?)
        .map_err(|_| anyhow!("this sign-in proof is damaged"))?;
    if claims.iss != ISSUER || claims.aud != AUDIENCE {
        bail!("this sign-in proof isn't from Reason Network");
    }
    let p = claims.proof;
    if expiry && p.exp <= now {
        bail!("this sign-in proof expired; sign in again");
    }
    if p.iat > now.saturating_add(MAX_SKEW_SECS) {
        bail!("this sign-in proof is dated in the future (is this computer's clock right?)");
    }
    if p.endpoint != endpoint.to_string() {
        bail!("this sign-in proof is for another machine");
    }
    if p.name.is_empty()
        || p.name.len() > 40
        || !p.name.bytes().all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
    {
        bail!("this sign-in proof's name isn't a valid name");
    }
    Ok(p)
}

/// The claims of `jws`, a compact JWS of type `typ` (a `what`, in errors) that one of Reason's keys signed, unparsed.
/// What else they must say is the caller's to check.
pub fn verify_signed(jws: &str, typ: &str, what: &str, max_len: usize) -> Result<Vec<u8>> {
    signed_claims(jws, typ, what, max_len, trusted())
}

fn signed_claims(jws: &str, typ: &str, what: &str, max_len: usize, keys: &[(String, Key)]) -> Result<Vec<u8>> {
    let bad = || anyhow!("this {what} is damaged");
    if jws.len() > max_len {
        bail!("this {what} is too long");
    }
    let mut parts = jws.trim().split('.');
    let (Some(h), Some(c), Some(s), None) = (parts.next(), parts.next(), parts.next(), parts.next()) else {
        return Err(bad());
    };
    let decode = |p: &str| BASE64URL_NOPAD.decode(p.as_bytes()).map_err(|_| bad());
    let header: Header = serde_json::from_slice(&decode(h)?).map_err(|_| bad())?;
    // RS256 only: never `none`, nor HS256 with the public key taken for a shared secret.
    if header.alg != "RS256" || header.typ != typ {
        bail!("not a Reason Network {what}");
    }
    let Some((_, key)) = keys.iter().find(|(kid, _)| *kid == header.kid) else {
        bail!("this {what} is signed with a key this version doesn't know (update Reason Network)");
    };
    if key.verify(&RSA_PKCS1_2048_8192_SHA256, format!("{h}.{c}").as_bytes(), &decode(s)?).is_err() {
        bail!("this {what}'s signature doesn't verify");
    }
    decode(c)
}

#[cfg(test)]
pub(crate) mod tests {
    use super::*;
    use iroh::SecretKey;
    use serde_json::json;

    use ring::signature::RsaKeyPair;
    use std::sync::OnceLock;

    pub const KID: &str = "test-1";

    fn pkcs8(cell: &'static OnceLock<RsaKeyPair>, der: &[u8]) -> &'static RsaKeyPair {
        cell.get_or_init(|| RsaKeyPair::from_pkcs8(der).expect("a test key"))
    }

    /// The key test builds trust (see `trusted`), standing in for Reason's: a 2048-bit RSA key made for these tests.
    pub fn signer() -> &'static RsaKeyPair {
        static K: OnceLock<RsaKeyPair> = OnceLock::new();
        pkcs8(&K, include_bytes!("testdata/proof-signer.pk8"))
    }

    /// A key nobody trusts.
    pub fn forger() -> &'static RsaKeyPair {
        static K: OnceLock<RsaKeyPair> = OnceLock::new();
        pkcs8(&K, include_bytes!("testdata/proof-forger.pk8"))
    }

    pub fn public(k: &RsaKeyPair) -> Key {
        RsaPublicKeyComponents::from(k.public())
    }

    pub fn header() -> serde_json::Value {
        json!({"alg": "RS256", "kid": KID, "typ": TYPE})
    }

    /// The RS256 signature over `input`, in base64url.
    pub fn signature(key: &RsaKeyPair, input: &str) -> String {
        let mut sig = vec![0; key.public().modulus_len()];
        key.sign(&ring::signature::RSA_PKCS1_SHA256, &ring::rand::SystemRandom::new(), input.as_bytes(), &mut sig)
            .unwrap();
        BASE64URL_NOPAD.encode(&sig)
    }

    pub fn sign_with(key: &RsaKeyPair, header: serde_json::Value, claims: serde_json::Value) -> String {
        let enc = |v: serde_json::Value| BASE64URL_NOPAD.encode(&serde_json::to_vec(&v).unwrap());
        let input = format!("{}.{}", enc(header), enc(claims));
        format!("{input}.{}", signature(key, &input))
    }

    pub fn claims(sub: &str, name: &str, endpoint: &EndpointId) -> serde_json::Value {
        let now = crate::util::now_ms() / 1000;
        json!({"iss": ISSUER, "aud": AUDIENCE, "sub": sub, "name": name, "email": format!("{name}@example.com"),
               "endpoint": endpoint.to_string(), "iat": now, "exp": now + 90 * 86_400})
    }

    /// A good proof that `endpoint` belongs to account `sub`, called `name`.
    pub fn proof(sub: &str, name: &str, endpoint: &EndpointId) -> String {
        sign_with(signer(), header(), claims(sub, name, endpoint))
    }

    #[test]
    fn a_good_proof_verifies() {
        let me = SecretKey::generate().public();
        let p = verify(&proof("user_1", "alex", &me), &me).unwrap();
        assert_eq!((p.sub.as_str(), p.name.as_str(), p.email.as_str()), ("user_1", "alex", "alex@example.com"));
        assert!(verify(&format!("  {}\n", proof("user_1", "alex", &me)), &me).is_ok());
    }

    #[test]
    fn rejects_bad_proofs() {
        let me = SecretKey::generate().public();
        let header = header();
        let err = |jws: &str| verify(jws, &me).unwrap_err().to_string();
        let with = |change: &dyn Fn(&mut serde_json::Value)| {
            let mut c = claims("user_1", "alex", &me);
            change(&mut c);
            sign_with(signer(), header.clone(), c)
        };

        let forged = sign_with(forger(), header.clone(), claims("user_1", "alex", &me));
        assert!(err(&forged).contains("signature doesn't verify"));
        // A good signature over other claims.
        let good = proof("user_1", "alex", &me);
        let other = with(&|c| c["name"] = json!("root"));
        let mixed = format!(
            "{}.{}.{}",
            good.split('.').next().unwrap(),
            other.split('.').nth(1).unwrap(),
            good.split('.').nth(2).unwrap()
        );
        assert!(err(&mixed).contains("signature doesn't verify"));
        assert!(err(&with(&|c| c["aud"] = json!("reason"))).contains("isn't from Reason Network"));
        assert!(err(&with(&|c| c["iss"] = json!("https://evil.example"))).contains("isn't from Reason Network"));
        // Reason's own issuer, but not the network's.
        assert!(err(&with(&|c| c["iss"] = json!("https://reasonmachines.com"))).contains("isn't from Reason Network"));
        assert!(err(&with(&|c| c["exp"] = json!(crate::util::now_ms() / 1000 - 1))).contains("expired"));
        assert!(err(&proof("user_1", "alex", &SecretKey::generate().public())).contains("for another machine"));
        for name in ["", "Alex", "alex smith", &"a".repeat(41)] {
            assert!(err(&with(&|c| c["name"] = json!(name))).contains("valid name"), "{name:?}");
        }
        let unknown =
            sign_with(signer(), json!({"alg": "RS256", "kid": "other", "typ": TYPE}), claims("user_1", "alex", &me));
        assert!(err(&unknown).contains("doesn't know"));
        let alg = sign_with(signer(), json!({"alg": "none", "kid": KID, "typ": TYPE}), claims("user_1", "alex", &me));
        assert!(err(&alg).contains("not a Reason Network sign-in proof"));
        for damaged in ["", "a.b", "a.b.c.d", &good[..good.len() - 4]] {
            assert!(verify(damaged, &me).is_err(), "{damaged:?}");
        }
    }

    #[test]
    fn only_trusted_keys_count() {
        let me = SecretKey::generate().public();
        let jws = proof("user_1", "alex", &me);
        let now = crate::util::now_ms() / 1000;
        assert!(verify_with(&jws, &me, now, &[], true).is_err(), "no keys, nothing verifies");
        let keys = [(KID.to_string(), public(signer()))];
        assert!(verify_with(&jws, &me, now, &keys, true).is_ok());
        let later = now + 91 * 86_400;
        assert!(verify_with(&jws, &me, later, &keys, true).is_err(), "expired by then");
        assert!(verify_with(&jws, &me, later, &keys, false).is_ok(), "but still Reason's word, for who holds a name");
    }

    #[test]
    fn reads_a_jwks_key() {
        let p = public(signer());
        let (n, e) = (BASE64URL_NOPAD.encode(&p.n), BASE64URL_NOPAD.encode(&p.e));
        let jwks: Jwks = serde_json::from_value(
            json!({"keys": [{"kty": "RSA", "kid": KID, "n": n, "e": e, "alg": "RS256", "use": "sig"}]}),
        )
        .unwrap();
        let k = key(&jwks.keys[0].n, &jwks.keys[0].e).unwrap();
        assert_eq!((k.n, k.e), (p.n.clone(), p.e.clone()));
        // A leading zero byte (as some encoders write it) is the same key.
        let padded = BASE64URL_NOPAD.encode(&[&[0u8][..], &p.n].concat());
        assert_eq!(key(&padded, &e).unwrap().n, p.n);
        assert!(key("not base64!", &e).is_none());
        // Under 2048 bits isn't trusted.
        assert!(key(&BASE64URL_NOPAD.encode(&p.n[..128]), &e).is_none());
    }

    #[test]
    fn the_production_keys_are_pinned() {
        // SHA-256 of the modulus, as Reason's JWKS gave it on 2026-10-20: an accidental edit to `KEYS` fails here.
        let pins = [("reason-oidc-kms-2026-10", "c8a5d1e79ecc6c6056a7a11eac0b870a664f4b4ecb27392e7db4544c23e039c4")];
        assert_eq!(KEYS.len(), pins.len());
        for ((kid, n, e), (pinned_kid, pinned)) in KEYS.iter().zip(pins) {
            assert_eq!(*kid, pinned_kid);
            let k = key(n, e).expect("an RSA key of at least 2048 bits");
            let hash = data_encoding::HEXLOWER.encode(ring::digest::digest(&ring::digest::SHA256, &k.n).as_ref());
            assert_eq!(hash, pinned, "{kid}");
            assert_eq!(k.e, [1, 0, 1], "{kid}");
        }
        // It's trusted (next to the test key); the issuer's env key isn't.
        assert!(trusted().iter().any(|(k, _)| k == "reason-oidc-kms-2026-10"));
        assert!(!trusted().iter().any(|(k, _)| k == "reason-oidc-prod-2026-10-07"));
    }

    #[test]
    fn only_rs256_counts() {
        let me = SecretKey::generate().public();
        let c = claims("user_1", "alex", &me);
        let enc = |v: &serde_json::Value| BASE64URL_NOPAD.encode(&serde_json::to_vec(v).unwrap());
        // HS256 keyed with Reason's public key (anyone has it), in the forms it gets published.
        let p = public(signer());
        let jwk =
            json!({"kty": "RSA", "kid": KID, "n": BASE64URL_NOPAD.encode(&p.n), "e": BASE64URL_NOPAD.encode(&p.e)});
        for secret in [p.n.clone(), serde_json::to_vec(&jwk).unwrap()] {
            let input = format!("{}.{}", enc(&json!({"alg": "HS256", "kid": KID, "typ": TYPE})), enc(&c));
            let tag = ring::hmac::sign(&ring::hmac::Key::new(ring::hmac::HMAC_SHA256, &secret), input.as_bytes());
            let jws = format!("{input}.{}", BASE64URL_NOPAD.encode(tag.as_ref()));
            assert!(verify(&jws, &me).unwrap_err().to_string().contains("not a Reason Network sign-in proof"));
        }
        // Unsigned.
        for sig in ["", "AAAA"] {
            let jws = format!("{}.{}.{sig}", enc(&json!({"alg": "none", "kid": KID, "typ": TYPE})), enc(&c));
            assert!(verify(&jws, &me).unwrap_err().to_string().contains("not a Reason Network sign-in proof"));
        }
        // Another RSA scheme's name, over a good RS256 signature.
        let good = proof("user_1", "alex", &me);
        let mut parts = good.split('.');
        let (_, body, sig) = (parts.next(), parts.next().unwrap(), parts.next().unwrap());
        let ps = format!("{}.{body}.{sig}", enc(&json!({"alg": "PS256", "kid": KID, "typ": TYPE})));
        assert!(verify(&ps, &me).is_err());
    }

    #[test]
    fn an_expired_proof_still_says_whose_machine_it_is() {
        let me = SecretKey::generate().public();
        let mut c = claims("user_1", "alex", &me);
        c["exp"] = json!(crate::util::now_ms() / 1000 - 1);
        let jws = sign_with(signer(), header(), c);
        assert!(verify(&jws, &me).is_err());
        assert_eq!(verify_ignoring_expiry(&jws, &me).unwrap().sub, "user_1");
        // Everything else still counts.
        assert!(verify_ignoring_expiry(&jws, &SecretKey::generate().public()).is_err());
        let forged = sign_with(forger(), header(), claims("user_1", "alex", &me));
        assert!(verify_ignoring_expiry(&forged, &me).is_err());
    }

    #[test]
    fn refuses_proofs_from_the_future() {
        let me = SecretKey::generate().public();
        for iat in [json!(i64::MAX), json!(crate::util::now_ms() / 1000 + 2 * 86_400)] {
            let mut c = claims("user_1", "alex", &me);
            c["iat"] = iat;
            let jws = sign_with(signer(), header(), c);
            assert!(verify(&jws, &me).unwrap_err().to_string().contains("in the future"));
            assert!(verify_ignoring_expiry(&jws, &me).is_err());
        }
        let mut c = claims("user_1", "alex", &me);
        c["iat"] = json!(crate::util::now_ms() / 1000 + 3600);
        assert!(verify(&sign_with(signer(), header(), c), &me).is_ok(), "a clock a bit ahead");
    }

    #[test]
    fn refuses_a_huge_proof_before_decoding_it() {
        let me = SecretKey::generate().public();
        let header = BASE64URL_NOPAD.encode(br#"{"alg":"RS256","kid":"test-1","typ":"reason-network-proof"}"#);
        for big in [
            format!("{}.A.{}", "A".repeat(4 << 20), "A".repeat(342)),
            format!("{header}.{}.{}", "A".repeat(4 << 20), "A".repeat(342)),
        ] {
            let t = std::time::Instant::now();
            assert!(verify(&big, &me).unwrap_err().to_string().contains("too long"));
            assert!(t.elapsed() < std::time::Duration::from_millis(50), "{:?}", t.elapsed());
        }
    }

    #[test]
    fn the_header_has_exactly_alg_kid_and_typ() {
        let me = SecretKey::generate().public();
        let c = claims("user_1", "alex", &me);
        for header in [
            json!({"alg": "RS256", "kid": KID, "typ": TYPE, "crit": ["exp"], "exp": 1}),
            json!({"alg": "RS256", "kid": KID, "typ": TYPE, "jku": "https://evil.example/keys.json"}),
            json!({"alg": "RS256", "kid": KID}),
        ] {
            let jws = sign_with(signer(), header.clone(), c.clone());
            assert!(verify(&jws, &me).unwrap_err().to_string().contains("damaged"), "{header}");
            assert!(verify_ignoring_expiry(&jws, &me).is_err(), "{header}");
        }
        // A key twice is refused too.
        let h =
            BASE64URL_NOPAD.encode(format!(r#"{{"alg":"RS256","kid":"zzz","kid":"{KID}","typ":"{TYPE}"}}"#).as_bytes());
        let body = BASE64URL_NOPAD.encode(&serde_json::to_vec(&c).unwrap());
        let input = format!("{h}.{body}");
        let jws = format!("{input}.{}", signature(signer(), &input));
        assert!(verify(&jws, &me).is_err());
    }
}
