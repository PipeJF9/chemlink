"""Adapter for AutoGrid4 command-line execution."""

import os
import shutil
import subprocess
from typing import Optional


class AutoGridAdapter:
	"""Wrapper around AutoGrid4 binary invocation."""

	DEFAULT_EXECUTABLE = os.environ.get("AUTOGRID4_BIN", "/usr/local/bin/autogrid4")
	DEFAULT_FALLBACKS = (
		os.environ.get("AUTOGRID4_BIN", "/usr/local/bin/autogrid4"),
		"/nfs/chemlink/software/autogrid4/bin/autogrid4",
		"/usr/local/bin/autogrid4",
		"/usr/local/bin/autogrid",
	)

	def __init__(self, executable: Optional[str] = None):
		self.executable = executable or self.DEFAULT_EXECUTABLE
		self.executable = self._resolve_executable(self.executable, self.DEFAULT_FALLBACKS)

	@staticmethod
	def _resolve_executable(executable: str, fallbacks: tuple[str, ...] = ()) -> str:
		"""Resolve executable from explicit path, PATH, or fallback locations."""
		if os.path.isabs(executable) and os.path.isfile(executable):
			return executable

		resolved = shutil.which(executable)
		if resolved:
			return resolved

		for candidate in fallbacks:
			if os.path.isfile(candidate):
				return candidate

		return executable

	def validate(self) -> None:
		"""Ensure AutoGrid4 exists and is executable."""
		if not os.path.isfile(self.executable):
			raise FileNotFoundError(f"AutoGrid4 not found: {self.executable}")
		if not os.access(self.executable, os.X_OK):
			raise RuntimeError(f"AutoGrid4 is not executable: {self.executable}")

	def generate_maps(self, gpf_file: str, timeout_seconds: int = 300) -> str:
		"""Generate .maps.fld files from a GPF file and return the output map path."""
		workdir = os.path.dirname(gpf_file)
		gpf_name = os.path.basename(gpf_file)
		base_name = os.path.splitext(gpf_name)[0]
		glg_file = f"{base_name}.glg"
		map_file = os.path.join(workdir, f"{base_name}.maps.fld")

		result = subprocess.run(
			[self.executable, "-p", gpf_name, "-l", glg_file],
			capture_output=True,
			text=True,
			cwd=workdir,
			timeout=timeout_seconds,
		)

		if result.returncode != 0:
			raise RuntimeError(f"AutoGrid failed for {gpf_name}: {result.stderr.strip()}")
		if not os.path.isfile(map_file):
			raise RuntimeError(f"AutoGrid finished but map file not found: {map_file}")

		return map_file