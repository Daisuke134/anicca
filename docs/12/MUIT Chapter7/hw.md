# Middle Report for Information Security Lecture

**Student ID:** 2411218  
**Date:** 2026/01/09

---

## 1. Calculate nP on EC:E

**Problem Statement:**  
Calculate $nP$ on the elliptic curve $E: y^2 \equiv x^3 + 2x + 2 \pmod{17}$.  
Given point: $P = (5, 1)$.  
Determine $n$ using Student ID: $2411218$.

### (1) Calculation of n

Using the formula $n = (\text{Student ID} \pmod 7) + 3$:

$$
2411218 \div 7 = 344459 \quad \text{remainder} \quad 5
$$

$$
n = 5 + 3 = 8
$$

**Target:** We need to calculate **8P**.

### (2) Calculation of 8P

We compute $8P$ using the doubling method ($2P, 4P, 8P$).  
**Doubling Formula** for $Q=(x, y)$ on $y^2 = x^3 + ax + b$:
- Slope $\lambda = \frac{3x^2 + a}{2y}$
- $x' = \lambda^2 - 2x$
- $y' = \lambda(x - x') - y$

#### Step 1: Calculate 2P
Given $P = (5, 1)$.
$$
\lambda = \frac{3(5^2) + 2}{2(1)} = \frac{77}{2} \equiv \frac{9}{2} = 9 \times 2^{-1} \pmod{17}
$$
Since $2 \times 9 = 18 \equiv 1 \pmod{17}$, the inverse $2^{-1} \equiv 9$.
$$
\lambda = 9 \times 9 = 81 \equiv 13 \pmod{17}
$$

$$
x_{2P} = 13^2 - 2(5) = 169 - 10 = 159 \equiv 6 \pmod{17}
$$
$$
y_{2P} = 13(5 - 6) - 1 = 13(-1) - 1 = -14 \equiv 3 \pmod{17}
$$
**$\therefore 2P = (6, 3)$**

#### Step 2: Calculate 4P (Doubling 2P)
Given $2P = (6, 3)$.
$$
\lambda = \frac{3(6^2) + 2}{2(3)} = \frac{110}{6} \equiv \frac{8}{6} = 8 \times 6^{-1} \pmod{17}
$$
Since $6 \times 3 = 18 \equiv 1 \pmod{17}$, the inverse $6^{-1} \equiv 3$.
$$
\lambda = 8 \times 3 = 24 \equiv 7 \pmod{17}
$$

$$
x_{4P} = 7^2 - 2(6) = 49 - 12 = 37 \equiv 3 \pmod{17}
$$
$$
y_{4P} = 7(6 - 3) - 3 = 21 - 3 = 18 \equiv 1 \pmod{17}
$$
**$\therefore 4P = (3, 1)$**

#### Step 3: Calculate 8P (Doubling 4P)
Given $4P = (3, 1)$.
$$
\lambda = \frac{3(3^2) + 2}{2(1)} = \frac{29}{2} \equiv \frac{12}{2} = 6 \pmod{17}
$$

$$
x_{8P} = 6^2 - 2(3) = 36 - 6 = 30 \equiv 13 \pmod{17}
$$
$$
y_{8P} = 6(3 - 13) - 1 = 6(-10) - 1 = -60 - 1 = -61 \equiv 7 \pmod{17}
$$
(Note: $-61 = 17 \times (-4) + 7$)

### Result
**$$8P = (13, 7)$$**

---

\newpage

## 2. Opinion on the applications of advanced cryptography

**Title: Balancing Privacy and Utility in Voice AI with Advanced Cryptography**

As a developer of a Voice AI application that supports habit formation through conversation, I see immense potential for advanced cryptography to resolve the fundamental conflict between "data utilization" and "user privacy."

Currently, many AI services rely on decrypting user data in the cloud to perform inference or analysis. However, voice data is biometric and highly sensitive, containing not just content but also emotional and environmental context. To build trust in next-generation AI, we must move beyond simple "encryption at rest" to **functional encryption** that allows data to be used while remaining encrypted.

I believe the following three applications of advanced cryptography will be critical in the near future:

**1. Searchable Encryption for Private Logs**
Users often want to search their past conversation history (e.g., "When did I say I felt stressed?"), but storing these logs in plaintext on a server creates a significant security risk. Searchable encryption would allow our servers to query encrypted databases and return relevant results to the user without the server ever "seeing" the content of the query or the stored logs. This is essential for maintaining privacy in personal journaling or mental health apps.

**2. Attribute-Based Encryption (ABE) for Granular Access Control**
In a coaching or healthcare context, a user might want to share their "habit progress data" with a human mentor but keep the raw "audio recordings" private. Attribute-Based Encryption (ABE) would allow us to encrypt data with specific attributes (e.g., `access:mentor`, `type:summary`). This ensures that third parties can only decrypt what they are explicitly authorized to see based on their attributes, without the platform provider needing to manage shared keys manually.

**3. Proxy Re-Encryption for Secure Data Sharing**
If a user wants to switch AI providers or share their data with a family member, Proxy Re-Encryption could allow the platform to transform ciphertext encrypted for the user into ciphertext decryptable by the recipient. Crucially, this happens without the platform ever obtaining the plaintext or the user's private key, enabling secure data portability in cloud environments.

In conclusion, advanced cryptography is not just a security measure but a business enabler. It allows startups to build "trustless" architectures where the value of AI—personalization and insight—can be delivered without asking users to surrender ownership of their most intimate data.
