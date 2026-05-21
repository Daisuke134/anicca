import { readFile } from 'node:fs/promises';
import sharp from 'sharp';

/**
 * Read a PNG file, convert to JPG, and return as base64 string.
 * Blotato TikTok photo posts require JPG format.
 */
export async function loadImageAsBase64Jpg(pngPath: string): Promise<string> {
  const pngBuffer = await readFile(pngPath);

  const jpgBuffer = await sharp(pngBuffer)
    .jpeg({ quality: 90 })
    .toBuffer();

  return jpgBuffer.toString('base64');
}
