"""AI-powered tools — chat, summarize, code review, image generation.

All cmd_* functions return str (plain text).
Uses LLMClient from agent.llm for LLM calls.
"""

import os
import subprocess
import time

import requests

from zhixing.agent.llm import LLMClient
from zhixing.config import Config


def _get_client(model: str | None = None) -> LLMClient:
    """Create an LLMClient from the global config, optionally overriding the model."""
    config = Config()
    client = LLMClient(config)
    if model:
        client.model = model
    return client


def _call_llm(prompt: str, system: str = "", model: str | None = None) -> str:
    """Send a chat message to the LLM and return the response text."""
    client = _get_client(model)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        response = client.chat(messages)
        content = response["choices"][0]["message"].get("content", "")
        return content or "(empty response)"
    except (ConnectionError, TimeoutError, ValueError) as e:
        return f"LLM call failed: {e}"
    except Exception as e:
        return f"LLM call failed: {e}"


# ── Command Handlers ─────────────────────────────────────


def cmd_chat(params: dict) -> str:
    """Chat directly with the LLM without agent routing.

    Parameters:
        prompt (str): The chat prompt/message.
        model (str, optional): Override the default model.
    """
    prompt = params.get("prompt", "")
    model = params.get("model", None)

    if not prompt:
        return "❌ Need 'prompt' parameter"

    reply = _call_llm(prompt, model=model)
    return f"💬 {reply}"


