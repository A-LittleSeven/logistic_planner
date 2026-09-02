"""求解器注册表。

拓展点: 新增一个求解算法 = 写一个函数 -> 用对应 registry.register 注册。
路由层通过 registry.get(name) 取用, 无需改路由代码。
"""
from typing import Callable

SolverFunc = Callable[..., dict]


class SolverRegistry:
    def __init__(self) -> None:
        self._solvers: dict[str, SolverFunc] = {}

    def register(self, name: str, func: SolverFunc) -> SolverFunc:
        self._solvers[name] = func
        return func

    def get(self, name: str) -> SolverFunc:
        if name not in self._solvers:
            raise KeyError(
                f"未注册的求解器: {name}; 可用: {self.list()}"
            )
        return self._solvers[name]

    def list(self) -> list[str]:
        return list(self._solvers)


# 每个模块一个注册表
location_registry = SolverRegistry()
routing_registry = SolverRegistry()
clustering_registry = SolverRegistry()
schedule_registry = SolverRegistry()

