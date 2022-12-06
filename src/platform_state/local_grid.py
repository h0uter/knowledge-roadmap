import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import numpy.typing as npt
from skimage import draw

from src.config import Scenario, cfg


@dataclass
class FrontierSamplingViewModel:
    local_grid_img: npt.NDArray
    new_frontier_cells: list[tuple[int, int]]
    collision_cells: list[tuple[int, int]]


class LocalGrid:
    def __init__(self, xy: tuple[float, float], img_data: npt.NDArray):
        self._log = logging.getLogger(__name__)

        # Where the robot was when the lg image was obtained
        self.lg_xy = xy
        self.img_data = img_data  # r,c with origin top left (numpy convention)

        self.LG_LEN_IN_N_CELLS = int(cfg.LG_LEN_IN_M / cfg.LG_MTR_PER_CELL)
        self.PIXEL_OCCUPIED_THRESHOLD = 220

    def is_within_local_grid(self, coords: tuple[float, float]) -> bool:
        """
        Check if the world coordinates are within the local grid.
        """
        if (
            coords[0] < self.lg_xy[0] - cfg.LG_LEN_IN_M / 2
            or coords[0] > self.lg_xy[0] + cfg.LG_LEN_IN_M / 2
            or coords[1] < self.lg_xy[1] - cfg.LG_LEN_IN_M / 2
            or coords[1] > self.lg_xy[1] + cfg.LG_LEN_IN_M / 2
        ):
            return False
        return True

    def xy2rc(self, xy: tuple[float, float]) -> tuple[int, int]:
        """
        Convert the world coordinates to the cell indices of the local grid.
        Assumes that the world coordinate falls within the local grid.
        """

        if not self.is_within_local_grid(xy):
            raise ValueError(f"World coordinate {xy} is not within the local grid.")

        if cfg.SCENARIO == Scenario.REAL:
            c = int(
                (xy[0] - self.lg_xy[0]) / cfg.LG_MTR_PER_CELL
                + self.LG_LEN_IN_N_CELLS / 2
            )
            r = int(
                (xy[1] - self.lg_xy[1]) / cfg.LG_MTR_PER_CELL
                + self.LG_LEN_IN_N_CELLS / 2
            )

        else:
            c = int((xy[0] - self.lg_xy[0] + cfg.LG_LEN_IN_M / 2) / cfg.LG_MTR_PER_CELL)
            r = int(
                (-xy[1] + self.lg_xy[1] + cfg.LG_LEN_IN_M / 2) / cfg.LG_MTR_PER_CELL
            )

        return r, c

    def rc2xy(self, rc: tuple[int, int]) -> tuple[float, float]:
        """
        Convert the cell indices to the world coordinates.
        """
        if cfg.SCENARIO == Scenario.REAL:
            x = (
                self.lg_xy[0]
                + (rc[1] - self.LG_LEN_IN_N_CELLS / 2) * cfg.LG_MTR_PER_CELL
            )
            y = (
                self.lg_xy[1]
                + (rc[0] - self.LG_LEN_IN_N_CELLS / 2) * cfg.LG_MTR_PER_CELL
            )
        else:
            x = self.lg_xy[0] - cfg.LG_LEN_IN_M / 2 + rc[1] * cfg.LG_MTR_PER_CELL
            y = self.lg_xy[1] + cfg.LG_LEN_IN_M / 2 - rc[0] * cfg.LG_MTR_PER_CELL
        return x, y

    def is_collision_free_straight_line_between_cells(
        self, r0c0: tuple[int, int], r1c1: tuple[int, int]
    ) -> tuple[bool, Optional[tuple[float, float]]]:

        rr, cc = draw.line(int(r0c0[0]), int(r0c0[1]), int(r1c1[0]), int(r1c1[1]))

        for r, c in zip(rr, cc):
            if cfg.SCENARIO == Scenario.REAL:
                if np.greater(
                    self.img_data[r, c][0:2],
                    [self.PIXEL_OCCUPIED_THRESHOLD, self.PIXEL_OCCUPIED_THRESHOLD],
                ).any():
                    x, y = self.rc2xy((r, c))
                    collision_point = (x, y)

                    return False, collision_point

            if cfg.SCENARIO == Scenario.SIM_MAZE_MEDIUM:
                if np.greater(
                    self.img_data[r, c][3],
                    [self.PIXEL_OCCUPIED_THRESHOLD],
                ).any():
                    x, y = self.rc2xy((r, c))
                    collision_point = (x, y)

                    return False, collision_point

            else:
                if np.less(
                    self.img_data[r, c],
                    [
                        self.PIXEL_OCCUPIED_THRESHOLD,
                        self.PIXEL_OCCUPIED_THRESHOLD,
                        self.PIXEL_OCCUPIED_THRESHOLD,
                        self.PIXEL_OCCUPIED_THRESHOLD,
                    ],
                ).any():
                    x, y = self.rc2xy((r, c))
                    collision_point = (x, y)
                    return False, collision_point

        return True, None
