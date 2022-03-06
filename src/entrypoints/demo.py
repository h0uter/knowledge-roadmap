import logging
import time
from typing import Sequence

import matplotlib

from src.data_providers.simulated_agent import SimulatedAgent
from src.data_providers.spot_agent import SpotAgent
from src.entities.knowledge_roadmap import KnowledgeRoadmap
from src.entities.abstract_agent import AbstractAgent
import src.utils.event as event
from src.usecases.exploration_usecase import ExplorationUsecase
from src.utils.config import Config, PlotLvl, Scenario, Vizualiser
from src.entrypoints.vizualisation_listener import VizualisationListener
from src.utils.krm_stats import KRMStats


############################################################################################
# DEMONSTRATIONS
############################################################################################


def init_entities(cfg: Config):
    if cfg.SCENARIO == Scenario.REAL:
        agents = [SpotAgent()]
    else:
        agents = [
            SimulatedAgent(cfg.AGENT_START_POS, cfg, i) for i in range(cfg.NUM_AGENTS)
        ]

    krm = KnowledgeRoadmap(cfg, start_poses=[agent.pos for agent in agents])
    exploration_usecases = [ExplorationUsecase(cfg) for i in range(cfg.NUM_AGENTS)]

    VizualisationListener(
        cfg
    ).setup_event_handler()  # setup the listener for vizualisation

    return agents, krm, exploration_usecases


def priority_frontier_mvp_test(step, krm):
    if step >= 1:
        """" experiment with neg edge cost"""
        frontiers = krm.get_all_frontiers_idxs()
        lowest_frontier_idx = min(frontiers)
        prio_ft_data = krm.get_node_data_by_idx(lowest_frontier_idx)
        krm.set_frontier_edge_weight(lowest_frontier_idx, -100.0)
        prio_ft_pos = prio_ft_data["pos"]

        event.post_event("viz point", prio_ft_pos)
        # for edge in krm.graph.edges:
        #     print(f"edge: {edge} properties: {krm.graph.edges[edge]}")


# TODO: cleanup all the stuff not neccesary to understand the code high level
def perform_exploration_demo(
    cfg: Config,
    agents: Sequence[AbstractAgent],
    krm: KnowledgeRoadmap,
    exploration_usecases: Sequence[ExplorationUsecase],
):
    step = 0
    krm_stats = KRMStats()

    start = time.perf_counter()
    my_logger = logging.getLogger(__name__)

    """setup"""
    for agent in agents:
        exploration_usecases[agent.name].exploration_strategy.localize_agent_to_wp(
            agent, krm
        )
        # krm.add_world_object(agent.pos, f"Agent {agent.name} start")

    """ Main Logic"""
    my_logger.info(f"starting exploration demo {cfg.SCENARIO=}")
    while (
        not any(
            exploration_usecase.exploration_strategy.exploration_completed is True
            for exploration_usecase in exploration_usecases
        )
        and step < cfg.MAX_STEPS
    ):
        step_start = time.perf_counter()

        for agent_idx in range(len(agents)):
            if exploration_usecases[agent_idx].run_usecase_step(agents[agent_idx], krm):
                my_logger.info(f"Agent {agent_idx} completed exploration")
                break

        """Data collection"""
        step_duration = time.perf_counter() - step_start
        krm_stats.update(krm, step_duration)

        """ Visualisation """
        my_logger.debug(
            f"{step} -------------------------------------------------------- {step_duration:.4f}s"
        )
        event.post_event(
            "figure update",
            {"krm": krm, "agents": agents, "usecases": exploration_usecases},
        )

        if step % 50 == 0:
            s = f"sim step = {step} took {step_duration:.4f}s, with {agents[0].steps_taken} move actions"
            my_logger.info(s)

            # priority_frontier_test(step, krm)

        step += 1

    """Results"""
    # TODO: move this to the usecase, close to the data
    my_logger.info(
        f"""
    !!!!!!!!!!! EXPLORATION COMPLETED !!!!!!!!!!!
    It took {step} sim steps
    with {agents[0].steps_taken} move actions
    and {time.perf_counter()-start:.2f}s to complete the exploration.
        """
    )

    event.post_event(
        "figure final result",
        {"krm": krm, "agents": agents, "usecases": exploration_usecases},
    )

    if cfg.PLOT_LVL <= PlotLvl.STATS_ONLY:
        krm_stats.plot_krm_stats()

    # krm_stats.save()

    return not any(
        exploration_usecase.exploration_strategy.exploration_completed is True
        for exploration_usecase in exploration_usecases
    )


def main(cfg: Config):
    agents, krm, exploration_usecases = init_entities(cfg)
    success = perform_exploration_demo(cfg, agents, krm, exploration_usecases)
    return success


def benchmark_func():
    cfg = Config(
        plot_lvl=PlotLvl.NONE,
        num_agents=1,
        scenario=Scenario.SIM_MAZE_MEDIUM,
        max_steps=400,
    )
    main(cfg)


if __name__ == "__main__":
    matplotlib.use("Qt5agg")

    cfg = Config()
    # cfg = Config(scenario=Scenario.SIM_VILLA_ROOM)
    # cfg = Config(num_agents=5, scenario=Scenario.SIM_MAZE_MEDIUM)
    # cfg = Config(num_agents=2)
    # cfg = Config(num_agents=10, scenario=Scenario.SIM_MAZE_MEDIUM)
    # cfg = Config(plot_lvl=PlotLvl.NONE)
    # cfg = Config(scenario=Scenario.SIM_VILLA_ROOM, plot_lvl=PlotLvl.RESULT_ONLY)
    # cfg = Config(scenario=Scenario.SIM_MAZE)
    # cfg = Config(scenario=Scenario.SIM_VILLA, vizualiser=Vizualiser.MATPLOTLIB)
    # cfg = Config(plot_lvl=PlotLvl.RESULT_ONLY, scenario=Scenario.SIM_MAZE_MEDIUM)

    # cfg = Config(scenario=Scenario.REAL, vizualiser=Vizualiser.MATPLOTLIB)

    # cfg = Config(PlotLvl.NONE, World.SIM_MAZE, num_agents=10)
    # cfg = Config(scenario=Scenario.SIM_VILLA, num_agents=10)
    # cfg = Config(scenario=Scenario.SIM_MAZE_MEDIUM)
    # cfg = Config(scenario=Scenario.SIM_MAZE_MEDIUM, vizualiser=Vizualiser.MATPLOTLIB)
    # cfg = Config(vizualiser=Vizualiser.MATPLOTLIB)

    main(cfg)
    # benchmark_func()
