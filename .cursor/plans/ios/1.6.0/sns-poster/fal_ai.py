"""
Fal.ai API Wrapper
画像/動画/音声生成
"""
import time
import requests
from typing import Optional, Dict, Any
from config import FAL_API_KEY, FAL_BASE_URL


class FalAIClient:
    """Fal.ai API Client"""

    def __init__(self, api_key: str = FAL_API_KEY):
        self.api_key = api_key
        self.base_url = FAL_BASE_URL
        self.headers = {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

    def _queue_request(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit to Fal.ai queue and wait for result"""
        url = f"{self.base_url}/{endpoint}"
        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        result = response.json()

        # If queued, poll for completion using the URLs from response
        if "request_id" in result:
            status_url = result.get("status_url", "")
            response_url = result.get("response_url", "")
            return self._wait_for_completion(status_url, response_url)
        return result

    def _wait_for_completion(
        self, status_url: str, response_url: str, timeout: int = 300, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """Poll for queue completion using URLs from initial response"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check status
            response = requests.get(status_url, headers=self.headers)
            response.raise_for_status()
            status = response.json()

            current_status = status.get("status", "unknown")
            if current_status == "COMPLETED":
                # Fetch result
                result_response = requests.get(response_url, headers=self.headers)
                result_response.raise_for_status()
                return result_response.json()
            elif current_status == "FAILED":
                raise Exception(f"Fal.ai request failed: {status}")

            print(f"  ⏳ Status: {current_status}...")
            time.sleep(poll_interval)

        raise TimeoutError(f"Fal.ai request timed out after {timeout}s")

    # =========================================================================
    # Image Generation (FLUX)
    # =========================================================================
    def generate_image(
        self,
        prompt: str,
        image_size: str = "square_hd",
        num_images: int = 1,
    ) -> Dict[str, Any]:
        """Generate image using FLUX Schnell"""
        payload = {
            "prompt": prompt,
            "image_size": image_size,
            "num_images": num_images,
        }
        print(f"🖼️ Generating image: {prompt[:50]}...")
        return self._queue_request("fal-ai/flux/schnell", payload)

    # =========================================================================
    # Video Generation (Seedance)
    # =========================================================================
    def generate_video(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        duration: int = 5,
    ) -> Dict[str, Any]:
        """Generate video using Seedance Pro (Bytedance)"""
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
        }
        print(f"🎬 Generating video: {prompt[:50]}...")
        return self._queue_request("fal-ai/bytedance/seedance/v1/pro/text-to-video", payload)

    # =========================================================================
    # Audio Generation (MMAudio)
    # =========================================================================
    def generate_audio(
        self,
        prompt: str,
        duration: int = 10,
    ) -> Dict[str, Any]:
        """Generate audio using MMAudio v2"""
        payload = {
            "prompt": prompt,
            "duration": duration,
        }
        print(f"🔊 Generating audio: {prompt[:50]}...")
        return self._queue_request("fal-ai/mmaudio-v2/text-to-audio", payload)

    # =========================================================================
    # Kling 2.5 Pro (高品質動画)
    # =========================================================================
    def generate_video_kling(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        duration: str = "5",
    ) -> Dict[str, Any]:
        """Generate video using Kling 2.5 Turbo Pro"""
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "duration": duration,
        }
        print(f"🎬 Generating Kling video: {prompt[:50]}...")
        return self._queue_request("fal-ai/kling-video/v2.5-turbo/pro/text-to-video", payload)

    # =========================================================================
    # Ideogram v3 (テキスト入り画像生成)
    # =========================================================================
    def generate_image_ideogram(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        style_type: str = "general",
    ) -> Dict[str, Any]:
        """Generate image with text using Ideogram v3 (best for text in images)"""
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "style_type": style_type,
        }
        print(f"🖼️ Generating Ideogram image: {prompt[:50]}...")
        return self._queue_request("fal-ai/ideogram/v3", payload)

    # =========================================================================
    # Nano Banana Pro (Google Gemini - 最強テキスト生成)
    # =========================================================================
    def generate_image_nano_banana(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
    ) -> Dict[str, Any]:
        """Generate image with text using Nano Banana Pro (Google Gemini 2.5 Flash Image)"""
        payload = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
        }
        print(f"🍌 Generating Nano Banana image: {prompt[:50]}...")
        return self._queue_request("fal-ai/nano-banana-pro", payload)


# =============================================================================
# Quick Access Functions
# =============================================================================
_client = None


def get_client() -> FalAIClient:
    """Get singleton client instance"""
    global _client
    if _client is None:
        _client = FalAIClient()
    return _client


def generate_image(prompt: str, size: str = "square_hd") -> str:
    """Generate image and return URL"""
    result = get_client().generate_image(prompt, size)
    images = result.get("images", [])
    if images:
        return images[0].get("url", "")
    return ""


def generate_video(prompt: str, aspect_ratio: str = "9:16", duration: int = 10) -> str:
    """Generate video and return URL"""
    result = get_client().generate_video(prompt, aspect_ratio, duration)
    video = result.get("video", {})
    return video.get("url", "")


def generate_audio(prompt: str, duration: int = 10) -> str:
    """Generate audio and return URL"""
    result = get_client().generate_audio(prompt, duration)
    audio = result.get("audio", {})
    return audio.get("url", "")


if __name__ == "__main__":
    # Test: Generate a simple image
    print("=== Fal.ai Test ===")
    client = FalAIClient()

    # Quick test with a simple prompt
    result = client.generate_image("A peaceful zen garden with morning light", num_images=1)
    print(f"✅ Image generated: {result.get('images', [{}])[0].get('url', 'N/A')}")

