import matplotlib.pyplot as plt
import numpy as np
from src.entities.knowledge_road_map import KnowledgeRoadmap
import networkx as nx


class Agent():
    ''' 
    Agent only here to test the KRM framework im developping.
    Feature wise it should match the out of the box capabilities of Spot.
    If its not in the spot services, it should not be here.
    '''

    def __init__(self, debug=False):
        self.debug = debug
        self.at_wp = 0
        self.pos = (0, 0)
        self.previous_pos = self.pos
        self.agent_drawing = None
        self.local_grid_drawing = None
        self.krm = KnowledgeRoadmap()
        self.no_more_frontiers = False
        self.steps_taken = 0

    def debug_logger(self):
        print("==============================")
        print(">>> " + nx.info(self.krm.KRM))
        print(f">>> self.at_wp: {self.at_wp}")
        print(f">>> movement: {self.previous_pos} >>>>>> {self.pos}")
        print(f">>> frontiers: {self.krm.get_all_frontiers_idxs()}")
        print("==============================")

    def teleport_to_pos(self, pos):
        # TODO: add a check to see if the position is within the navigation radius.
        self.previous_pos = self.pos
        self.pos = pos
        self.steps_taken += 1

    def sample_frontiers(self, world):
        ''' sample new frontier positions from local_grid '''
        agent_at_world_node = world.get_node_by_pos(self.pos)
        # indexing the graph like this returns the neigbors
        observable_nodes = world.graph[agent_at_world_node]

        # so this is godmode dictionary with pos info of all nodes
        world_node_pos_dict = nx.get_node_attributes(world.graph, 'pos')

        for node in observable_nodes:
            obs_pos = world_node_pos_dict[node]
            # dict with all the pos of nodes already in krm
            krm_node_pos_dict = nx.get_node_attributes(self.krm.KRM, 'pos')

            # check if the there is not already a node in my KRM with the same position as the observable node
            if obs_pos not in krm_node_pos_dict.values():
                frontier_pos = obs_pos

                # if there is no node at that pos in the KRM, add it
                self.krm.add_frontier(frontier_pos, self.at_wp)

    #############################################################################################
    ### ENTRYPOINT FOR GUIDING EXPLORATION WITH SEMANTICS ###
    #############################################################################################
    def evaluate_frontiers(self, frontier_idxs):
        ''' 
        Evaluate the frontiers and return the best one.
        this is the entrypoint for exploiting semantics        
        '''
        shortest_path_by_node_count = float('inf')
        selected_frontier_idx = None

        for frontier_idx in frontier_idxs:
            candidate_path = nx.shortest_path(
                self.krm.KRM, source=self.at_wp, target=frontier_idx)
            # choose the last shortest path among equals
            # if len(candidate_path) <= shortest_path_by_node_count:
            #  choose the first shortest path among equals
            if len(candidate_path) < shortest_path_by_node_count:
                shortest_path_by_node_count = len(candidate_path)
                selected_frontier_idx = candidate_path[-1]

        return selected_frontier_idx
    #############################################################################################

    def select_target_frontier(self):
        ''' using the KRM, obtain the optimal frontier to visit next'''
        frontier_idxs = self.krm.get_all_frontiers_idxs()
        if len(frontier_idxs) > 0:
            target_frontier = self.evaluate_frontiers(frontier_idxs)

            return target_frontier
        else:
            self.no_more_frontiers = True
            return None, None

    def find_path_to_selected_frontier(self, target_frontier):
        path = nx.shortest_path(
            self.krm.KRM, source=self.at_wp, target=target_frontier)
        return path

    def sample_waypoint(self):
        '''
        Sample a new waypoint at current agent pos, and add an edge connecting it to prev wp.
        this should be sampled from the pose graph eventually
        '''
        wp_at_previous_pos = self.krm.get_node_by_pos(self.previous_pos)
        # TODO: add a check if the proposed new wp is not already in the KRM
        self.krm.add_waypoint(self.pos, wp_at_previous_pos)
        self.at_wp = self.krm.get_node_by_pos(self.pos)

    def perform_path_step(self, path):
        '''
        Execute a single step of the path.
        '''
        if self.debug:
            print(f"the path {path} length is {len(path)}")
        if len(path) > 1:
            node_data = self.krm.get_node_data_by_idx(path[0])
            self.teleport_to_pos(node_data['pos'])
            path.pop(0)
            return path

        elif len(path) == 1:
            selected_frontier_data = self.krm.get_node_data_by_idx(
                path[0])
            self.teleport_to_pos(selected_frontier_data['pos'])
            if self.debug:
                print(f"SELECTED FRONTIER POS {selected_frontier_data['pos']}")
            return None

    def check_for_shortcuts(self, world):
        agent_at_world_node = world.get_node_by_pos(self.pos)
        observable_nodes = world.graph[agent_at_world_node]

        for world_node in observable_nodes:
            # convert observable world node to krm node
            krm_node = self.krm.get_node_by_pos(world.graph.nodes[world_node]['pos'])

            if not self.krm.KRM.has_edge(krm_node, self.at_wp):
                if krm_node != self.at_wp and krm_node: # prevent self loops and None errors
                    if self.debug: 
                        print("shortcut found")
                    # add the correct type of edge
                    if self.krm.KRM.nodes[krm_node]["type"] == "frontier":
                        self.krm.KRM.add_edge(self.at_wp, krm_node, type="frontier_edge")
                    else:
                        self.krm.KRM.add_edge(self.at_wp, krm_node, type="waypoint_edge")

    # HACK: perception processing should be more eleborate and perhaps be its own separate entity
    def process_world_object_perception(self, world):
        agent_at_world_node = world.get_node_by_pos(self.pos)
        if "world_object_dummy" in world.graph.nodes[agent_at_world_node].keys():
            world_object = world.graph.nodes[agent_at_world_node]["world_object_dummy"]
            if self.debug:
                print(f"world object '{world_object}' found")
            wo_pos = world.graph.nodes[agent_at_world_node]["world_object_pos_dummy"]
            self.krm.add_world_object(wo_pos, world_object)

    def world_coord2pix_idx(self, world, x_pos, y_pos):
        '''converts world coordinates to image pixel indices'''

        Nx_pix = world.map_img.shape[1]
        Ny_pix = world.map_img.shape[0]
        # print(f"nx_pix: {Nx_pix}, ny_pix: {Ny_pix}")

        # FIXME: this has to be linked to the x and y offset in the gui
        x_map_length_scale = 50
        y_map_length_scale = 40

        x_pix_per_meter = Nx_pix // x_map_length_scale
        y_pix_per_meter = Ny_pix // y_map_length_scale

        x_origin_pix_offset = Nx_pix // 2
        y_origin_pix_offset = Ny_pix // 2

        x_pix = x_pos * x_pix_per_meter - x_origin_pix_offset
        y_pix = y_pos * y_pix_per_meter - y_origin_pix_offset

        return x_pix, y_pix

    def observe_local_grid(self, size, world):
        '''crops the image around pos with size'''
        x, y = self.pos # world coords
        x, y = self.world_coord2pix_idx(world, x,y)

        # BUG:: cannot sample near edge of the image world.
        local_grid = world.map_img[int(y-size):int(y+size), int(x-size):int(x+size)]
        # print(f"local grid size: {local_grid.shape}")
        return local_grid

    # def pix_coord2world_coord(self, x_pix, y_pix):
    #     '''converts image coordinates to world coordinates'''
    #     x_pix = x * (self.map_img.shape[1] // 20)
    #     y_pix = x * (self.map_img.shape[0] // 20)
    #     x_offset = self.map_img.shape[1] // 2
    #     y_offset = self.map_img.shape[0] // 2
    #     x = x_pix + x_offset
    #     y = y_pix + y_offset
    #     return x, y

