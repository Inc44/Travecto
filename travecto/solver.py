from __future__ import annotations

from typing import List

from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def tsp(
	distance_matrix: List[List[int]],
	start_idx: int,
	workers: int,
	time_limit_s: int,
) -> List[int]:
	size = len(distance_matrix)
	manager = pywrapcp.RoutingIndexManager(size, 1, start_idx)
	routing_model = pywrapcp.RoutingModel(manager)

	def distance(from_index: int, to_index: int) -> int:
		origin = manager.IndexToNode(from_index)
		destination = manager.IndexToNode(to_index)
		return distance_matrix[origin][destination]

	callback_id = routing_model.RegisterTransitCallback(distance)
	routing_model.SetArcCostEvaluatorOfAllVehicles(callback_id)
	search_params = pywrapcp.DefaultRoutingSearchParameters()
	search_params.first_solution_strategy = (
		routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
	)
	search_params.local_search_metaheuristic = (
		routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
	)
	search_params.time_limit.FromSeconds(time_limit_s)
	if hasattr(search_params, "num_search_workers"):
		search_params.num_search_workers = workers
	solution = routing_model.SolveWithParameters(search_params)
	if solution is None:
		raise RuntimeError("TSP solver failed to find a solution")
	route = []
	idx = routing_model.Start(0)
	while not routing_model.IsEnd(idx):
		route.append(manager.IndexToNode(idx))
		idx = solution.Value(routing_model.NextVar(idx))
	route.append(manager.IndexToNode(idx))
	return route
