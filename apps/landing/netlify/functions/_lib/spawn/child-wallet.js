// Child wallet generation (ethers, secp256k1 — Base/Ethereum compatible). spec27b.
// The child's address is its dashboard `id` and a basescan-checkable, parent-distinct identity.
const { Wallet } = require("ethers");

function newChildWallet() {
  const w = Wallet.createRandom();
  return { address: w.address, privateKey: w.privateKey };
}

// HARD: a child must NEVER share the parent's wallet (proves distinct lineage on basescan).
function assertDistinct(parentAddr, childAddr) {
  if (String(parentAddr).toLowerCase() === String(childAddr).toLowerCase()) {
    throw new Error("child wallet collided with parent — refusing to spawn");
  }
  return true;
}

module.exports = { newChildWallet, assertDistinct };
