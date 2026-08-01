const { makeMarketingGoHandler, makeSupabasePersist } = require("./_lib/marketing-go");

const PRODUCTS = {
  ai: { productId: "aniccaios", kind: "app", appId: "6755129214" },
  ho: { productId: "honne", kind: "app", appId: "6759667221" },
  ej: { productId: "ebook-ja", kind: "web", path: "/achan" },
  ee: { productId: "ebook-en", kind: "web", path: "/monk" },
};

exports.handler = async (event) => {
  const providerToken = process.env.ASC_VENDOR_NUMBER;
  const supabaseUrl = process.env.SUPABASE_URL;
  const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!providerToken || !supabaseUrl || !serviceKey)
    return { statusCode: 503, headers: { "cache-control": "no-store" }, body: "Attribution unavailable" };
  return makeMarketingGoHandler({
    products: PRODUCTS,
    providerToken,
    persist: makeSupabasePersist({ url: supabaseUrl, serviceKey }),
  })(event);
};
