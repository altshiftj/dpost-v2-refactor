from __future__ import annotations

from pathlib import Path
import time
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, Optional

from ipat_watchdog.core.config import constants as _CONST
from ipat_watchdog.core.config import current
from ipat_watchdog.core.config.schema import DeviceConfig
from ipat_watchdog.core.logging.logger import setup_logger
from ipat_watchdog.core.processing.file_processor_abstract import (
    FileProcessorABS,
    FileProbeResult,
    ProcessingOutput,
)
from ipat_watchdog.core.storage.filesystem_utils import (
    move_item,
    move_to_exception_folder,
    get_unique_filename,
)
from ipat_watchdog.core.records.local_record import LocalRecord

logger = setup_logger(__name__)

# ----------------------------------
# Tunables / constants
# ----------------------------------
_PROBENAME_KEY = "probenname"
_MAX_PREFIX_BYTES = 200_000
_TARGET_DELIM = ";"  # convert tabs → semicolon


def _id_separator() -> str:
    try:
        return current().id_separator
    except RuntimeError:
        return _CONST.ID_SEP


def _is_ngb(p: Path) -> bool:
    return p.suffix.lower() == ".ngb"


def _is_csv_like(p: Path) -> bool:
    return p.suffix.lower() in {".csv", ".tsv"}


@dataclass
class _Pending:
    t: float
    folder: Path
    csv_path: Optional[Path] = None
    probenname: Optional[str] = None


