import io as _io

from PIL import Image

from app.ingestion.fetchers import (
    csv_to_text,
    fetch_csv,
    ocr_image,
    read_local_file,
)


def _png_bytes() -> bytes:
    buf = _io.BytesIO()
    Image.new("RGB", (8, 8), (255, 255, 255)).save(buf, format="PNG")
    return buf.getvalue()


CSV_UTF8 = b"application_number,title,inventor\n202301000123,Turmeric wellness Gummies,Ramesh Kumar\n202301000456,Ashwagandha immunity capsule, Priya Sharma\n"

# Latin-1 CSV must still decode via the errors="ignore" path.
CSV_LATIN1 = "name,status\nDr. Jos\u00e9,Approved\n".encode("latin-1")


def test_csv_to_text_flattens_rows_with_headers():
    text = csv_to_text(CSV_UTF8)
    assert "application_number: 202301000123" in text
    assert "title: Turmeric wellness Gummies" in text
    assert "inventor: Ramesh Kumar" in text
    assert "202301000456" in text


def test_csv_to_text_skips_empty_rows():
    data = b"h1,h2\na,b\n\n,, \n,\n"
    text = csv_to_text(data)
    assert "h1: a" in text
    assert "h2: b" in text
    assert "\n" not in text  # only the real row remains
    assert "h1: a | h2: b" in text


def test_csv_to_text_decodes_latin1_gracefully():
    text = csv_to_text(CSV_LATIN1)
    assert "Approved" in text


def test_csv_to_text_returns_empty_for_garbage_bytes():
    assert csv_to_text(b"\x00\xff\xfe broken") == ""


def test_fetch_csv_reads_local_file(tmp_path):
    path = tmp_path / "patents.csv"
    path.write_bytes(CSV_UTF8)
    text = fetch_csv(str(path))
    assert text and "Turmeric wellness Gummies" in text


def test_read_local_file_handles_csv(tmp_path):
    path = tmp_path / "survey.csv"
    path.write_bytes(b"plant,use\nTulsi,Respiratory\n")
    local = read_local_file(str(path))
    assert local is not None
    title, text = local
    assert title == "survey.csv"
    assert "plant: Tulsi" in text


def test_read_local_file_returns_none_for_unknown_ext(tmp_path):
    path = tmp_path / "notes.log"
    path.write_text("hello")
    assert read_local_file(str(path)) is None


def test_ingest_local_corpus_glob_includes_csv_and_images():
    import inspect

    import app.ingestion.pipeline as pipeline_mod

    src_text = inspect.getsource(pipeline_mod.ingest_local_corpus)
    assert "*.csv" in src_text
    assert "*.png" in src_text


def test_ocr_image_returns_none_when_reader_unavailable(monkeypatch):
    monkeypatch.setattr("app.ingestion.fetchers._get_ocr_reader", lambda *a, **k: None)
    assert ocr_image(_png_bytes()) is None


def test_ocr_image_joins_detected_text(monkeypatch):
    class FakeReader:
        def readtext(self, arr, detail=0):
            assert arr is not None
            return ["TULSI", "500 mg"]

    monkeypatch.setattr("app.ingestion.fetchers._get_ocr_reader", lambda *a, **k: FakeReader())
    text = ocr_image(_png_bytes())
    assert text == "TULSI 500 mg"


def test_ocr_image_swallows_decode_failures(monkeypatch):
    class ThrowingReader:
        def readtext(self, arr, detail=0):
            raise RuntimeError("model corrupt")

    monkeypatch.setattr("app.ingestion.fetchers._get_ocr_reader", lambda *a, **k: ThrowingReader())
    assert ocr_image(_png_bytes()) is None


def test_imports_exist_for_upload_router():
    from app.ingestion import fetchers

    assert hasattr(fetchers, "csv_to_text")
    assert hasattr(fetchers, "ocr_image")