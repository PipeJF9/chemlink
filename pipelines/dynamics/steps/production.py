import os
from typing import List, Optional
from tqdm import tqdm

from ..logger import get_step_logger
from utils.retry import SubprocessError, run_subprocess

_GROMPP_TIMEOUT = 120


class ProductionStep:
    def __init__(self, config, gmx_bin):
        self.config      = config
        self.gmx_bin     = gmx_bin
        work             = self.config["work_dir"]
        self.npt_gro     = os.path.join(work, "npt.gro")
        self.npt_cpt     = os.path.join(work, "npt.cpt")
        self.topol       = os.path.join(work, "topol.top")
        self.md_mdp      = os.path.join(work, "md.mdp")
        self.md_tpr      = os.path.join(work, "md.tpr")
        self.output_base = "md"
        self.logger      = get_step_logger(
            __name__, os.path.join(work, "simulation.log")
        )

    def _create_production_mdp(self) -> None:
        ns_time = float(self.config["ns_time"])
        nsteps  = int((ns_time * 1000) / 0.002)
        with open(self.md_mdp, "w") as fh:
            fh.write(
                f"integrator           = md\n"
                f"nsteps               = {nsteps}\n"
                f"dt                   = 0.002\n"
                f"nstxout              = 0\n"
                f"nstvout              = 0\n"
                f"nstfout              = 0\n"
                f"nstenergy            = 5000\n"
                f"nstlog               = 5000\n"
                f"nstxout-compressed   = 5000\n"
                f"compressed-x-grps    = System\n"
                f"continuation         = yes\n"
                f"constraint_algorithm = lincs\n"
                f"constraints          = h-bonds\n"
                f"cutoff-scheme        = Verlet\n"
                f"ns_type              = grid\n"
                f"nstlist              = 10\n"
                f"rcoulomb             = 1.0\n"
                f"rvdw                 = 1.0\n"
                f"coulombtype          = PME\n"
                f"pme_order            = 4\n"
                f"fourierspacing       = 0.16\n"
                f"tcoupl               = V-rescale\n"
                f"tc-grps              = System\n"
                f"tau_t                = 0.1\n"
                f"ref_t                = 300\n"
                f"pcoupl               = Parrinello-Rahman\n"
                f"pcoupltype           = isotropic\n"
                f"tau_p                = 2.0\n"
                f"ref_p                = 1.0\n"
                f"compressibility      = 4.5e-5\n"
                f"pbc                  = xyz\n"
                f"gen_vel              = no\n"
            )

    def _gpu_fallback(self, mdrun_cpu: List[str]):
        """Return an on_retry callback that switches to CPU on the first retry."""
        def _callback(attempt: int, exc: Exception) -> Optional[List[str]]:
            if attempt == 1:
                self.logger.warning(
                    "GPU production run failed — retrying on CPU only."
                )
            return mdrun_cpu if attempt == 1 else None
        return _callback

    def run(self) -> None:
        self._create_production_mdp()

        grompp_cmd = [
            self.gmx_bin, "grompp",
            "-f", self.md_mdp,
            "-c", self.npt_gro,
            "-t", self.npt_cpt,
            "-p", self.topol,
            "-o", self.md_tpr,
            "-maxwarn", "10",
        ]

        threads    = str(self.config.get("threads", 8))
        use_gpu    = bool(self.config.get("gpu_ids"))
        mdrun_base = [
            self.gmx_bin, "mdrun", "-v",
            "-deffnm", self.output_base,
            "-ntomp", threads,
            "-pin", "on",
        ]
        mdrun_gpu = mdrun_base + ["-nb", "gpu", "-pme", "gpu", "-update", "gpu"]
        mdrun_cpu = mdrun_base

        with tqdm(total=2, desc="  └─ Production Dynamics", leave=False) as pbar:
            try:
                run_subprocess(
                    grompp_cmd,
                    timeout=_GROMPP_TIMEOUT,
                    retries=2,
                    logger=self.logger,
                )
                pbar.update(1)

                # No wall-clock timeout for production — duration is user-defined.
                # GPU fallback is still applied if CUDA initialisation fails.
                run_subprocess(
                    mdrun_gpu if use_gpu else mdrun_cpu,
                    timeout=None,
                    retries=2 if use_gpu else 1,
                    cwd=self.config["work_dir"],
                    logger=self.logger,
                    on_retry=self._gpu_fallback(mdrun_cpu) if use_gpu else None,
                )
                pbar.update(1)

            except SubprocessError as exc:
                self.logger.error("Production MD failed:\n%s", exc.stderr)
                raise RuntimeError(str(exc)) from exc
            except Exception:
                self.logger.exception("Unexpected error in ProductionStep")
                raise
