"""Concrete processor for V2 sem_phenomxl2 plugin."""

from __future__ import annotations

from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, Mapping

from dpost_v2.application.contracts.context import ProcessingContext
from dpost_v2.application.contracts.plugin_contracts import ProcessorResult
from dpost_v2.plugins.devices._device_template.processor import (
    DeviceProcessorFormatError,
    DeviceProcessorValidationError,
    TemplateDeviceProcessor,
)


class DeviceProcessor(TemplateDeviceProcessor):
    """SEM processor implementing parity-spec native-image and ELID behavior."""

    _ELID_EXTENSION = ".elid"
    _NATIVE_EXTENSIONS = frozenset({".tiff", ".tif", ".jpeg", ".jpg"})
    _DESCRIPTOR_EXTENSIONS = frozenset({".odt", ".elid"})

    def prepare(self, raw_input: Mapping[str, Any]) -> Mapping[str, Any]:
        """Normalize input and capture the routed filename expected by runtime."""
        prepared = dict(super().prepare(raw_input))
        source_path = str(prepared["source_path"]).strip()
        source = self._pure_path(source_path)
        normalized_stem = self._strip_trailing_digit(source.stem)
        prepared["normalized_stem"] = normalized_stem
        prepared["output_name"] = f"{normalized_stem}{source.suffix}"
        return prepared

    def process(
        self,
        prepared_input: Mapping[str, Any],
        context: ProcessingContext,
    ) -> ProcessorResult:
        """Return SEM-native image or ELID artifact metadata for routing."""
        _ = context
        source_path = str(prepared_input.get("source_path", "")).strip()
        if not source_path:
            raise DeviceProcessorValidationError("prepared source_path is required")

        source = self._pure_path(source_path)
        extension = self._extension_token(prepared_input, source)

        if extension in self._NATIVE_EXTENSIONS:
            return ProcessorResult(
                final_path=self._native_output_path(
                    source,
                    output_name=str(
                        prepared_input.get("output_name", source.name)
                    ).strip(),
                ),
                datatype="img",
            )

        if extension == self._ELID_EXTENSION:
            return self._build_elid_result(source_path, source)

        raise DeviceProcessorFormatError(
            f"unsupported extension {extension!r} for {self.settings.plugin_id}"
        )

    @staticmethod
    def _strip_trailing_digit(filename: str) -> str:
        """Mirror legacy behavior: strip only one trailing digit when present."""
        if filename and filename[-1].isdigit():
            return filename[:-1]
        return filename

    def _build_elid_result(
        self,
        source_path: str,
        source: PurePath,
    ) -> ProcessorResult:
        """Describe ELID ZIP and descriptor artifacts from the source directory."""
        source_dir = Path(source_path)
        if not source_dir.exists() or not source_dir.is_dir():
            raise DeviceProcessorValidationError(
                "sem_phenomxl2 .elid processing requires a directory source_path"
            )

        base = source.stem
        target_parent = source.parent
        descriptor_paths = tuple(
            self._normalize_output_path(target_parent / f"{base}{descriptor.suffix}")
            for descriptor in sorted(
                source_dir.iterdir(),
                key=lambda item: item.name.lower(),
            )
            if descriptor.is_file()
            and descriptor.suffix.lower() in self._DESCRIPTOR_EXTENSIONS
        )
        return ProcessorResult(
            final_path=self._normalize_output_path(target_parent / f"{base}.zip"),
            datatype="elid",
            force_paths=descriptor_paths,
        )

    def _native_output_path(self, source: PurePath, *, output_name: str) -> str:
        return self._normalize_output_path(source.with_name(output_name))

    @staticmethod
    def _extension_token(prepared_input: Mapping[str, Any], source: PurePath) -> str:
        extension = str(prepared_input.get("extension", "")).strip().lower()
        if extension:
            return extension
        return source.suffix.lower()

    @staticmethod
    def _pure_path(value: str) -> PurePath:
        if "\\" in value or (len(value) >= 2 and value[1] == ":"):
            return PureWindowsPath(value)
        return PurePosixPath(value)

    @staticmethod
    def _normalize_output_path(path: PurePath) -> str:
        return path.as_posix()
