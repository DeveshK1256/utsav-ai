import zlib

from PIL import Image


class LosslessPDFExporter:
    @classmethod
    def image_to_lossless_pdf(cls, image: Image.Image, dpi: float = 300.0) -> bytes:
        """
        Encapsulates an RGB image into a single-page PDF using FlateDecode
        (lossless zlib compression). Produces a bitwise-lossless raster print PDF.
        """
        rgb = image.convert("RGB")
        w, h = rgb.size
        raw_bytes = rgb.tobytes()
        flate_data = zlib.compress(raw_bytes, level=6)

        pt_w = w * 72.0 / dpi
        pt_h = h * 72.0 / dpi

        body = bytearray()
        body.extend(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

        offsets = {}

        # Obj 1: Catalog
        offsets[1] = len(body)
        body.extend(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")

        # Obj 2: Pages
        offsets[2] = len(body)
        body.extend(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")

        # Obj 3: Page
        offsets[3] = len(body)
        page_dict = (
            f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {pt_w:.4f} {pt_h:.4f}] "
            f"/Contents 4 0 R /Resources << /XObject << /Im1 5 0 R >> "
            "/ProcSet [/PDF /ImageC] >> >>\nendobj\n"
        ).encode("ascii")
        body.extend(page_dict)

        # Obj 4: Content stream (paints image to page dimensions)
        content_stream = f"q {pt_w:.4f} 0 0 {pt_h:.4f} 0 0 cm /Im1 Do Q\n".encode("ascii")
        offsets[4] = len(body)
        body.extend(f"4 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("ascii"))
        body.extend(content_stream)
        body.extend(b"endstream\nendobj\n")

        # Obj 5: Image XObject with FlateDecode
        offsets[5] = len(body)
        im_header = (
            f"5 0 obj\n<< /Type /XObject /Subtype /Image /Width {w} /Height {h} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode "
            f"/Length {len(flate_data)} >>\nstream\n"
        ).encode("ascii")
        body.extend(im_header)
        body.extend(flate_data)
        body.extend(b"\nendstream\nendobj\n")

        # Cross-reference table
        xref_offset = len(body)
        body.extend("xref\n0 6\n0000000000 65535 f \n".encode("ascii"))
        for i in range(1, 6):
            body.extend(f"{offsets[i]:010d} 00000 n \n".encode("ascii"))

        trailer = (f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n").encode(
            "ascii"
        )
        body.extend(trailer)
        return bytes(body)

    # ---------------------------------------------------------
    # Classic Royal Helpers
    # ---------------------------------------------------------
