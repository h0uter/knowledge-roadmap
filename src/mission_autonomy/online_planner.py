from src.mission_autonomy.abstract_planner import (
    AbstractPlanner,
    CouldNotFindPlan,
    TargetNodeNotFound,
)
from src.mission_autonomy.executor import PlanExecutor
from src.mission_autonomy.situational_graph import SituationalGraph
from src.platform_control.abstract_agent import AbstractAgent


class OnlinePlanner(AbstractPlanner):
    """This planner selects the optimal task and makes a plan each iteration"""

    def pipeline(
        self, agent: AbstractAgent, tosg: SituationalGraph, executor: PlanExecutor
    ) -> bool:
        if agent.init_explore_step_completed:

            filtered_tosg = self._filter_graph(tosg, agent)

            """select a task"""
            agent.task = self._task_selection(agent, filtered_tosg)
            if not agent.task:
                return tosg.check_if_tasks_exhausted()

            """ generate a plan"""
            try:
                agent.plan = self._find_plan_for_task(
                    agent.at_wp, tosg, agent.task, filtered_tosg
                )
            except CouldNotFindPlan:
                self._log.error(f"Could not find a plan for task {agent.task}")
                agent.clear_task()
            except TargetNodeNotFound:
                self._log.error(f"Could not find a target node for task {agent.task}")
                agent.clear_task()

        if not self.validate_plan(agent.plan, tosg):
            return None

    def process_execution_result(self, result, agent: AbstractAgent, tosg):

        if result.success:
            agent.plan.mutate_success()
            if len(agent.plan) == 0:
                self._destroy_task(agent, tosg)
                agent.plan = None
        else:
            self._destroy_task(agent, tosg)
            agent.plan = None

        """check completion of mission"""
        tasks_exhausted = tosg.check_if_tasks_exhausted()

        return tasks_exhausted
