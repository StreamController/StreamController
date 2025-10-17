"""
Thread Pool Manager for StreamController

Centralized thread pool management to replace individual threading.Thread instances
with managed thread pools for better resource control and monitoring.

Author: Core447
Year: 2024
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional, Dict, List
from loguru import logger as log
from collections import defaultdict
import queue


class ThreadPoolStats:
    """Statistics tracking for thread pool usage"""
    
    def __init__(self):
        self.submitted_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.active_tasks = 0
        self.start_time = time.time()
        self.last_reset = time.time()
        
    def reset(self):
        """Reset statistics"""
        self.submitted_tasks = 0
        self.completed_tasks = 0
        self.failed_tasks = 0
        self.last_reset = time.time()
        
    def get_stats(self) -> dict:
        """Get current statistics"""
        uptime = time.time() - self.start_time
        return {
            "submitted_tasks": self.submitted_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "active_tasks": self.active_tasks,
            "uptime_seconds": uptime,
            "tasks_per_second": self.completed_tasks / max(uptime, 1)
        }


class ManagedThreadPoolExecutor(ThreadPoolExecutor):
    """Enhanced ThreadPoolExecutor with statistics and monitoring"""
    
    def __init__(self, pool_name: str, max_workers: int, thread_name_prefix: str):
        super().__init__(max_workers=max_workers, thread_name_prefix=thread_name_prefix)
        self.pool_name = pool_name
        self.stats = ThreadPoolStats()
        self._lock = threading.RLock()
        
    def submit(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a task with statistics tracking"""
        with self._lock:
            self.stats.submitted_tasks += 1
            self.stats.active_tasks += 1
            
        future = super().submit(self._wrap_task, fn, *args, **kwargs)
        return future
        
    def _wrap_task(self, fn: Callable, *args, **kwargs) -> Any:
        """Wrapper to track task completion and handle errors"""
        try:
            result = fn(*args, **kwargs)
            with self._lock:
                self.stats.completed_tasks += 1
            return result
        except Exception as e:
            with self._lock:
                self.stats.failed_tasks += 1
            log.error(f"Task failed in {self.pool_name} pool: {e}")
            raise
        finally:
            with self._lock:
                self.stats.active_tasks -= 1
                
    def get_stats(self) -> dict:
        """Get pool statistics"""
        with self._lock:
            stats = self.stats.get_stats()
            stats["pool_name"] = self.pool_name
            stats["max_workers"] = self._max_workers
            return stats


