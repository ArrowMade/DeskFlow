"""OCR tool — extract text from screen using macOS Vision framework."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile

from .base import BaseTool, RiskLevel, ToolResult


class OCRScreenTool(BaseTool):
    name = "ocr_screen"
    description = (
        "Extract all visible text from the screen or a specific region using macOS "
        "built-in OCR (Vision framework). Returns text with approximate positions. "
        "Use this to read what's on screen when you need to understand content, "
        "find text, or verify actions worked."
    )
    risk_level = RiskLevel.SAFE

    def get_input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "region": {
                    "type": "object",
                    "description": "Screen region to OCR. Omit for full screen.",
                    "properties": {
                        "x": {"type": "integer", "description": "Left X coordinate"},
                        "y": {"type": "integer", "description": "Top Y coordinate"},
                        "width": {"type": "integer", "description": "Region width"},
                        "height": {"type": "integer", "description": "Region height"},
                    },
                    "required": ["x", "y", "width", "height"],
                },
            },
        }

    async def execute(self, region: dict | None = None) -> ToolResult:
        # Step 1: Take a screenshot (optionally of a region)
        fd, filepath = tempfile.mkstemp(suffix=".png")
        os.close(fd)

        try:
            if region:
                cmd = [
                    "screencapture", "-x",
                    "-R", f"{region['x']},{region['y']},{region['width']},{region['height']}",
                    filepath,
                ]
            else:
                cmd = ["screencapture", "-x", filepath]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)

            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                return ToolResult(
                    output="Screenshot failed. Grant screen recording permission.",
                    success=False,
                )

            # Step 2: Run OCR using macOS Vision framework via Python
            python_script = f'''
import json, sys

try:
    import Vision
    from Foundation import NSURL
    import Quartz
except ImportError:
    print(json.dumps({{"error": "PyObjC Vision framework not available. Run: pip install pyobjc-framework-Vision"}}))
    sys.exit(0)

image_url = NSURL.fileURLWithPath_("{filepath}")
image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
if not image_source:
    print(json.dumps({{"error": "Could not load screenshot"}}))
    sys.exit(0)

cg_image = Quartz.CGImageSourceCreateImageAtIndex(image_source, 0, None)
if not cg_image:
    print(json.dumps({{"error": "Could not create image"}}))
    sys.exit(0)

img_width = Quartz.CGImageGetWidth(cg_image)
img_height = Quartz.CGImageGetHeight(cg_image)

request = Vision.VNRecognizeTextRequest.alloc().init()
request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
request.setUsesLanguageCorrection_(True)

handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, None)
success = handler.performRequests_error_([request], None)

results = []
if success:
    for observation in request.results():
        text = observation.topCandidates_(1)[0].string()
        confidence = observation.topCandidates_(1)[0].confidence()
        bbox = observation.boundingBox()

        # Convert normalized coords to pixel coords
        x = int(bbox.origin.x * img_width)
        y = int((1 - bbox.origin.y - bbox.size.height) * img_height)
        w = int(bbox.size.width * img_width)
        h = int(bbox.size.height * img_height)

        results.append({{
            "text": text,
            "confidence": round(confidence, 2),
            "x": x, "y": y, "w": w, "h": h,
        }})

# Sort by y position (top to bottom), then x (left to right)
results.sort(key=lambda r: (r["y"], r["x"]))
print(json.dumps(results, ensure_ascii=False, indent=2)[:15000])
'''

            proc = await asyncio.create_subprocess_exec(
                "python3", "-c", python_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            output = stdout.decode(errors="replace").strip()
            if not output:
                err_msg = stderr.decode(errors="replace").strip()
                return ToolResult(
                    output=f"OCR failed: {err_msg[:500]}",
                    success=False,
                )

            try:
                data = json.loads(output)
                if isinstance(data, dict) and "error" in data:
                    return ToolResult(output=data["error"], success=False)

                # Build readable output
                lines = []
                lines.append(f"=== Screen Text ({len(data)} blocks) ===\n")
                for item in data:
                    pos = f"({item['x']},{item['y']} {item['w']}x{item['h']})"
                    lines.append(f"[{pos}] {item['text']}")

                return ToolResult(output="\n".join(lines))

            except json.JSONDecodeError:
                return ToolResult(output=output)

        except asyncio.TimeoutError:
            return ToolResult(output="OCR timed out", success=False)
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)
