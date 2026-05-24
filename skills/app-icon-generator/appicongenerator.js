#!/usr/bin/env node

const args = process.argv.slice(2);

// Parse CLI arguments
let prompt = null;
let size = 'square';
let tokenFlag = null;
let ref = null;

for (let i = 0; i < args.length; i++) {
  if (args[i] === '--size' && i + 1 < args.length) {
    size = args[++i];
  } else if (args[i] === '--token' && i + 1 < args.length) {
    tokenFlag = args[++i];
  } else if (args[i] === '--ref' && i + 1 < args.length) {
    ref = args[++i];
  } else if (!prompt && !args[i].startsWith('--')) {
    prompt = args[i];
  }
}

const TOKEN = tokenFlag;

if (!TOKEN) {
  console.error('\n\u2717 Token required. Pass via: --token YOUR_TOKEN');
  console.error('  Get yours at: https://www.neta.art/open/');
  process.exit(1);
}

if (!prompt) {
  console.error('\n\u2717 Prompt required. Usage:');
  console.error('  node appicongenerator.js "your prompt" --token YOUR_TOKEN');
  process.exit(1);
}

const SIZES = {
  square: { width: 1024, height: 1024 },
  portrait: { width: 832, height: 1216 },
  landscape: { width: 1216, height: 832 },
  tall: { width: 704, height: 1408 },
};

if (!SIZES[size]) {
  console.error(`\n\u2717 Invalid size "${size}". Choose: square, portrait, landscape, tall`);
  process.exit(1);
}

const { width, height } = SIZES[size];

const headers = {
  'x-token': TOKEN,
  'x-platform': 'nieta-app/web',
  'content-type': 'application/json',
};

const body = {
  storyId: 'DO_NOT_USE',
  jobType: 'universal',
  rawPrompt: [{ type: 'freetext', value: prompt, weight: 1 }],
  width,
  height,
  meta: { entrance: 'PICTURE,VERSE' },
  context_model_series: '8_image_edit',
};

if (ref) {
  body.inherit_params = {
    collection_uuid: ref,
    picture_uuid: ref,
  };
}

async function main() {
  // Submit the image generation task
  const createRes = await fetch('https://api.talesofai.com/v3/make_image', {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!createRes.ok) {
    const text = await createRes.text();
    console.error(`\n\u2717 API error (${createRes.status}): ${text}`);
    process.exit(1);
  }

  const createData = await createRes.json().catch(() => null);
  let taskUuid;

  if (typeof createData === 'string') {
    taskUuid = createData;
  } else if (createData && createData.task_uuid) {
    taskUuid = createData.task_uuid;
  } else {
    // Response might be plain text
    const text = await createRes.clone().text().catch(() => null);
    if (text && typeof text === 'string' && text.length > 0 && !text.startsWith('{')) {
      taskUuid = text.trim();
    } else {
      console.error('\n\u2717 Unexpected response from API:', createData);
      process.exit(1);
    }
  }

  console.error(`\u2713 Task submitted: ${taskUuid}`);
  console.error('  Polling for result...');

  // Poll for completion
  const MAX_ATTEMPTS = 90;
  const POLL_INTERVAL = 2000;

  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL));

    const pollRes = await fetch(`https://api.talesofai.com/v1/artifact/task/${taskUuid}`, {
      method: 'GET',
      headers,
    });

    if (!pollRes.ok) {
      console.error(`  Poll attempt ${attempt} failed (${pollRes.status}), retrying...`);
      continue;
    }

    const pollData = await pollRes.json();
    const status = pollData.task_status;

    if (status === 'PENDING' || status === 'MODERATION') {
      console.error(`  Attempt ${attempt}/${MAX_ATTEMPTS}: ${status}`);
      continue;
    }

    // Task is done
    const imageUrl =
      (pollData.artifacts && pollData.artifacts[0] && pollData.artifacts[0].url) ||
      pollData.result_image_url;

    if (imageUrl) {
      console.log(imageUrl);
      process.exit(0);
    } else {
      console.error('\n\u2717 Task completed but no image URL found in response.');
      console.error('  Response:', JSON.stringify(pollData, null, 2));
      process.exit(1);
    }
  }

  console.error(`\n\u2717 Timed out after ${MAX_ATTEMPTS} polling attempts.`);
  process.exit(1);
}

main().catch((err) => {
  console.error('\n\u2717 Unexpected error:', err.message);
  process.exit(1);
});
