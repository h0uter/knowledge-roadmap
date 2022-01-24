import matplotlib.pyplot as plt
import keyboard
from matplotlib import image
import os
import numpy as np
from skimage import draw
from PIL import Image

from knowledge_roadmap.entities.agent import Agent
from knowledge_roadmap.data_providers.manual_graph_world import *
from knowledge_roadmap.entrypoints.GUI import GUI
from knowledge_roadmap.usecases.exploration import Exploration
from knowledge_roadmap.data_providers.world_graph_generator import GraphGenerator
from knowledge_roadmap.data_providers.local_grid_adapter import LocalGridAdapter
from knowledge_roadmap.entities.frontier_sampler import FrontierSampler 


import matplotlib
matplotlib.use("Tkagg")

############################################################################################
# DEMONSTRATIONS
############################################################################################


def exploration_sampling(world, agent, exploration_use_case, gui, stepwise=False):
    '''
    The function runs the exploration use case until the agent has no more frontiers to explore. 
    
    The function visualizes the exploration process by showing the local grid, the agent's position, the
    KRM, and the frontiers. 
        
    :param world: the world object
    :param agent: the agent object
    :param exploration_use_case: the exploration use case to use. It is a class that implements the
    run_exploration_step method
    :param gui: the GUI object
    :param stepwise: If True, the exploration will be run stepwise. If False, the exploration will be
    run in a loop, defaults to False (optional)
    :return: None
    '''

    debug_container = {
        'world': world, 
        'agent': agent, 
        'exploration_use_case': exploration_use_case, 
        'gui': gui}

    local_grid_adapter = LocalGridAdapter(
        map_length_scales=(gui.x_offset, gui.y_offset),
        mode='spoof',
        size_pix=200, 
        cell_size=1, 
        debug_container=debug_container
        )

    sampler = FrontierSampler(local_grid_adapter.cell_size, local_grid_adapter.size_pix)

    while agent.no_more_frontiers == False:
        if not stepwise:
            local_grid_img = local_grid_adapter.get_local_grid()
            gui.draw_local_grid(local_grid_img)

            exploration_use_case.run_exploration_step(world)
            if gui.map_img is not None: 

                frontiers = sampler.sample_frontiers(
                    local_grid_img, 
                    local_grid_adapter.size_pix, 
                    radius=150, 
                    num_frontiers_to_sample=1, 
                    local_grid_adapter=local_grid_adapter
                    )
                for frontier in frontiers:
                    xx, yy = sampler.get_cells_under_line((local_grid_adapter.size_pix, local_grid_adapter.size_pix), frontier)
                    plt.plot(xx, yy) # draw the line as collection of pixels

                    x_local, y_local = frontier[0], frontier[1]
                    x_global = agent.pos[0] + (x_local - local_grid_adapter.size_pix) / 50
                    y_global = agent.pos[1] +  (y_local - local_grid_adapter.size_pix) /50
                    frontier_pos_global = (x_global, y_global)
                    # gui.ax1.plot(x_global, y_global, 'ro')
                    agent.krm.add_frontier(frontier_pos_global, agent.at_wp)


            gui.viz_krm(agent, agent.krm) # TODO: make the KRM independent of the agent
            gui.draw_agent(agent.pos)
            # TODO: put all drawing logic in one function
            # FIXME: fix agent.krm bullshit, KRM should be an entity which can be shared by multiple agents
            plt.pause(0.001)
        elif stepwise:
            # BUG:: matplotlib crashes after 10 sec if we block the execution like this.
            keypress = keyboard.read_key()
            if keypress:
                keypress = False
                exploration_use_case.run_exploration_step(world)

                gui.viz_krm(agent, agent.krm)
                gui.draw_agent(agent.pos)
                plt.pause(0.01)

    plt.ioff()
    plt.show()

def exploration_on_randomly_generated_graph_world():
    world = GraphGenerator(100,save_world_to_file=True)
    gui = GUI(map_img=None)
    gui.preview_graph_world(world)
    agent = Agent(debug=False)
    exploration_use_case = Exploration(agent, debug=False)
    exploration_on_graph(world, agent, exploration_use_case, gui)

