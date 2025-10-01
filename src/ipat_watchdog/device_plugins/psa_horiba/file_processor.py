"""Processor for Horiba Partica LA-960 exports (no staging; Probenname buckets; sentinel.ngb finalize).

Flow:
- We collect CSVs + NGBs in memory per watch folder + Probenname.
- When 'sentinel.ngb' arrives, we DO NOT move files yet. We:
    * remember the whole bucket under _finalizing[sentinel_path]
    * return a **synthetic path** whose filename is "<Probenname>.ngb"
      so the pipeline uses <Probenname> as the record prefix.
- Later, device_specific_processing() is called with the real sentinel path.
  We pull the bucket from _finalizing and:
    * zip all .ngb into "<Probenname>.zip", numbering contiguously and
      continuing if the zip already exists (append case)
    * convert TSV->semicolon and move CSVs into the record directory,
      continuing numbering if files already exist (append case)
"""

from __future__ import annotations

from pathlib import Path
import time
import re
import zipfile
from dataclasses import dataclass, field
from typing import Dict, Optional, List

from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.records.local_record import LocalRecord
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    move_to_exception_folder,
    get_unique_filename
)
from ipat_watchdog.core.records.record_manager import RecordManager
from ipat_watchdog.core.records.local_record import LocalRecord

logger = setup_logger(__name__)

# ------------------------------
# Tunables / constants
# ------------------------------

# Header key (lowercased) for the user-entered sample name.
_PROBENAME_KEY = "probenname"

def _is_sentinel_ngb(p: Path) -> bool:
    """True for an .ngb named exactly 'sentinel.ngb' (case-insensitive stem)."""
    return p.suffix.lower() == ".ngb" and p.stem.lower() == "sentinel"

_MAX_PREFIX_BYTES = 200_000  # read enough to capture header
_VALID_NAME_RE = re.compile(r"[A-Za-z0-9._\-+=@()\[\]{} ]+$")

# Convert Horiba TSVs to semicolon (avoid conflict with German decimal commas).
CONVERT_TSV_TO_SEMICOLON = True
_TARGET_DELIMITER = ";"


def _id_separator() -> str:
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP


# ------------------------------
# Session state
# ------------------------------

@dataclass
class _SessionBucket:
    """In-flight Horiba session (per watch folder)."""
    t: float
    dir: Path
    probename: Optional[str] = None
    csvs: List[Path] = field(default_factory=list)
    ngbs: List[Path] = field(default_factory=list)
    first_arrival_kind: Optional[str] = None  # "res" or "raw"


# ------------------------------
# Processor (no staging)
# ------------------------------

