// Stripe webhook → Printful auto-fulfillment for anicca-fashion-factory.
// Listens to: checkout.session.completed
// Action: read metadata.printful_sync_variant_id, place Printful order, send Resend confirmation.
//
// Required env (set in Netlify):
//   STRIPE_SECRET_KEY              — sk_live_...
//   STRIPE_FASHION_WEBHOOK_SECRET  — whsec_... (Stripe dashboard webhook signing secret)
//   PRINTFUL_API_KEY               — Printful private token
//   PRINTFUL_STORE_ID              — 18142516
//   RESEND_API_KEY                 — re_...
//   SUPABASE_URL                   — https://cycgdwndgfgdbnndithc.supabase.co
//   SUPABASE_SERVICE_ROLE_KEY      — for fashion_orders table

const stripe = require('stripe');

exports.handler = async (event) => {
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'method not allowed' };
  }

  const STRIPE_SECRET = process.env.STRIPE_SECRET_KEY;
  const WEBHOOK_SECRET = process.env.STRIPE_FASHION_WEBHOOK_SECRET;
  const PF_KEY = process.env.PRINTFUL_API_KEY;
  const PF_STORE = process.env.PRINTFUL_STORE_ID || '18142516';
  const RESEND_KEY = process.env.RESEND_API_KEY;

  if (!STRIPE_SECRET || !PF_KEY) {
    return { statusCode: 500, body: 'missing env' };
  }

  const stripeClient = stripe(STRIPE_SECRET);

  // Verify Stripe signature
  let stripeEvent;
  try {
    stripeEvent = WEBHOOK_SECRET
      ? stripeClient.webhooks.constructEvent(
          event.body,
          event.headers['stripe-signature'],
          WEBHOOK_SECRET
        )
      : JSON.parse(event.body); // dev only — never production without secret
  } catch (err) {
    console.error('signature verify failed:', err.message);
    return { statusCode: 400, body: `Webhook Error: ${err.message}` };
  }

  // Only handle completed checkout sessions
  if (stripeEvent.type !== 'checkout.session.completed') {
    return { statusCode: 200, body: 'event ignored' };
  }

  const session = stripeEvent.data.object;

  try {
    // Expand line_items to get the product metadata.
    // shipping_details and customer_details are inline — never expand.
    const sessionWithItems = await stripeClient.checkout.sessions.retrieve(session.id, {
      expand: ['line_items.data.price.product'],
    });

    const items = (sessionWithItems.line_items?.data || []).map((li) => ({
      sync_variant_id: parseInt(li.price?.product?.metadata?.printful_sync_variant_id, 10),
      quantity: li.quantity,
      product_slug: li.price?.product?.metadata?.product,
    }));

    if (!items.length || items.some((i) => !i.sync_variant_id)) {
      console.error('no Printful sync_variant_id in session', session.id);
      return { statusCode: 200, body: 'no fashion items' };
    }

    const ship = sessionWithItems.shipping_details || sessionWithItems.customer_details;
    const addr = ship?.address;
    if (!addr) {
      throw new Error('no shipping address on session ' + session.id);
    }

    const recipient = {
      name: ship.name || sessionWithItems.customer_details?.name || 'Customer',
      address1: addr.line1,
      address2: addr.line2 || undefined,
      city: addr.city,
      state_code: addr.state || undefined,
      country_code: addr.country,
      zip: addr.postal_code,
      email: sessionWithItems.customer_details?.email,
      phone: sessionWithItems.customer_details?.phone || undefined,
    };

    const orderBody = {
      external_id: session.id,
      shipping: 'STANDARD',
      recipient,
      items: items.map((i) => ({
        sync_variant_id: i.sync_variant_id,
        quantity: i.quantity,
      })),
    };

    // POST Printful order with confirm=true
    const pfRes = await fetch(`https://api.printful.com/orders?confirm=true`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${PF_KEY}`,
        'X-PF-Store-Id': PF_STORE,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(orderBody),
    });
    const pfJson = await pfRes.json();
    if (!pfRes.ok) {
      throw new Error(`Printful HTTP ${pfRes.status}: ${JSON.stringify(pfJson).slice(0, 500)}`);
    }
    const pfOrder = pfJson.result || {};
    console.log(`✅ Printful order ${pfOrder.id} created for stripe session ${session.id}`);

    // Persist order to Supabase (fashion_orders) — best-effort
    if (process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY) {
      await fetch(`${process.env.SUPABASE_URL}/rest/v1/fashion_orders`, {
        method: 'POST',
        headers: {
          apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
          Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
          'Content-Type': 'application/json',
          Prefer: 'resolution=merge-duplicates,return=minimal',
        },
        body: JSON.stringify({
          stripe_session_id: session.id,
          stripe_payment_intent: session.payment_intent,
          printful_order_id: pfOrder.id,
          customer_email: recipient.email,
          shipping_country: addr.country,
          items: items,
          amount_total_cents: session.amount_total,
          currency: session.currency,
          status: pfOrder.status || 'pending',
          created_at: new Date().toISOString(),
        }),
      }).catch((e) => console.error('supabase insert failed:', e.message));
    }

    // Resend confirmation
    if (RESEND_KEY && recipient.email) {
      const itemList = items
        .map((i) => `• ${i.product_slug} × ${i.quantity}`)
        .join('\n');
      await fetch('https://api.resend.com/emails', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${RESEND_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          from: 'Anicca Fashion <onboarding@resend.dev>',
          to: recipient.email,
          subject: `Order received — Anicca Fashion (${pfOrder.id})`,
          html: `<p>Thanks for your order from Anicca Fashion.</p>
<p><strong>Order #${pfOrder.id}</strong></p>
<pre>${itemList}</pre>
<p>Each piece is printed on demand at a Printful facility — usually shipped within 5–7 business days, delivered in 7–12 days worldwide.</p>
<p>You will get a tracking link as soon as it leaves the printer.</p>
<p>Reply to this email for any question. Anicca answers within 24 hours.</p>
<p>— Anicca</p>`,
        }),
      }).catch((e) => console.error('resend failed:', e.message));
    }

    return {
      statusCode: 200,
      body: JSON.stringify({ ok: true, printful_order_id: pfOrder.id }),
    };
  } catch (err) {
    console.error('webhook error:', err);
    return { statusCode: 500, body: `webhook error: ${err.message}` };
  }
};
