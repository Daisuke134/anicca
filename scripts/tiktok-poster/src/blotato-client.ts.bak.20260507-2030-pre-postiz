const BLOTATO_API_BASE = 'https://backend.blotato.com/v2';

interface BlotatoClientOptions {
  dryRun?: boolean;
  apiKey?: string;
}

export interface BlotatoPostResult {
  postSubmissionId: string;
}

export interface BlotatoStatusResult {
  status: string;
  publicUrl: string | null;
}

export class BlotatoClient {
  private readonly dryRun: boolean;
  private readonly apiKey: string;

  constructor(options: BlotatoClientOptions = {}) {
    this.dryRun = options.dryRun ?? false;
    this.apiKey = options.apiKey ?? '';

    if (!this.dryRun && !this.apiKey) {
      throw new Error(
        'BLOTATO_API_KEY required. Use --dry-run for testing without credentials.',
      );
    }
  }

  /** Upload image to Blotato CDN via source URL. Returns CDN URL. */
  async uploadMedia(sourceUrl: string): Promise<{ url: string }> {
    if (this.dryRun) {
      return { url: `https://dry-run-cdn.example.com/${Date.now()}.jpg` };
    }

    const res = await fetch(`${BLOTATO_API_BASE}/media`, {
      method: 'POST',
      headers: {
        'blotato-api-key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ url: sourceUrl }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Blotato media upload failed: HTTP ${res.status} — ${text}`);
    }

    const data = (await res.json()) as { url?: string };
    if (!data.url) {
      throw new Error('Blotato media upload returned no URL');
    }

    return { url: data.url };
  }

  /** Post a photo to TikTok via Blotato. Returns postSubmissionId. */
  async postPhoto(
    accountId: string,
    imageUrl: string,
    caption: string,
  ): Promise<BlotatoPostResult> {
    if (this.dryRun) {
      return { postSubmissionId: `dry-post-${Date.now()}` };
    }

    const res = await fetch(`${BLOTATO_API_BASE}/posts`, {
      method: 'POST',
      headers: {
        'blotato-api-key': this.apiKey,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        post: {
          accountId,
          content: {
            // B2: conservative limit to avoid provider-side counting mismatch
            text: caption.slice(0, 2000),
            mediaUrls: [imageUrl],
            platform: 'tiktok',
          },
          target: {
            targetType: 'tiktok',
            privacyLevel: 'PUBLIC_TO_EVERYONE',
            disabledComments: false,
            disabledDuet: false,
            disabledStitch: false,
            isBrandedContent: false,
            isYourBrand: false,
            isAiGenerated: false,
          },
        },
      }),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      throw new Error(`Blotato post failed: HTTP ${res.status} — ${text}`);
    }

    const data = (await res.json()) as { id?: string; postSubmissionId?: string };
    const postId = data.postSubmissionId ?? data.id;
    if (!postId) {
      throw new Error(`Blotato post returned no ID: ${JSON.stringify(data)}`);
    }

    return { postSubmissionId: postId };
  }

  /** Check post status by postSubmissionId. Used for TTL recovery. */
  async checkPostStatus(
    postSubmissionId: string,
  ): Promise<BlotatoStatusResult | null> {
    if (this.dryRun) {
      return null;
    }

    try {
      const res = await fetch(`${BLOTATO_API_BASE}/posts/${postSubmissionId}`, {
        method: 'GET',
        headers: {
          'blotato-api-key': this.apiKey,
        },
      });

      if (!res.ok) return null;

      const data = (await res.json()) as {
        status?: string;
        publicUrl?: string;
      };

      if (!data.status) return null;

      return {
        status: data.status,
        publicUrl: data.publicUrl ?? null,
      };
    } catch {
      return null;
    }
  }
}