def exploration_on_manual_graph_world():
    # full_path = os.path.join('resource', 'floor-plan-villa.png')
    full_path = os.path.join('resource', 'output-onlinepngtools.png')
    upside_down_map_img = image.imread(full_path)
    map_img = img_axes2world_axes(upside_down_map_img)

    world = ManualGraphWorld(map_img=map_img)
    gui = GUI(map_img=world.map_img)
    gui.preview_graph_world(world)
    agent = Agent(debug=False)
    exploration_use_case = Exploration(agent, debug=False)
    exploration_on_graph(world, agent, exploration_use_case, gui)

def graph_generator_debug():
    world = GraphGenerator(200)
    gui = GUI()
    gui.preview_graph_world(world)

def local_grid_sampler_test():
    EMPTY_CELL = 0
    OBSTACLE_CELL = 1
    FRONTIER_CELL = 2
    GOAL_CELL = 3
    MOVE_CELL = 4
    cell_size = 1
    num_cells = 15
    two_times_num_cells = int(num_cells*2)
    # x_prev, y_prev = num_cells, num_cells
    x_prev, y_prev = 5, 5

    empty_data = np.zeros((two_times_num_cells, two_times_num_cells))
    data = empty_data

    # add a boundary to the local grid
    rr, cc = draw.rectangle_perimeter((2,2), (two_times_num_cells-5, two_times_num_cells-5), shape=data.shape)
    data[rr,cc] = 1

    local_grid = FrontierSampler(cell_size, num_cells)
    local_grid.draw_grid(data)


    for i in range(10):
        x_sample, y_sample = local_grid.sample_point_around_other_point(x_prev, y_prev, radius=20, data=data)
        # print(f"Sampled point: {x_sample}, {y_sample}")
        # local_grid.draw_line(x_prev, y_prev, x_sample, y_sample)
        # x_prev, y_prev = x_sample, y_sample
        data[y_sample, x_sample] = FRONTIER_CELL

    plt.ioff()
    plt.plot(x_prev, y_prev, marker='s', color='red', linestyle='none')
    local_grid.draw_grid(data)


def exploration_with_sampling_viz(result_only):
    # this is the prior image of the villa we can include for visualization purposes
    # It is different from the map we use to emulate the local grid.
    # full_path = os.path.join('resource', 'output-onlinepngtools.png')
    full_path = os.path.join('resource', 'villa_holes_closed.png')
    upside_down_map_img = Image.open(full_path)
    print(upside_down_map_img.size)
    map_img = img_axes2world_axes(upside_down_map_img)
    world = ManualGraphWorld()
    gui = GUI(map_img=map_img)
    # gui.preview_graph_world(world)
    agent = Agent(debug=False)
    exploration_use_case = Exploration(agent, debug=False)

    debug_container = {
        'world': world, 
        'agent': agent, 
        'exploration_use_case': exploration_use_case, 
        'gui': gui}

    local_grid_adapter = LocalGridAdapter(
        map_length_scales=(gui.origin_x_offset, gui.origin_y_offset),
        mode='spoof',
        size_pix=200, 
        cell_size=1, 
        debug_container=debug_container
        )

    # sampler = FrontierSampler()

    while agent.no_more_frontiers == False:
        local_grid_img = local_grid_adapter.get_local_grid()
        gui.draw_local_grid(local_grid_img)

        exploration_use_case.run_exploration_step(world, agent, local_grid_img, local_grid_adapter)

        if not result_only:
            gui.viz_krm(agent, agent.krm) # TODO: make the KRM independent of the agent
            gui.draw_agent(agent.pos, )
            plt.pause(0.001)
    
    gui.viz_krm(agent, agent.krm) # TODO: make the KRM independent of the agent
    plt.ioff()
    plt.show()


if __name__ == '__main__':

    exploration_with_sampling_viz(False)
    # exploration_on_manual_graph_world()
    # exploration_on_randomly_generated_graph_world()
    # graph_generator_debug()
    # local_grid_sampler_test()
    