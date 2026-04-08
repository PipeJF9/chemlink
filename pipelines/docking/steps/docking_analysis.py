"""Docking analysis step for molecular docking."""

import csv
import glob
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ....storage.file_manager import create_folder
from ....utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass(frozen=True)
class DockingResult:
	"""Normalized docking result extracted from one DLG file."""

	protein: str
	ligand: str
	affinity: Optional[float]
	run: Optional[int]
	rmsd: Optional[float]
	dlg_file: str


class DockingAnalysis:
	"""Analyze AutoDock outputs and generate summary reports."""

	def __init__(self, output_path: str):
		self.output_path = output_path
		self.results_dir = os.path.join(self.output_path, "ResultadosDocking")
		self.analysis_dir = os.path.join(self.output_path, "AnalisisDocking")
		self.summary_txt = os.path.join(self.analysis_dir, "resumen_analisis.txt")
		self.summary_csv = os.path.join(self.analysis_dir, "resumen_analisis.csv")
		self.summary_md = os.path.join(self.analysis_dir, "resumen_analisis.md")

	@staticmethod
	def _parse_float(value: str) -> Optional[float]:
		try:
			return float(value)
		except (TypeError, ValueError):
			return None

	@staticmethod
	def _parse_int(value: str) -> Optional[int]:
		try:
			return int(value)
		except (TypeError, ValueError):
			return None

	def _parse_dlg(self, dlg_path: str) -> DockingResult:
		"""Parse the best affinity from a DLG file."""
		protein = Path(dlg_path).parent.parent.name
		base = Path(dlg_path).stem
		ligand = base.replace(f"{protein}_", "", 1)

		affinity = None
		run = None
		rmsd = None

		with open(dlg_path, "r", encoding="utf-8", errors="ignore") as handle:
			for line in handle:
				match = re.search(r"^\s*(\d+)\s+[-+]?[0-9]*\.?[0-9]+\s+[-+]?[0-9]*\.?[0-9]+\s+([-+]?[0-9]*\.?[0-9]+)\s+([-+]?[0-9]*\.?[0-9]+)", line)
				if match:
					run = self._parse_int(match.group(1))
					affinity = self._parse_float(match.group(2))
					rmsd = self._parse_float(match.group(3))
					break

		return DockingResult(
			protein=protein,
			ligand=ligand,
			affinity=affinity,
			run=run,
			rmsd=rmsd,
			dlg_file=dlg_path,
		)

	def _collect_results(self) -> List[DockingResult]:
		"""Collect every DLG file from the docking results tree."""
		results: List[DockingResult] = []
		for dlg_path in glob.glob(os.path.join(self.results_dir, "*", "dlg", "*.dlg")):
			try:
				results.append(self._parse_dlg(dlg_path))
			except Exception as exc:
				logger.warning("Could not parse %s: %s", dlg_path, exc)
		return results

	def _best_results(self, results: Iterable[DockingResult]) -> List[DockingResult]:
		"""Pick the best affinity per protein/ligand pair."""
		best: Dict[tuple, DockingResult] = {}
		for result in results:
			key = (result.protein, result.ligand)
			if result.affinity is None:
				continue
			current = best.get(key)
			if current is None or (current.affinity is not None and result.affinity < current.affinity):
				best[key] = result
		return sorted(best.values(), key=lambda item: (item.protein, item.affinity if item.affinity is not None else float("inf")))

	def _write_text_summary(self, results: List[DockingResult]) -> None:
		"""Write a human-readable summary."""
		with open(self.summary_txt, "w", encoding="utf-8") as handle:
			handle.write("DOCKING ANALYSIS SUMMARY\n")
			handle.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n")
			handle.write("=" * 72 + "\n\n")
			for result in results:
				handle.write(f"Protein: {result.protein}\n")
				handle.write(f"Ligand: {result.ligand}\n")
				handle.write(f"Affinity: {result.affinity if result.affinity is not None else 'N/A'}\n")
				handle.write(f"Run: {result.run if result.run is not None else 'N/A'}\n")
				handle.write(f"RMSD: {result.rmsd if result.rmsd is not None else 'N/A'}\n")
				handle.write(f"DLG: {result.dlg_file}\n")
				handle.write("-" * 72 + "\n")

	def _write_csv_summary(self, results: List[DockingResult]) -> None:
		"""Write a CSV summary for downstream analysis."""
		with open(self.summary_csv, "w", newline="", encoding="utf-8") as handle:
			writer = csv.DictWriter(
				handle,
				fieldnames=["protein", "ligand", "affinity", "run", "rmsd", "dlg_file"],
			)
			writer.writeheader()
			for result in results:
				writer.writerow(
					{
						"protein": result.protein,
						"ligand": result.ligand,
						"affinity": result.affinity,
						"run": result.run,
						"rmsd": result.rmsd,
						"dlg_file": result.dlg_file,
					}
				)

	def _write_markdown_summary(self, results: List[DockingResult]) -> None:
		"""Write a markdown report for quick inspection."""
		with open(self.summary_md, "w", encoding="utf-8") as handle:
			handle.write("# Docking Analysis Summary\n\n")
			handle.write(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}\n\n")
			handle.write("| Protein | Ligand | Affinity | Run | RMSD | DLG |\n")
			handle.write("|---|---|---:|---:|---:|---|\n")
			for result in results:
				handle.write(
					f"| {result.protein} | {result.ligand} | {result.affinity if result.affinity is not None else 'N/A'} | "
					f"{result.run if result.run is not None else 'N/A'} | {result.rmsd if result.rmsd is not None else 'N/A'} | "
					f"{result.dlg_file} |\n"
				)

	def run(self) -> Dict[str, int]:
		"""Execute docking analysis and create summary reports."""
		logger.info("Starting docking analysis")
		create_folder(self.analysis_dir)
		results = self._collect_results()
		if not results:
			logger.warning("No DLG files found for analysis in %s", self.results_dir)
		best_results = self._best_results(results)

		self._write_text_summary(best_results)
		self._write_csv_summary(best_results)
		self._write_markdown_summary(best_results)
		logger.info(
			"Docking analysis completed: parsed=%d, summarized=%d, outputs=%s",
			len(results),
			len(best_results),
			self.analysis_dir,
		)

		return {
			"parsed": len(results),
			"summarized": len(best_results),
		}