class FileProcessorPSAHoriba(FileProcessorABS):
    """Atomic two-step: CSV first, then a single NGB triggers processing.

    Preprocessing
    ------------
    • On CSV: parse Probenname, remember CSV for the folder, return None.
    • On NGB: if we have a pending CSV, stash the pair for finalization and
      return a **synthetic path** whose filename is "<Probenname>.ngb" to make
      the pipeline use <Probenname> as the filename_prefix.

    Processing
    ----------
    • Rename CSV to the incoming fileprefix (get_unique_filename) and convert
      TAB → ';'.
    • Zip the NGB into <prefix>.zip (unique via get_unique_filename), storing
      the entry as <prefix>.ngb.
    • Move both artifacts to the record folder.
    """

    def __init__(self, device_config: DeviceConfig) -> None:
        super().__init__(device_config)
        self.device_config = device_config
        # keyed by absolute folder path (str)
        self._pending: Dict[str, _Pending] = {}
        # buckets ready to finalize, keyed by REAL ngb path (str)
        self._finalizing: Dict[str, _Pending] = {}

    # -------------------------------
    # Pre-processing
    # -------------------------------
    def device_specific_preprocessing(self, path: str) -> Optional[str]:
        p = Path(path)
        folder_key = str(p.parent.resolve())

        if _is_csv_like(p):
            # Remember CSV metadata so we can rename the eventual NGB using its Probenname.
            pend = self._pending.get(folder_key) or _Pending(t=time.time(), folder=p.parent)
            try:
                meta = self._parse_csv_metadata(p)
            except Exception as e:
                logger.warning("PSA: CSV metadata parse failed for %s: %s", p, e)
                meta = {}

            pn = (meta.get(_PROBENAME_KEY) or "").strip() or None
            if not pn:
                pn = p.stem  # fall back to filename stem
            pend.csv_path = p
            pend.probenname = pn
            pend.t = time.time()
            self._pending[folder_key] = pend
            logger.debug("PSA: remembered CSV %s with probenname=%r", p, pn)
            self._purge_stale()
            return None

        if _is_ngb(p):
            pend = self._pending.get(folder_key)
            if not pend or not pend.csv_path:
                # No CSV remembered yet → nothing to do
                self._purge_stale()
                return None

            # we have CSV + NGB: advertise synthetic path using <Probenname>
            advertised = Path(p.parent, f"{pend.probenname}{p.suffix}")
            # Stash bookkeeping under the real NGB path so processing can zip/move the correct source.
            self._finalizing[str(p)] = pend
            # clear pending for this folder so subsequent runs start fresh
            self._pending.pop(folder_key, None)
            logger.debug("PSA: NGB %s paired with CSV %s; advertising %s",
                         p, pend.csv_path, advertised.name)
            self._purge_stale()
            return str(advertised)

        # other files: ignore
        return None

    # -------------------------------
    # Probing (for CSVs only)
    # -------------------------------
    def probe_file(self, filepath: str) -> FileProbeResult:
        p = Path(filepath)
        if not _is_csv_like(p):
            return FileProbeResult.mismatch("Not a CSV/TSV for PSA Horiba")
        try:
            text = self._read_text_prefix(p)
        except Exception as exc:
            return FileProbeResult.unknown(str(exc))
        t = text.lower()
        score = sum(tok in t for tok in ["horiba", "partica", "la-960", "diameter"]) \
                - sum(tok in t for tok in ["dissolution", "cumulative release"])
        if score <= 0:
            return FileProbeResult.unknown("Content inconclusive for PSA Horiba")
        confidence = min(0.55 + 0.15 * score, 0.95)
        return FileProbeResult.match(confidence=confidence, reason=f"PSA markers (score={score})")

    def is_appendable(self, record: LocalRecord, filename_prefix: str, extension: str) -> bool:
        return True

    @classmethod
    def get_device_id(cls) -> str:
        return "psa_horiba_atomic"

    # -------------------------------
    # Processing
    # -------------------------------
    def device_specific_processing(
        self,
        src_path: str,
        record_path: str,
        filename_prefix: str,
        extension: str,
    ) -> ProcessingOutput:
        ngb_real = Path(src_path)
        pend = self._finalizing.pop(str(ngb_real), None)
        # Pairing must have been recorded during preprocessing; otherwise we cannot build the archive.
        if not pend or not pend.csv_path:
            raise RuntimeError("No pending CSV for this NGB; cannot finalize")

        record_dir = Path(record_path)
        record_dir.mkdir(parents=True, exist_ok=True)

        # ---- 1) CSV: convert TAB→';' and move with unique name based on prefix
        csv_src = pend.csv_path
        csv_dest = Path(get_unique_filename(record_path, filename_prefix, ".csv"))
        self._convert_tabs_to_semicolon(csv_src, csv_dest)
        logger.debug("PSA: CSV moved %s → %s", csv_src, csv_dest)

        # ---- 2) NGB: zip as <prefix>.zip (unique), entry named <prefix>.ngb
        zip_dest = Path(get_unique_filename(record_path, filename_prefix, ".zip"))
        arcname = f"{filename_prefix}.ngb"
        with zipfile.ZipFile(zip_dest, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.write(ngb_real, arcname=arcname)
        try:
            ngb_real.unlink(missing_ok=True)
        except Exception:
            pass
        logger.debug("PSA: NGB zipped %s → %s (arcname=%s)", ngb_real, zip_dest, arcname)

        return ProcessingOutput(final_path=str(record_dir), datatype="psa")

    # -------------------------------
    # Helpers
    # -------------------------------
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
        """Parse Horiba header until numeric table begins; accept TAB or ';'."""
        def _looks_like_table_header(token: str) -> bool:
            t = token.strip().strip('"')
            if re.match(r'^[xX]\([^)]*\)$', t):
                return True
            return bool(re.match(r'^[\s]*[0-9]*[.,]?[0-9]+([\sEe][+-]?[0-9]+)?\s*$', t))

        text = self._read_text_prefix(p, bytes_limit=_MAX_PREFIX_BYTES)
        if not text:
            return {}
        meta: Dict[str, str] = {}
        for line in text.splitlines():
            ls = line.strip()
            if not ls:
                continue
            parts = re.split(r"\t+|;", ls)
            if not parts:
                continue
            first = parts[0].strip().strip('"').strip("\ufeff")
            if _looks_like_table_header(first):
                break
            if len(parts) >= 2:
                k = first.lower()
                v = parts[1].strip().strip('"')
                if k and v:
                    meta[k] = v
        return meta

    def _purge_stale(self) -> None:
        now = time.time()
        ttl_seconds = getattr(getattr(self.device_config, "batch", None), "ttl_seconds", 600)
        # Drop CSVs that never received their NGB companion within the configured TTL.
        to_drop = []
        for k, pend in self._pending.items():
            if now - pend.t > ttl_seconds:
                to_drop.append(k)
        for k in to_drop:
            payload = self._pending.pop(k, None)
            if not payload:
                continue
            for p in [payload.csv_path]:
                if p and p.exists():
                    try:
                        move_to_exception_folder(str(p))
                        logger.info("PSA: purged stale CSV '%s'", p)
                    except Exception as exc:
                        logger.warning("PSA: could not purge stale '%s': %s", p, exc)

    def _convert_tabs_to_semicolon(self, src: Path, dest: Path) -> None:
        data = None
        for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            try:
                data = src.read_text(encoding=enc, errors="ignore")
                break
            except Exception:
                data = None
        if data is None:
            raise RuntimeError(f"Unable to read CSV: {src}")
        converted = data.replace("\t", _TARGET_DELIM)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(converted, encoding="utf-8")
        try:
            src.unlink(missing_ok=True)
        except Exception:
            pass
