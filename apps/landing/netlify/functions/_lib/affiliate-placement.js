const PLACEMENT = /^elevenlabs-discovered-[a-z0-9][a-z0-9-]*-en(?:-experiment-[a-f0-9]{12})?-1$/;

function isAffiliatePlacement(value) {
  return typeof value === "string" && value.length <= 80 && PLACEMENT.test(value);
}

module.exports = { PLACEMENT, isAffiliatePlacement };
