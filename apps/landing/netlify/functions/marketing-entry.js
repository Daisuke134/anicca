const { makeEntryHandler, makeSupabasePersist } = require("./_lib/marketing-entry");

exports.handler = async (event) => {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return { statusCode: 503, body: "Entry receipt unavailable" };
  return makeEntryHandler({ persist: makeSupabasePersist({ url, serviceKey: key }) })(event);
};
// AFFILIATE_ENTRY_V1