class ThreadPoolManager:
    """
    Centralized thread pool manager for StreamController
    
    Manages separate thread pools for different types of tasks:
    - background_pool: General background tasks (file I/O, cache operations)  
    - ui_pool: UI-related tasks (asset loading, thumbnail generation)
    - video_pool: Video processing tasks (cache loading, frame processing)
    - network_pool: Network operations (store API calls, downloads)
    """
    
    def __init__(self):
        self._pools: Dict[str, ManagedThreadPoolExecutor] = {}
        self._shutdown = False
        self._lock = threading.RLock()
        
        # Initialize thread pools based on system capabilities
        self._initialize_pools()
        
        log.info("ThreadPoolManager initialized with pools: " + 
                ", ".join([f"{name}({pool._max_workers})" for name, pool in self._pools.items()]))
        
    def _initialize_pools(self):
        """Initialize thread pools with appropriate worker counts"""
        
        # Background tasks: File I/O, cache operations, general processing
        self._pools["background"] = ManagedThreadPoolExecutor(
            pool_name="background",
            max_workers=4,
            thread_name_prefix="bg-work"
        )
        
        # UI tasks: Asset loading, thumbnail generation (limited to avoid blocking UI)
        self._pools["ui"] = ManagedThreadPoolExecutor(
            pool_name="ui", 
            max_workers=2,
            thread_name_prefix="ui-work"
        )
        
        # Video processing: Cache loading, frame processing
        self._pools["video"] = ManagedThreadPoolExecutor(
            pool_name="video",
            max_workers=2, 
            thread_name_prefix="video-work"
        )
        
        # Network operations: Store API calls, downloads
        self._pools["network"] = ManagedThreadPoolExecutor(
            pool_name="network",
            max_workers=3,
            thread_name_prefix="net-work"
        )
        
        # Short-lived tasks: Quick operations, timers, callbacks
        self._pools["quick"] = ManagedThreadPoolExecutor(
            pool_name="quick",
            max_workers=2,
            thread_name_prefix="quick-work"
        )
        
    def submit_background_task(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a background task (file I/O, cache operations)"""
        return self._submit_to_pool("background", fn, *args, **kwargs)
        
    def submit_ui_task(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a UI-related task (asset loading, thumbnail generation)"""
        return self._submit_to_pool("ui", fn, *args, **kwargs)
        
    def submit_video_task(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a video processing task (cache loading, frame processing)"""
        return self._submit_to_pool("video", fn, *args, **kwargs)
        
    def submit_network_task(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a network task (store API calls, downloads)"""
        return self._submit_to_pool("network", fn, *args, **kwargs)
        
    def submit_quick_task(self, fn: Callable, *args, **kwargs) -> Future:
        """Submit a quick task (timers, callbacks, short operations)"""
        return self._submit_to_pool("quick", fn, *args, **kwargs)
        
    def _submit_to_pool(self, pool_name: str, fn: Callable, *args, **kwargs) -> Future:
        """Submit task to specified pool with error handling"""
        if self._shutdown:
            raise RuntimeError("ThreadPoolManager is shutting down")
            
        with self._lock:
            pool = self._pools.get(pool_name)
            if not pool:
                raise ValueError(f"Unknown thread pool: {pool_name}")
                
            try:
                return pool.submit(fn, *args, **kwargs)
            except Exception as e:
                log.error(f"Failed to submit task to {pool_name} pool: {e}")
                raise
                
    def get_pool_stats(self, pool_name: Optional[str] = None) -> Dict:
        """Get statistics for specified pool or all pools"""
        with self._lock:
            if pool_name:
                pool = self._pools.get(pool_name)
                if not pool:
                    raise ValueError(f"Unknown thread pool: {pool_name}")
                return pool.get_stats()
            else:
                return {name: pool.get_stats() for name, pool in self._pools.items()}
                
    def get_overall_stats(self) -> Dict:
        """Get overall statistics across all pools"""
        with self._lock:
            total_submitted = sum(pool.stats.submitted_tasks for pool in self._pools.values())
            total_completed = sum(pool.stats.completed_tasks for pool in self._pools.values())
            total_failed = sum(pool.stats.failed_tasks for pool in self._pools.values())
            total_active = sum(pool.stats.active_tasks for pool in self._pools.values())
            
            return {
                "total_submitted_tasks": total_submitted,
                "total_completed_tasks": total_completed,
                "total_failed_tasks": total_failed,
                "total_active_tasks": total_active,
                "pool_count": len(self._pools),
                "pools": list(self._pools.keys())
            }
            
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for all active tasks to complete"""
        start_time = time.time()
        
        while True:
            stats = self.get_overall_stats()
            if stats["total_active_tasks"] == 0:
                return True
                
            if timeout and (time.time() - start_time) > timeout:
                return False
                
            time.sleep(0.1)
            
    def shutdown(self, wait: bool = True):
        """Shutdown all thread pools"""
        log.info("Shutting down ThreadPoolManager...")
        
        with self._lock:
            self._shutdown = True
            
            for name, pool in self._pools.items():
                try:
                    pool.shutdown(wait=wait)
                    log.debug(f"Shutdown {name} pool")
                except Exception as e:
                    log.error(f"Error shutting down {name} pool: {e}")
                    
        log.info("ThreadPoolManager shutdown complete")
        
    def reset_stats(self):
        """Reset statistics for all pools"""
        with self._lock:
            for pool in self._pools.values():
                pool.stats.reset()
                
    def is_healthy(self) -> bool:
        """Check if thread pool manager is in healthy state"""
        if self._shutdown:
            return False
            
        try:
            stats = self.get_overall_stats()
            # Consider unhealthy if too many tasks are failing
            total_tasks = stats["total_submitted_tasks"]
            if total_tasks > 0:
                failure_rate = stats["total_failed_tasks"] / total_tasks
                if failure_rate > 0.1:  # More than 10% failure rate
                    return False
            return True
        except Exception:
            return False


# Global instance to be initialized in globals.py
thread_pool_manager: Optional[ThreadPoolManager] = None


def get_thread_pool_manager() -> ThreadPoolManager:
    """Get the global thread pool manager instance"""
    global thread_pool_manager
    if thread_pool_manager is None:
        thread_pool_manager = ThreadPoolManager()
    return thread_pool_manager


def submit_background_task(fn: Callable, *args, **kwargs) -> Future:
    """Convenience function for background tasks"""
    return get_thread_pool_manager().submit_background_task(fn, *args, **kwargs)


def submit_ui_task(fn: Callable, *args, **kwargs) -> Future:
    """Convenience function for UI tasks"""
    return get_thread_pool_manager().submit_ui_task(fn, *args, **kwargs)


def submit_video_task(fn: Callable, *args, **kwargs) -> Future:
    """Convenience function for video tasks"""
    return get_thread_pool_manager().submit_video_task(fn, *args, **kwargs)


def submit_network_task(fn: Callable, *args, **kwargs) -> Future:
    """Convenience function for network tasks"""
    return get_thread_pool_manager().submit_network_task(fn, *args, **kwargs)


def submit_quick_task(fn: Callable, *args, **kwargs) -> Future:
    """Convenience function for quick tasks"""
    return get_thread_pool_manager().submit_quick_task(fn, *args, **kwargs)