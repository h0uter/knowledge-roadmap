import time
from abc import ABC, abstractmethod
from typing import Sequence

import src.core.event_system as event_system
from src.config import Scenario, cfg
from src.core import event_system
from src.core.topics import Topics
from src.core.planning.graph_planner_interface import GraphPlannerInterface
from src.core.planning.graph_task_planner import GraphTaskPlanner
from src.mission_autonomy.task_allocator import TaskAllocator
from src.operator.feedback_pipeline import (
    feedback_pipeline_completion,
    feedback_pipeline_init,
    feedback_pipeline_single_step,
)
from src.platform_autonomy.control.abstract_agent import AbstractAgent
from src.platform_autonomy.control.real.spot_agent import SpotAgent
from src.platform_autonomy.control.sim.simulated_agent import SimulatedAgent
from src.platform_autonomy.execution.abstract_behavior import AbstractBehavior
from src.platform_autonomy.platform_runner import PlatformRunnerMessage
from src.shared.plan_model import PlanModel
from src.shared.prior_knowledge.behaviors import Behaviors
from src.shared.prior_knowledge.capabilities import Capabilities
from src.shared.prior_knowledge.objectives import Objectives
from src.shared.situational_graph import SituationalGraph
from src.shared.task import Task

# I want my mainloop to only contain 4 high level steps:
# 1. mission_logic
# 2. platform logic
# 3. process events


def common_initialization(
    tosg: SituationalGraph, agents: Sequence[AbstractAgent], start_poses
):
    """Add a waypoint to the tosg for each agent, but check for duplicates"""
    duplicate_start_poses = []
    for start_pos in start_poses:
        if start_pos not in duplicate_start_poses:
            tosg.add_waypoint_node(start_pos)
            duplicate_start_poses.append(start_pos)

    """setup vizualisation of start poses"""
    for agent in agents:
        agent.get_local_grid()
        # agent.localize_to_waypoint(tosg)
        # HACK: not ideal but this removes dependency of agent on tosg
        AbstractBehavior._localize_to_waypoint(agent, tosg)
        event_system.post_event(
            Topics.MISSION_VIEW_START_POINT, agent.pos
        )  # viz start position


class Mission(ABC):
    def __init__(self):
        self.step = 0
        self.mission_completed = False

    @abstractmethod
    def mission_initialization(
        self,
    ) -> tuple[
        list[AbstractAgent],
        SituationalGraph,
        GraphPlannerInterface,
        TaskAllocator,
    ]:
        pass

    def mission_main_loop(self):

        (
            agents,
            tosg,
            planner,
            task_allocator,
        ) = self.mission_initialization()

        start, tosg_stats, my_logger = feedback_pipeline_init()

        """ Main Logic Loop"""
        while (not self.mission_completed) and self.step < cfg.MAX_STEPS:

            self.inner_loop(
                agents,
                tosg,
                planner,
                my_logger,
                tosg_stats,
                task_allocator,
            )

        feedback_pipeline_completion(
            self.step, agents, tosg, tosg_stats, planner, my_logger, start
        )

        # krm_stats.save()
        return self.mission_completed

    def inner_loop(
        self,
        agents: list[AbstractAgent],
        tosg: SituationalGraph,
        planner: GraphPlannerInterface,
        my_logger,
        tosg_stats,
        task_allocator: TaskAllocator,
    ):
        step_start = time.perf_counter()

        # task allocation
        # my window event will put something in a queue here that will result in that task being done first.
        # and also to lock the goto task in place

        for agent_idx in range(len(agents)):
            agent = agents[agent_idx]

            if agent.init_explore_step_completed:

                # TODO: conceptually figure out who should do the filtering of the graph
                filtered_tosg = planner._filter_graph(tosg, agent.capabilities)

                # task allocation
                """select a task"""
                agent.task = task_allocator._single_agent_task_selection(
                    agent.at_wp, filtered_tosg
                )
                if not agent.task:
                    return tosg.check_if_tasks_exhausted()

            data = PlatformRunnerMessage(agent, tosg)
            event_system.post_event(Topics.RUN_PLATFORM, data)

            self.mission_completed = tosg.check_if_tasks_exhausted()

        """---------------------------------------"""

        feedback_pipeline_single_step(
            self.step, step_start, agents, tosg, tosg_stats, planner, my_logger
        )
        self.step += 1


class MissionRunner(Mission):
    def mission_initialization(self):
        """Manually set first task to exploring current position."""

        (
            agents,
            tosg,
            planner,
            task_allocator,
        ) = self.init_search_and_rescue_entities()

        common_initialization(tosg, agents, start_poses=[agent.pos for agent in agents])

        for agent in agents:

            # Add an explore edge on the start node to ensure a exploration sampling action
            edge = tosg.add_edge_of_type(agent.at_wp, agent.at_wp, Behaviors.EXPLORE)
            tosg.tasks.append(Task(edge, Objectives.EXPLORE_ALL_FTS))

            # spoof the task selection, just select the first one.
            agent.task = tosg.tasks[0]

            # obtain the plan which corresponds to this edge.
            init_explore_edge = agent.task.edge

            agent.plan = PlanModel([init_explore_edge])

        return agents, tosg, planner, task_allocator

    @staticmethod
    # TODO: refactor out the dependency on a specific agent.
    def init_search_and_rescue_entities() -> tuple[
        list[AbstractAgent],
        SituationalGraph,
        GraphPlannerInterface,
        TaskAllocator,
    ]:
        agent1_capabilities = {Capabilities.CAN_ASSESS}
        if cfg.SCENARIO == Scenario.REAL:
            agents = [SpotAgent(agent1_capabilities)]
        else:
            agents = [
                SimulatedAgent(agent1_capabilities)
            ]  # make the first agent only posses the capabilities
            agents.extend([SimulatedAgent(set(), i) for i in range(1, cfg.NUM_AGENTS)])

        tosg = SituationalGraph()
        task_allocator = TaskAllocator()
        planner = GraphTaskPlanner()

        return agents, tosg, planner, task_allocator
