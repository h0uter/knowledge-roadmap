from copy import copy
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from skimage import draw

from knowledge_roadmap.entities.agent import Agent

EMPTY_CELL = 0
OBSTACLE_CELL = 1
FRONTIER_CELL = 2
GOAL_CELL = 3
MOVE_CELL = 4

class FrontierSampler():
    def __init__(self, debug_mode=False) -> None:
        self.init = False
        self.debug = debug_mode

    def get_cells_under_line(self, point_a, point_b):  
        # TODO: check if x and y is correct
        rr, cc = draw.line(int(point_a[0]), int(point_a[1]), int(point_b[0]), int(point_b[1]))

        return rr, cc

    def plot_collision(self, data, r, c, to, at, local_grid_adapter):
        plt.figure(9)
        x_meter, y_meter = local_grid_adapter.local_pix_idx2world_coord(data, c, r)

        plt.cla()
        plt.ion()
        plt.imshow(data, origin='lower')
        *at_meters, = local_grid_adapter.local_pix_idx2world_coord(data, at[1], at[0])
        *to_meters, = local_grid_adapter.local_pix_idx2world_coord(data, to[1], to[0])
        print(at_meters)
        plt.plot([at_meters[0], to_meters[0]], [at_meters[1], to_meters[1]], color='green')
        plt.plot(x_meter, y_meter, marker='s', color='red', markersize=10)
        plt.pause(0.001)
        plt.figure(1)

    # TODO: add robot size as parameter to the collision check.
    def collision_check(self, data, at, to, local_grid_adapter,debug=False):
        '''
        If the path goes through an obstacle, report collision.
        
        :param data: the occupancy grid
        :param at: the starting point of the line segment
        :param to: the goal location
        :param local_grid_adapter: a LocalGridAdapter object
        :return: A boolean value.
        '''
        rr, cc = self.get_cells_under_line(at, to)
        
        # for cell in path, if one of them is an obstacle, resample
        for r, c in zip(rr, cc):
            if np.less(data[r,c], [230, 230, 230, 230]).any():
                if debug:
                    print(f"Collision at {r}, {c}")
                    self.plot_collision(data, r, c, to, at, local_grid_adapter)

                return False  
        return True

    def sample_point_around_other_point(self, x, y, radius, data, local_grid_adapter):
        '''
        Given a point and a radius, sample a point in the circle around the point.
        
        :param x: the x coordinate of the point to sample around
        :param y: the y-coordinate of the point to sample around
        :param radius: The radius of the circle around the point to sample
        :param data: the data that we're sampling from
        :param local_grid_adapter: This is the local grid adapter that is used to check for collisions
        :return: The x and y coordinates of the sampled point.
        '''
        valid_sample = False

        while not valid_sample:
            r = radius * np.sqrt(np.random.uniform(low=0.6, high=1))
            theta = np.random.random() * 2 * np.pi

            x_sample = int(x + r * np.cos(theta))
            y_sample = int(y + r * np.sin(theta))

            valid_sample = self.collision_check(data=data, at=(x, y), to=(x_sample, y_sample), local_grid_adapter=local_grid_adapter)

        return x_sample, y_sample

    def sample_frontiers(self, local_grid, local_grid_adapter, radius=90, num_frontiers_to_sample=5) -> list:
        '''
        Given a local grid, sample N points around a given point, and return the sampled points.
        
        :param local_grid: the grid of the local map
        :param local_grid_adapter: the adapter for the local grid
        :param radius: the radius of the circle around the center point that we sample points from, defaults
        to 90 (optional)
        :param num_frontiers_to_sample: the number of frontiers to sample, defaults to 5 (optional)
        :return: A list of tuples, each tuple is a frontier point.
        '''
        candidate_frontiers = []
        grid_size = local_grid_adapter.size_pix
        while len(candidate_frontiers) < num_frontiers_to_sample:
            x_center = grid_size
            y_center = grid_size

            x_sample, y_sample = self.sample_point_around_other_point(x_center, y_center, radius=radius, data=local_grid, local_grid_adapter=local_grid_adapter)
            
            # BUG: why the hell is this y,x ....
            x_sample, y_sample = local_grid_adapter.local_pix_idx2world_coord(local_grid, y_sample, x_sample)
            
            candidate_frontiers.append((x_sample, y_sample))

        candidate_frontiers = np.array(candidate_frontiers).astype(np.int)
        
        return candidate_frontiers


    # def init_plot(self, data) -> None:
    #     fig = plt.figure()
    #     ax = fig.add_subplot(111)
    #     plt.ion()

    #     ax.grid(which='major', axis='both', linestyle='-', color='k', linewidth=1)
    #     ax.set_xticks(np.arange(0.5, data.shape[0], 1))
    #     ax.set_yticks(np.arange(0.5, data.shape[0], 1))
    #     plt.tick_params(axis='both', which='both', bottom=False,   
    #                 left=False, labelbottom=False, labelleft=False) 

    #     EMPTY_CELL = 0
    #     OBSTACLE_CELL = 1
    #     FRONTIER_CELL = 2
    #     GOAL_CELL = 3
    #     MOVE_CELL = 4

    #     self.cmap = colors.ListedColormap(['white', 'black', 'green', 'red', 'blue'])
    #     self.bounds = [EMPTY_CELL, OBSTACLE_CELL, FRONTIER_CELL, GOAL_CELL, MOVE_CELL, MOVE_CELL + 1]
    #     self.norm = colors.BoundaryNorm(self.bounds, self.cmap.N)
    #     # DONT fuck with extent it causes aliasing problems
    #     plt.imshow( 
    #         data, 
    #         cmap = self.cmap , 
    #         norm= self.norm,
    #         )

    #     plt.show()
    #     plt.pause(0.001)

    # def draw_grid(self, data) -> None:
    #     if not self.init:
    #         self.init_plot(data)
    #         self.init = True

    #     plt.imshow( 
    #         data, 
    #         cmap = self.cmap , 
    #         norm = self.norm,
    #         origin='lower',
    #         )
    #     plt.show()
    #     plt.pause(0.001)

    # def draw_line(self, x1, y1, x2, y2) -> None:
    #     plt.plot([x1, x2], [y1, y2], marker='s', color='blue')

