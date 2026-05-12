import os
from typing import List, Optional
from tqdm import tqdm

from ..logger import get_step_logger
from utils.retry import SubprocessError, run_subprocess

# Each equilibration phase is 50 000 steps × 0.002 ps = 100 ps
_GROMPP_TIMEOUT = 120
_MDRUN_TIMEOUT  = 7200   # 2 h per phase


class EquilibrationStep:
    def __init__(self, config, gmx_bin):
        self.config   = config
        self.gmx_bin  = gmx_bin
        work          = self.config["work_dir"]
        self.em_gro   = os.path.join(work, "em.gro")
        self.topol    = os.path.join(work, "topol.top")
        self.nvt_mdp  = os.path.join(work, "nvt.mdp")
        self.nvt_tpr  = os.path.join(work, "nvt.tpr")
        self.nvt_gro  = os.path.join(work, "nvt.gro")
        self.nvt_cpt  = os.path.join(work, "nvt.cpt")
        self.npt_mdp  = os.path.join(work, "npt.mdp")
        self.npt_tpr  = os.path.join(work, "npt.tpr")
        self.npt_gro  = os.path.join(work, "npt.gro")
        self.logger   = get_step_logger(
            __name__, os.path.join(work, "simulation.log")
        )

    def _create_nvt_mdp(self) -> None:
        with open(self.nvt_mdp, "w") as fh:
            fh.write(
                "integrator           = md\n"
                "nsteps               = 50000\n"
                "dt                   = 0.002\n"
                "nstxout              = 5000\n"
                "nstvout              = 5000\n"
                "nstenergy            = 5000\n"
                "nstlog               = 5000\n"
                "continuation         = no\n"
                "constraint_algorithm = lincs\n"
                "constraints          = h-bonds\n"
                "cutoff-scheme        = Verlet\n"
                "ns_type              = grid\n"
                "nstlist              = 10\n"
                "rcoulomb             = 1.0\n"
                "rvdw                 = 1.0\n"
                "coulombtype          = PME\n"
                "pme_order            = 4\n"
                "fourierspacing       = 0.16\n"
                "tcoupl               = V-rescale\n"
                "tc-grps              = System\n"
                "tau_t                = 0.1\n"
                "ref_t                = 300\n"
                "pcoupl               = no\n"
                "pbc                  = xyz\n"
                "gen_vel              = yes\n"
                "gen_temp             = 300\n"
                "gen_seed             = -1\n"
            )

    def _create_npt_mdp(self) -> None:
        with open(self.npt_mdp, "w") as fh:
            fh.write(
                "integrator           = md\n"
                "nsteps               = 50000\n"
                "dt                   = 0.002\n"
                "nstxout              = 5000\n"
                "nstvout              = 5000\n"
                "nstenergy            = 5000\n"
                "nstlog               = 5000\n"
                "continuation         = yes\n"
                "constraint_algorithm = lincs\n"
                "constraints          = h-bonds\n"
                "cutoff-scheme        = Verlet\n"
                "ns_type              = grid\n"
                "nstlist              = 10\n"
                "rcoulomb             = 1.0\n"
                "rvdw                 = 1.0\n"
                "coulombtype          = PME\n"
                "pme_order            = 4\n"
                "fourierspacing       = 0.16\n"
                "tcoupl               = V-rescale\n"
                "tc-grps              = System\n"
                "tau_t                = 0.1\n"
                "ref_t                = 300\n"
                "pcoupl               = Parrinello-Rahman\n"
                "pcoupltype           = isotropic\n"
                "tau_p                = 2.0\n"
                "ref_p                = 1.0\n"
                "compressibility      = 4.5e-5\n"
                "refcoord_scaling     = com\n"
                "pbc                  = xyz\n"
                "gen_vel              = no\n"
            )

    def _gpu_fallback(self, mdrun_cpu: List[str]):
        """Return an on_retry callback that switches to CPU on the first retry."""
        def _callback(attempt: int, exc: Exception) -> Optional[List[str]]:
            if attempt == 1:
                self.logger.warning(
                    "GPU equilibration failed — retrying on CPU only."
                )
            return mdrun_cpu if attempt == 1 else None
        return _callback

    def _mdrun(self, deffnm: str, mdrun_gpu: List[str], mdrun_cpu: List[str]) -> None:
        use_gpu = bool(self.config.get("gpu_ids"))
        run_subprocess(
            mdrun_gpu if use_gpu else mdrun_cpu,
            timeout=_MDRUN_TIMEOUT,
            retries=2 if use_gpu else 1,
            cwd=self.config["work_dir"],
            logger=self.logger,
            on_retry=self._gpu_fallback(mdrun_cpu) if use_gpu else None,
        )

    def run(self) -> None:
        threads = str(self.config.get("threads", 8))

        with tqdm(total=4, desc="  └─ System Equilibration", leave=False) as pbar:
            try:
                # ── NVT ───────────────────────────────────────────────────────
                self._create_nvt_mdp()
                run_subprocess(
                    [
                        self.gmx_bin, "grompp",
                        "-f", self.nvt_mdp,
                        "-c", self.em_gro,
                        "-r", self.em_gro,
                        "-p", self.topol,
                        "-o", self.nvt_tpr,
                        "-maxwarn", "10",
                    ],
                    timeout=_GROMPP_TIMEOUT,
                    retries=2,
                    logger=self.logger,
                )
                pbar.update(1)

                base_nvt = [
                    self.gmx_bin, "mdrun", "-v",
                    "-deffnm", "nvt",
                    "-ntomp", threads, "-pin", "on",
                ]
                self._mdrun(
                    "nvt",
                    mdrun_gpu=base_nvt + ["-nb", "gpu", "-pme", "gpu", "-update", "gpu"],
                    mdrun_cpu=base_nvt,
                )
                pbar.update(1)

                # ── NPT ───────────────────────────────────────────────────────
                self._create_npt_mdp()
                run_subprocess(
                    [
                        self.gmx_bin, "grompp",
                        "-f", self.npt_mdp,
                        "-c", self.nvt_gro,
                        "-r", self.nvt_gro,
                        "-t", self.nvt_cpt,
                        "-p", self.topol,
                        "-o", self.npt_tpr,
                        "-maxwarn", "10",
                    ],
                    timeout=_GROMPP_TIMEOUT,
                    retries=2,
                    logger=self.logger,
                )
                pbar.update(1)

                base_npt = [
                    self.gmx_bin, "mdrun", "-v",
                    "-deffnm", "npt",
                    "-ntomp", threads, "-pin", "on",
                ]
                self._mdrun(
                    "npt",
                    mdrun_gpu=base_npt + ["-nb", "gpu", "-pme", "gpu", "-update", "gpu"],
                    mdrun_cpu=base_npt,
                )
                pbar.update(1)

                if not os.path.exists(self.npt_gro):
                    raise FileNotFoundError(
                        "Equilibration finished but output file was not found."
                    )

            except SubprocessError as exc:
                self.logger.error("Equilibration failed:\n%s", exc.stderr)
                raise RuntimeError(str(exc)) from exc
            except Exception:
                self.logger.exception("Unexpected error in EquilibrationStep")
                raise
