import matplotlib.pyplot as plt
import numpy as np
from numpy.core.numeric import Inf, Infinity
from knowledge_road_map import KnowledgeRoadmap
import networkx as nx
import keyboard

class Agent():
    ''' 
    Agent only here to test the KRM framework im developping.
    Feature wise it should match the out of the box capabilities of Spot.
    '''
    def __init__(self):
        self.at_wp = 0
        self.pos = (0, 0)
        self.previous_pos = self.pos
        self.agent_drawing = None
        self.krm = KnowledgeRoadmap()
        self.no_more_frontiers = False

    def debug_logger(self):
        print("==============================")
        print(">>> " + nx.info(self.krm.KRM))
        print(f">>> self.at_wp: {self.at_wp}")
        print(f">>> movement: {self.previous_pos} >>>>>> {self.pos}")
        print(f">>> frontiers: {self.krm.get_all_frontiers()}")
        print("==============================")

    def draw_agent(self, wp):
        ''' draw the agent on the world '''
        if self.agent_drawing != None:
            self.agent_drawing.remove()
        # self.agent_drawing = plt.arrow(
        #     wp[0], wp[1], 0.3, 0.3, width=0.4, color='blue')
        self.agent_drawing = plt.gca().add_patch(plt.Circle(
            (wp[0], wp[1]), 1, fc='blue'))
        # plt.draw()

    def teleport_to_pos(self, pos):
        self.previous_pos = self.pos
        self.pos = pos

    # TODO:: write a test for the sample frontiers function with a networkx demo graph
    def sample_frontiers(self, world):
        ''' sample new frontiers from local_grid '''
        agent_at_world_node = world.get_node_by_pos(self.pos)
        observable_nodes = world.world[agent_at_world_node] # indexing the graph like this returns the neigbors
        world_node_pos_dict = nx.get_node_attributes(world.world, 'pos')

        for node in observable_nodes:
            obs_pos = world_node_pos_dict[node]
            krm_node_pos_dict = nx.get_node_attributes(self.krm.KRM, 'pos')
            # check if the there is already a node in my KRM with the same position as the observable node
            if obs_pos not in krm_node_pos_dict.values():
                # frontier_pos = world.world._node[node]['pos']
                frontier_pos = obs_pos
                self.krm.add_frontier(frontier_pos, self.at_wp)

    # FIXME: this function needs to be made more explicit
    def select_target_frontier(self):
        ''' using the KRM, obtain the optimal frontier to visit next'''
        frontiers = self.krm.get_all_frontiers()
        if len(frontiers) > 0:
            ###############################################################################################################
            # TODO:: this is where the interesting logic comes in.
            ###############################################################################################################
            shortest_path_len = float('inf')
            selected_frontier = None
            self.selected_path = None

            # HACK: this whole logic is a hack ans should be refactored. 
            for frontier in frontiers:
                # print(f"frontier: {frontier}")
                targ = self.krm.get_node_by_UUID(frontier['id'])
                ans = nx.shortest_path(self.krm.KRM, source=self.at_wp, target=targ)
                print(f"shortest path: {ans}")
                if len(ans) < shortest_path_len:
                    shortest_path_len = len(ans)
                    selected_frontier = ans[-1] # just take the last one if there are multiple
                    self.selected_path = ans
                    ans.pop() # pop the last element, cause its a frontier
                
            target_frontier = self.krm.get_node_by_idx(selected_frontier)
            return target_frontier
        else:
            self.no_more_frontiers = True
            return 

    def goto_target_frontier(self):
        '''perform the move actions to reach the target frontier'''
        for node_idx in self.selected_path:
            node = self.krm.get_node_by_idx(node_idx)
            self.teleport_to_pos(node['pos'])
            self.draw_agent(node['pos'])
            plt.show()
            plt.pause(0.05)
            # self.debug_logger()

    def sample_waypoint(self):
        '''
        sample a new waypoint from the pose graph of the agent and remove the current frontier.
        '''
        wp_at_previous_pos = self.krm.get_node_by_pos(self.previous_pos)
        # TODO: add a check if the proposed new wp is not already in the KRM
        self.krm.add_waypoint(self.pos, wp_at_previous_pos)
        self.at_wp = self.krm.get_node_by_pos(self.pos)

    # HACK:: the whole logic of this function is one big hack
    def explore_algo(self, world):
        '''the logic powering exploration'''

        self.sample_frontiers(world)  # sample frontiers from the world
 
        '''illustrate the KRM'''
        self.krm.draw_current_krm()  # illustrate krm with new frontiers
        self.draw_agent(self.pos)  # draw the agent on the world
        plt.pause(0.3)

        '''select the target frontier and if there are no more frontiers remaining, we are done'''
        selected_frontier = self.select_target_frontier()  # select a frontier to visit
        #  this should be handled in select_target_frontier()
        if self.no_more_frontiers == True:  # if there are no more frontiers, we are done
            print("!!!!!!!!!!! EXPLORATION COMPLETED !!!!!!!!!!!")
            return

        # TODO:: hide this logic to obtain the index of the frontier somewhere appropriate
        # so apparently we dont want the frontier itself, we want its idx
        # so the function above should return this idx instead of the object
        selected_frontier_idx = self.krm.get_node_by_UUID(
            selected_frontier["id"])         # obtain the idx from the frontier object using its id

        # SO Apparently we need to check if we are at the cloostest wp to the selected frontier.
        # prob got to do with Y sections?
        # a frontier only has 1 wp as neighbor, so we ask for that neigbor
        closest_wp_to_selected_frontier_idx = list(
            nx.neighbors(self.krm.KRM, selected_frontier_idx))[0]
        closest_wp_to_selected_frontier = self.krm.get_node_by_idx(
            closest_wp_to_selected_frontier_idx)
        '''if the pos of the closest wp to our frontier is not our agent pos, we need to move to it'''
        if closest_wp_to_selected_frontier['pos'] != self.pos:
            self.goto_target_frontier()

        '''after reaching the wp next to the selected frontier, move to the selected frontier'''
        # TODO: remove this teleport code
        self.teleport_to_pos(selected_frontier['pos'])

        '''now we have visited the frontier we can remove it from the KRM and sample a waypoint in its place'''
        self.krm.remove_frontier(selected_frontier)
        self.sample_waypoint()

        self.debug_logger()

    def explore(self, world, stepwise=False):
        '''
        Explore the world by sampling new frontiers and waypoints.
        if stepwise is True, the exploration will be done in steps.
        '''
        while self.no_more_frontiers == False:
            if not stepwise:
                self.explore_algo(world)
            elif stepwise:
                # BUG:: matplotlib crashes after 10 sec if we block the execution like this.
                self.keypress = keyboard.read_key()
                if self.keypress:
                    self.keypress = False
                    self.explore_algo(world)

        self.krm.draw_current_krm()