class FileProcessorPSAHoriba(FileProcessorABS):
    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        # Pending by "<folder>::<Probenname>" or "<folder>::__open__<epoch>"
        self._pending: Dict[str, _SessionBucket] = {}
        # Buckets ready to finalize, keyed by REAL sentinel path string.
        self._finalizing: Dict[str, _SessionBucket] = {}
        self.device_config = device_config

    # ------------------------------------------------------------------
    # Pre-processing
    # ------------------------------------------------------------------
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        element = Path(path)
        ext = element.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            kind = "raw"   # .ngb
        elif ext in exported_exts:
            kind = "res"   # .csv / tsv
        else:
            return path

        folder = element.parent

        # CSV arrival: attach to bucket keyed by Probenname
        if kind == "res":
            meta = {}
            try:
                meta = self._parse_csv_metadata(element)
            except Exception as e:
                logger.warning("PSA: failed parsing CSV metadata '%s': %s", element, e)

            probenname = (meta.get(_PROBENAME_KEY) or "").strip() or None
            bkey = self._make_bucket_key(folder, probenname, f"__open__{int(time.time())}")
            bucket = self._touch_bucket(bkey, folder, first_kind="res")
            if probenname:
                bucket.probename = probenname
            bucket.csvs.append(element)
            bucket.t = time.time()

            logger.debug("PSA: CSV attached: probename=%r, bucket=%s, #csv=%d, #ngb=%d",
                         bucket.probename, bkey, len(bucket.csvs), len(bucket.ngbs))
            self._purge_orphans()
            return None

        # NGB arrival: attach; finalize only if sentinel
        if kind == "raw":
            bkey = self._pick_bucket_for_ngb(folder) or self._make_bucket_key(folder, None, f"__open__{int(time.time())}")
            bucket = self._touch_bucket(bkey, folder, first_kind="raw")
            bucket.ngbs.append(element)
            bucket.t = time.time()

            is_sentinel = _is_sentinel_ngb(element)
            logger.debug("PSA: NGB attached: bucket=%s, #ngb=%d, sentinel=%s",
                         bkey, len(bucket.ngbs), is_sentinel)

            if not is_sentinel:
                self._purge_orphans()
                return None

            # --- FINALIZE trigger
            self._finalizing[str(element)] = bucket
            self._pending.pop(bkey, None)

            # Advertise a synthetic path "<Probenname>.ngb" so the pipeline uses Probenname as prefix
            advertised_prefix = self._choose_probename_for_advertising(bucket) or element.stem or "psa_session"
            synthetic = element.with_name(f"{advertised_prefix}{element.suffix}")

            self._purge_orphans()
            return str(synthetic)

        return None

    # ------------------------------------------------------------------
    # Probing (route CSVs here)
    # ------------------------------------------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        path = Path(filepath)
        ext = path.suffix.lower()
        native_exts = self.device_config.files.native_extensions
        exported_exts = self.device_config.files.exported_extensions

        if ext in native_exts:
            return FileProbeResult.unknown("Binary raw file; probe skipped")
        if ext not in exported_exts:
            return FileProbeResult.mismatch("Unsupported extension for PSA Horiba")

        try:
            snippet = self._read_text_prefix(path)
        except Exception as exc:
            logger.debug("PSA probe failed to read '%s': %s", path, exc)
            return FileProbeResult.unknown(str(exc))

        text = snippet.lower()
        score = sum(tok in text for tok in ["horiba", "partica", "la-960", "psa", "diameter"]) \
                - sum(tok in text for tok in ["dissolution", "cumulative release"])
        if score <= 0:
            return FileProbeResult.unknown("CSV content inconclusive for PSA Horiba")
        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(confidence=confidence, reason=f"Found PSA markers (score={score})")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "psa_horiba"

    # ------------------------------------------------------------------
    # Processing (zip NGBs; convert/move CSVs; append-aware)
    # ------------------------------------------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        """
        Finalize a PSA Horiba acquisition when the real sentinel.ngb arrives.

        New strategy:
        - Each NON-sentinel .ngb is zipped into its own archive:
              <base><sep><NN>.zip  (NN = 01,02,... continuing any existing set)
        - Inside each zip the file is stored as <base><sep><NN>.ngb
        - Sentinel .ngb (single) is ALSO zipped (added last in the ordering)
        - CSV / TSV files are moved (with optional tab->semicolon conversion)
          using get_unique_filename for collision avoidance.
        """
        sentinel = Path(src_path)
        bucket = self._finalizing.pop(str(sentinel), None)
        if not bucket:
            raise RuntimeError("Finalizing bucket not found for sentinel; cannot continue")

        base = filename_prefix
        record_dir = Path(record_path)
        sep = _id_separator()

        # --- Prepare NGB list (sentinel last)
        ngb_regular = [p for p in bucket.ngbs if not _is_sentinel_ngb(p)]
        ngb_regular.sort(key=lambda p: p.name)
        sentinel_ngb = next((p for p in bucket.ngbs if _is_sentinel_ngb(p)), None)
        ngb_all: List[Path] = list(ngb_regular)
        if sentinel_ngb:
            # append sentinel explicitly so it's numbered after regular ones
            ngb_all.append(sentinel_ngb)

        # --- Determine next sequential index from existing per-NGB archives
        # Pattern: <base><sep>NN.zip
        import re
        pat_zip = re.compile(rf"^{re.escape(base)}{re.escape(sep)}(\d{{2}})\.zip$", re.IGNORECASE)
        max_existing = 0
        for existing in record_dir.glob(f"{base}{sep}*.zip"):
            m = pat_zip.match(existing.name)
            if m:
                try:
                    max_existing = max(max_existing, int(m.group(1)))
                except Exception:
                    pass
        next_idx = max_existing + 1

        # --- Zip each raw NGB separately (including sentinel if present at end)
        for raw_path in ngb_all:
            zip_name = f"{base}{sep}{next_idx:02d}.zip"
            zip_path = record_dir / zip_name
            arcname = f"{base}{sep}{next_idx:02d}.ngb"
            try:
                with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(raw_path, arcname=arcname)
                try:
                    raw_path.unlink(missing_ok=True)
                except Exception:
                    pass
                logger.debug("PSA: Created archive '%s' from '%s'", zip_path, raw_path)
            except Exception as exc:
                logger.warning("PSA: Failed to archive '%s': %s", raw_path, exc)
            next_idx += 1

        # (Sentinel already unlinked above if present)

        # --- Process CSV / TSV outputs
        csv_candidates = sorted(bucket.csvs, key=lambda p: p.name)
        for src in csv_candidates:
            try:
                dest_path = Path(get_unique_filename(record_path, base, src.suffix))
                if CONVERT_TSV_TO_SEMICOLON:
                    self._convert_tsv_to_semicolon(src, dest_path)
                else:
                    move_item(str(src), str(dest_path))
                logger.debug("PSA: Moved result file '%s' -> '%s'", src, dest_path)
            except Exception as exc:
                logger.warning("PSA: Failed handling result file '%s': %s", src, exc)

        return ProcessingOutput(final_path=str(record_dir), datatype="psa")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _read_text_prefix(path: Path, bytes_limit: int = 4096) -> str:
        raw = path.read_bytes()[:bytes_limit]
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                return raw.decode(enc, errors="ignore")
            except Exception:
                continue
        return raw.decode(errors="ignore")

    def _parse_csv_metadata(self, p: Path) -> Dict[str, str]:
        """
        Parse Horiba header key/value lines until the real numeric table begins.
        Accept TAB or ';' in header. (You mentioned you’ve tuned this—feel free to
        swap in your preferred version; this one is robust by default.)
        """
        def _is_table_header_token(token: str) -> bool:
            t = token.strip().strip('"').strip()
            if re.match(r'^[xX]\([^)]*\)$', t):  # exactly X(...)
                return True
            # numeric-like (incl. German comma decimals)
            return bool(re.match(r'^[\s]*[0-9]*[.,]?[0-9]+([\sEe][+-]?[0-9]+)?\s*$', t))

        text = self._read_text_prefix(p, bytes_limit=_MAX_PREFIX_BYTES)
        if not text:
            return {}
        meta: Dict[str, str] = {}
        for raw in text.splitlines():
            ls = raw.strip()
            if not ls:
                continue
            parts = re.split(r"\t+|;", ls)
            if not parts:
                continue
            first = parts[0].strip().strip('"').strip("\ufeff")
            if _is_table_header_token(first):
                break
            if len(parts) >= 2:
                k = first.lower()
                v = parts[1].strip().strip('"')
                if k and v:
                    meta[k] = v
        return meta


    def _choose_probename_for_advertising(self, bucket: _SessionBucket) -> Optional[str]:
        """Prefer stored bucket.probename; otherwise parse the first CSV if available."""
        if bucket.probename:
            return bucket.probename
        if bucket.csvs:
            try:
                meta = self._parse_csv_metadata(sorted(bucket.csvs, key=lambda p: p.name)[0])
                pn = (meta.get(_PROBENAME_KEY) or "").strip()
                if pn:
                    return pn
            except Exception:
                pass
        return None

    def _make_bucket_key(self, folder: Path, probename: Optional[str], fallback_suffix: str) -> str:
        return f"{folder}::{probename}" if probename else f"{folder}::{fallback_suffix}"

    def _touch_bucket(self, key: str, folder: Path, first_kind: str) -> _SessionBucket:
        b = self._pending.get(key)
        if b is None:
            b = _SessionBucket(t=time.time(), dir=folder, first_arrival_kind=first_kind)
            self._pending[key] = b
        elif b.first_arrival_kind is None:
            b.first_arrival_kind = first_kind
        return b

    def _pick_bucket_for_ngb(self, folder: Path) -> Optional[str]:
        choices = [(k, v) for k, v in self._pending.items() if v.dir == folder]
        if not choices:
            return None
        choices.sort(key=lambda kv: (0 if kv[1].csvs else 1, -kv[1].t))
        return choices[0][0]

    def _purge_orphans(self) -> None:
        now = time.time()
        ttl = getattr(self.device_config, "batch", None)
        ttl_seconds = getattr(ttl, "ttl_seconds", 600) if ttl else 600
        stale_keys = [key for key, payload in self._pending.items() if now - float(payload.t) > ttl_seconds]
        for key in stale_keys:
            payload = self._pending.pop(key, None)
            if not payload:
                continue
            for p in [*payload.csvs, *payload.ngbs]:
                if isinstance(p, Path) and p and p.exists():
                    try:
                        move_to_exception_folder(str(p))
                        logger.info("PSA: purged orphan '%s'", p)
                    except Exception as exc:
                        logger.warning("PSA: could not purge orphan '%s': %s", p, exc)

    # ------------------------------
    # Append-awareness helpers
    # ------------------------------
    def _max_index_in_zip(self, zf: zipfile.ZipFile, base: str, sep: str) -> int:
        pat_idx = re.compile(rf"^{re.escape(base)}{re.escape(sep)}(\d{{2}})\.ngb$", re.IGNORECASE)
        max_idx = 0
        for info in zf.infolist():
            fn = info.filename
            if fn.lower() == f"{base.lower()}.ngb":
                max_idx = max(max_idx, 1)
            else:
                m = pat_idx.match(fn)
                if m:
                    try:
                        max_idx = max(max_idx, int(m.group(1)))
                    except Exception:
                        pass
        return max_idx

    def _max_index_for_existing_csvs(self, record_dir: Path, base: str, ext: str, sep: str) -> int:
        pattern = re.compile(rf"^{re.escape(base)}{re.escape(sep)}(\d{{2}}){re.escape(ext)}$", re.IGNORECASE)
        max_idx = 0
        for p in record_dir.glob(f"{base}*{ext}"):
            m = pattern.match(p.name)
            if m:
                try:
                    max_idx = max(max_idx, int(m.group(1)))
                except Exception:
                    pass
        return max_idx

    # ------------------------------
    # CSV conversion helper
    # ------------------------------
    def _convert_tsv_to_semicolon(self, src: Path, dest: Path) -> None:
        data = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                data = src.read_text(encoding=enc, errors="ignore")
                break
            except Exception:
                data = None
        if data is None:
            raise RuntimeError(f"Unable to read CSV for conversion: {src}")

        converted = data.replace("\t", _TARGET_DELIMITER)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(converted, encoding="utf-8")
        try:
            src.unlink(missing_ok=True)
        except Exception:
            pass
