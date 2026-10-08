"""Colour helpers: turn any picture (CMYK, Adobe RGB, P3 ...) into plain sRGB.

Pictures saved for print are often CMYK. Converting them with a simple
"convert('RGB')" gives too-bright, neon colours, so the colour profile stored
inside the file is used instead. CMYK files without a profile fall back to
Japan Color 2001 Coated (cmyk.icc, next to this file).
"""
import io
import os

from PIL import Image, ImageCms

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRGB = ImageCms.createProfile("sRGB")
_CMYK_FALLBACK = os.path.join(_HERE, "cmyk.icc")


def to_srgb(im):
    """Return an RGB copy of `im` with correct colours."""
    icc = im.info.get("icc_profile")
    if im.mode in ("P", "LA", "L", "1"):
        im = im.convert("RGBA" if "A" in im.mode or im.mode == "P" else "RGB")
    try:
        if icc:
            src = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            if im.mode == "RGBA":
                im = im.convert("RGB")
            return ImageCms.profileToProfile(im, src, _SRGB, outputMode="RGB", renderingIntent=0)
        if im.mode == "CMYK" and os.path.exists(_CMYK_FALLBACK):
            return ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(_CMYK_FALLBACK), _SRGB,
                                             outputMode="RGB", renderingIntent=0)
    except Exception as exc:
        print(f"  ! colour profile not used: {exc}")
    return im.convert("RGB")
