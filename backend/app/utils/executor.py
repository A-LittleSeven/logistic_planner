"""运筹计算进程池/线程池调度器 (Solver Executor Pool)。

将 CPU 密集型的运筹优化（OR-Tools CVRP、ConstrainedKmeans、启发式排班与 2-opt 局部搜索）
与 FastAPI Web 事件循环及 SQLite 数据库会话彻底解耦：
- 计算期间不持有任何数据库连接（DB Session 仅在计算前后的毫秒级窗口内按需开启并立即释放）。
- 默认通过 ProcessPoolExecutor 在独立工作进程中并行执行纯计算任务，释放 GIL 与事件循环。
"""
import asyncio
import os
import pickle
import threading
from concurrent.futures import Executor, ProcessPoolExecutor, ThreadPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Any, Dict, Optional

from app.utils.distance import DistanceProvider, ensure_provider
from app.utils.logger import LogUtil

logger = LogUtil.get_logger(__name__)

_pool_lock = threading.Lock()
_process_pool: Optional[ProcessPoolExecutor] = None
_thread_pool: Optional[ThreadPoolExecutor] = None
_MAX_WORKERS = max(1, min(4, os.cpu_count() or 2))


def _run_solver_in_worker(
    domain: str,
    algorithm: str,
    req: Any,
    provider: Optional[DistanceProvider] = None,
) -> Dict[str, Any]:
    """在独立工作进程中执行的顶层纯计算入口函数（无 DB Session 依赖，参数与返回值完全可序列化）。"""
    prov = ensure_provider(provider)
    if domain == "clustering":
        from app.solvers import clustering_solver  # noqa: F401
        from app.utils.registry import clustering_registry
        solver = clustering_registry.get(algorithm)
        return solver(req, prov)
    elif domain == "schedule":
        from app.solvers import schedule_solver  # noqa: F401
        from app.utils.registry import schedule_registry
        solver = schedule_registry.get(algorithm)
        return solver(req, prov)
    elif domain == "routing":
        from app.solvers import routing_solver  # noqa: F401
        from app.utils.registry import routing_registry
        solver = routing_registry.get(algorithm)
        return solver(req, prov)
    else:
        raise ValueError(f"未知的求解领域: {domain}")


def get_solver_process_pool() -> Executor:
    """获取或惰性初始化全局运筹计算进程池（受限环境下自动降级为线程池）。"""
    global _process_pool
    if _process_pool is not None:
        return _process_pool
    with _pool_lock:
        if _process_pool is None:
            try:
                _process_pool = ProcessPoolExecutor(max_workers=_MAX_WORKERS)
                logger.info(f"🚀 运筹计算进程池已启动 (max_workers={_MAX_WORKERS})")
            except (PermissionError, OSError) as exc:
                logger.warning(f"当前运行环境限制多进程信号量，自动降级为线程池执行: {exc}")
                return get_solver_thread_pool()
    return _process_pool


def get_solver_thread_pool() -> ThreadPoolExecutor:
    """获取备用线程池执行器。"""
    global _thread_pool
    if _thread_pool is not None:
        return _thread_pool
    with _pool_lock:
        if _thread_pool is None:
            _thread_pool = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="solver_worker")
    return _thread_pool


async def run_solver_in_pool(
    domain: str,
    algorithm: str,
    req: Any,
    provider: Optional[DistanceProvider] = None,
) -> Dict[str, Any]:
    """将纯运筹求解任务异步派发至进程池执行，计算期间不阻塞事件循环且不占用数据库连接。"""
    loop = asyncio.get_running_loop()
    prov = ensure_provider(provider)
    pool = get_solver_process_pool()
    try:
        return await loop.run_in_executor(pool, _run_solver_in_worker, domain, algorithm, req, prov)
    except pickle.PicklingError as exc:
        # 仅参数/结果不可 pickle 时降级：求解器内部业务异常不属于此情形，不重跑
        logger.warning(f"求解参数包含不可跨进程序列化对象 ({exc})，自动回退至工作线程池执行")
        t_pool = get_solver_thread_pool()
        return await loop.run_in_executor(t_pool, _run_solver_in_worker, domain, algorithm, req, prov)
    except BrokenProcessPool as exc:
        # 进程池崩溃（如受限环境无法 spawn、worker 被杀）：丢弃坏池，降级线程池重试一次
        global _process_pool
        logger.warning(
            f"运筹进程池崩溃 ({exc})，已降级为线程池执行；"
            "注意：线程池内 TruckIdAllocator/车型池为进程级全局状态，并发求解可能相互干扰"
        )
        with _pool_lock:
            if _process_pool is not None:
                try:
                    _process_pool.shutdown(wait=False, cancel_futures=True)
                except Exception:
                    pass
                _process_pool = None
        t_pool = get_solver_thread_pool()
        return await loop.run_in_executor(t_pool, _run_solver_in_worker, domain, algorithm, req, prov)


def shutdown_solver_pool(wait: bool = False):
    """优雅关闭运筹计算进程池与线程池。"""
    global _process_pool, _thread_pool
    with _pool_lock:
        if _process_pool is not None:
            try:
                _process_pool.shutdown(wait=wait, cancel_futures=True)
            except Exception:
                pass
            _process_pool = None
        if _thread_pool is not None:
            try:
                _thread_pool.shutdown(wait=wait, cancel_futures=True)
            except Exception:
                pass
            _thread_pool = None