def cmd_summarize(params: dict) -> str:
    """Summarize text from a URL or direct text input.

    Parameters:
        url (str, optional): URL to fetch and summarize.
        text (str, optional): Direct text to summarize.
        max_length (int, optional): Maximum summary length in words. Default 200.
    """
    url = params.get("url", "")
    text = params.get("text", "")
    max_length = int(params.get("max_length", 200))

    if not url and not text:
        return "❌ Need either 'url' or 'text' parameter"

    content = ""
    source_desc = ""

    if url:
        try:
            resp = requests.get(url, timeout=30, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Zhixing/1.0)"
            })
            resp.raise_for_status()
            raw_html = resp.text
            source_desc = url

            # Extract readable text by stripping HTML tags
            try:
                from html.parser import HTMLParser

                class TextExtractor(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self._text = []
                        self._skip = False

                    def handle_starttag(self, tag, attrs):
                        if tag in ("script", "style"):
                            self._skip = True

                    def handle_endtag(self, tag):
                        if tag in ("script", "style"):
                            self._skip = False

                    def handle_data(self, data):
                        if not self._skip:
                            stripped = data.strip()
                            if stripped:
                                self._text.append(stripped)

                extractor = TextExtractor()
                extractor.feed(raw_html)
                extracted = " ".join(extractor._text)
                if extracted:
                    content = extracted
                else:
                    content = raw_html
            except Exception:
                content = raw_html

            # Truncate very long content
            if len(content) > 15000:
                content = content[:15000] + "\n... [truncated]"

        except requests.RequestException as e:
            return f"❌ Failed to fetch URL: {e}"
    else:
        content = text
        source_desc = "provided text"

    if not content.strip():
        return "❌ No content to summarize"

    prompt_text = (
        f"Please summarize the following content in no more than {max_length} words. "
        f"Provide a concise, informative summary covering the key points.\n\n"
        f"--- Content to summarize ---\n{content}\n--- End ---"
    )

    summary = _call_llm(prompt_text, system="You are a professional summarizer.")
    return f"📝 Summary of {source_desc}:\n\n{summary}"


def cmd_code_review(params: dict) -> str:
    """Review a source code file using the LLM.

    Parameters:
        path (str): Path to the file to review.
        language (str, optional): Programming language. Default "python".
    """
    path = params.get("path", "")
    language = params.get("language", "python")

    if not path:
        return "❌ Need 'path' parameter"

    if not os.path.exists(path):
        return f"❌ File not found: {path}"

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except Exception as e:
        return f"❌ Failed to read file: {e}"

    if not code.strip():
        return "❌ File is empty"

    # Truncate very large files
    if len(code) > 20000:
        code = code[:20000] + "\n# ... [file truncated due to length]"

    prompt_text = (
        f"Please review this {language} code. Analyze it for:\n"
        f"1. Bugs and logical errors\n"
        f"2. Security vulnerabilities\n"
        f"3. Performance issues\n"
        f"4. Code style and maintainability\n"
        f"5. Potential improvements\n\n"
        f"```{language}\n{code}\n```\n\n"
        f"Provide specific, actionable feedback. If no issues found, note that."
    )

    review = _call_llm(
        prompt_text,
        system="You are a senior software engineer conducting a thorough code review.",
    )
    return f"🔍 Code Review — {path}\n\n{review}"


def cmd_image_gen(params: dict) -> str:
    """Generate an image using DALL-E 3 via OpenAI API.

    Parameters:
        prompt (str): Image description prompt.
        size (str, optional): Image size. Default "1024x1024".
            Options: "1024x1024", "1792x1024", "1024x1792".
    """
    prompt = params.get("prompt", "")
    size = params.get("size", "1024x1024")

    if not prompt:
        return "❌ Need 'prompt' parameter"

    if size not in ("1024x1024", "1792x1024", "1024x1792"):
        return (
            f"❌ Invalid size '{size}'. "
            f"Options: 1024x1024, 1792x1024, 1024x1792"
        )

    config = Config()
    api_key = config.get("llm.api_key", "")

    if not api_key:
        return (
            "❌ OpenAI API key not configured.\n"
            "  Set it in ~/.zhixing/config.yaml:\n"
            "  llm:\n"
            "    api_key: sk-..."
        )

    try:
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "quality": "standard",
            },
            timeout=120,
        )
        response.raise_for_status()
        data = response.json()

        image_url = data["data"][0]["url"]
        revised_prompt = data["data"][0].get("revised_prompt", "")

        # Download the image
        img_resp = requests.get(image_url, timeout=60)
        img_resp.raise_for_status()

        # Determine file extension from content-type
        content_type = img_resp.headers.get("content-type", "")
        if "jpeg" in content_type or "jpg" in content_type:
            ext = ".jpg"
        elif "webp" in content_type:
            ext = ".webp"
        else:
            ext = ".png"

        output_dir = os.path.expanduser("~/Pictures/zhixing")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"dalle_{int(time.time())}{ext}")

        with open(output_path, "wb") as f:
            f.write(img_resp.content)

        # Open the image with default viewer
        subprocess.run(["open", output_path], capture_output=True, timeout=10)

        result = (
            f"✅ Image generated and saved: {output_path}\n"
            f"🖼 Size: {size}"
        )
        if revised_prompt and revised_prompt != prompt:
            result += f"\n📝 Revised prompt: {revised_prompt}"
        return result

    except requests.RequestException as e:
        return f"❌ Image generation failed: {e}"
    except KeyError as e:
        return f"❌ Unexpected API response: {e}"
    except Exception as e:
        return f"❌ Image generation failed: {e}"


# ── Command Registry ─────────────────────────────────────

COMMANDS: dict = {
    "chat": cmd_chat,
    "summarize": cmd_summarize,
    "code_review": cmd_code_review,
    "image_gen": cmd_image_gen,
}

TOOL_SCHEMAS: dict = {
    "chat": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The chat prompt/message to send to the LLM",
            },
            "model": {
                "type": "string",
                "description": "Override the default model (optional)",
            },
        },
        "required": ["prompt"],
    },
    "summarize": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to fetch and summarize",
            },
            "text": {
                "type": "string",
                "description": "Text content to summarize directly",
            },
            "max_length": {
                "type": "integer",
                "description": "Maximum summary length in words, default 200",
                "default": 200,
            },
        },
    },
    "code_review": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Absolute path to the file to review",
            },
            "language": {
                "type": "string",
                "description": "Programming language of the file, default 'python'",
                "default": "python",
            },
        },
        "required": ["path"],
    },
    "image_gen": {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "Description of the image to generate",
            },
            "size": {
                "type": "string",
                "description": "Image size: 1024x1024, 1792x1024, or 1024x1792",
                "default": "1024x1024",
                "enum": ["1024x1024", "1792x1024", "1024x1792"],
            },
        },
        "required": ["prompt"],
    },
}
