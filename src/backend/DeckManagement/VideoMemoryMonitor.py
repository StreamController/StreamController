"""
Video Memory Monitor for StreamController
Monitors memory usage in video processing pipeline and triggers cleanup when needed.
"""

import time
import gc
import psutil
import threading
from loguru import logger as log
from typing import Optional

class VideoMemoryMonitor:
    """Monitors memory usage and triggers cleanup for video processing components"""
    
    def __init__(self, warning_threshold_mb: int = 500, critical_threshold_mb: int = 1000):
        """
        Initialize memory monitor
        
        Args:
            warning_threshold_mb: Memory usage in MB to trigger gentle cleanup
            critical_threshold_mb: Memory usage in MB to trigger aggressive cleanup
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # Convert to bytes
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.check_interval = 30.0  # Check every 30 seconds - much less intrusive
        
        # Statistics
        self.cleanup_count = 0
        self.peak_memory = 0
        self.last_check = 0.0
        
        # Background monitoring thread
        self._stop_event = threading.Event()
        self._monitor_thread = None
        self._running = False
    
    def start_monitoring(self):
        """Start background memory monitoring thread"""
        if self._running:
            return
            
        self._running = True
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._background_monitor,
            name="VideoMemoryMonitor",
            daemon=True
        )
        self._monitor_thread.start()
        log.info("Video memory monitoring started (30-second intervals)")
    
    def stop_monitoring(self):
        """Stop background memory monitoring thread"""
        if not self._running:
            return
            
        self._running = False
        self._stop_event.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
        log.info("Video memory monitoring stopped")
    
    def _background_monitor(self):
        """Background thread that monitors memory usage"""
        while not self._stop_event.is_set():
            try:
                self.check_memory_usage()
                # Sleep for the check interval, but wake up if stop is requested
                self._stop_event.wait(timeout=self.check_interval)
            except Exception as e:
                log.error(f"Background memory monitor error: {e}")
                # Continue monitoring even if there's an error
        
    def check_memory_usage(self) -> Optional[str]:
        """
        Check current memory usage and trigger cleanup if needed
        
        Returns:
            Optional[str]: Status message if cleanup was triggered, None otherwise
        """
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # Track peak memory
            if memory_info.rss > self.peak_memory:
                self.peak_memory = memory_info.rss
            
            if memory_info.rss > self.critical_threshold:
                log.warning(f"Critical memory usage: {memory_mb:.1f}MB - forcing cleanup")
                self._force_cleanup()
                self.cleanup_count += 1
                return f"critical_cleanup_{memory_mb:.1f}MB"
                
            elif memory_info.rss > self.warning_threshold:
                log.info(f"High memory usage: {memory_mb:.1f}MB - gentle cleanup")
                self._gentle_cleanup()
                self.cleanup_count += 1
                return f"gentle_cleanup_{memory_mb:.1f}MB"
                
            return None
            
        except Exception as e:
            log.error(f"Memory monitoring error: {e}")
            return None
    
    def _force_cleanup(self) -> None:
        """Aggressive cleanup for critical memory usage"""
        try:
            # Import here to avoid circular imports
            import globals as gl
            
            # Clear background video caches from all deck controllers
            cleared_caches = 0
            if hasattr(gl, 'deck_manager') and hasattr(gl.deck_manager, 'deck_controller'):
                for i, controller in enumerate(gl.deck_manager.deck_controller):
                    # Clear background video cache
                    if hasattr(controller, 'background') and controller.background is not None:
                        if hasattr(controller.background, 'video') and controller.background.video is not None:
                            if hasattr(controller.background.video, 'cache') and controller.background.video.cache is not None:
                                cache_size = len(controller.background.video.cache)
                                controller.background.video.cache.clear()
                                cleared_caches += cache_size
                                log.info(f"Cleared {cache_size} background video frames from controller {i}")
                    
                    # Clear video caches from all inputs (keys, dials, etc.)
                    if hasattr(controller, 'inputs') and controller.inputs is not None:
                        for input_type, inputs in controller.inputs.items():
                            for controller_input in inputs:
                                if hasattr(controller_input, 'video') and controller_input.video is not None:
                                    if hasattr(controller_input.video, 'video_cache') and controller_input.video.video_cache is not None:
                                        if hasattr(controller_input.video.video_cache, 'cache') and controller_input.video.video_cache.cache is not None:
                                            cache_size = len(controller_input.video.video_cache.cache)
                                            controller_input.video.video_cache.cache.clear()
                                            cleared_caches += cache_size
            
            log.info(f"Force cleanup cleared {cleared_caches} video frames")
            
            # Force garbage collection multiple times
            collected = 0
            for _ in range(3):
                collected += gc.collect()
            
            log.info(f"Force GC collected {collected} objects")
            
        except Exception as e:
            log.error(f"Force cleanup failed: {e}")
    
    def _gentle_cleanup(self) -> None:
        """Gentle cleanup for high memory usage"""
        try:
            # Import here to avoid circular imports
            import globals as gl
            
            # Clear only older frames from video caches (keep recent ones)
            cleared_frames = 0
            if hasattr(gl, 'deck_manager') and hasattr(gl.deck_manager, 'deck_controller'):
                for i, controller in enumerate(gl.deck_manager.deck_controller):
                    # Gentle cleanup for background videos - keep last 30 frames
                    if hasattr(controller, 'background') and controller.background is not None:
                        if hasattr(controller.background, 'video') and controller.background.video is not None:
                            if hasattr(controller.background.video, 'cache') and controller.background.video.cache is not None:
                                cache = controller.background.video.cache
                                if len(cache) > 30:
                                    keys_to_remove = sorted(cache.keys())[:-30]
                                    for key in keys_to_remove:
                                        if key in cache:
                                            cache[key] = None
                                            del cache[key]
                                            cleared_frames += 1
                                            
                    # Gentle cleanup for input videos - keep last 15 frames since they're smaller
                    if hasattr(controller, 'inputs') and controller.inputs is not None:
                        for input_type, inputs in controller.inputs.items():
                            for controller_input in inputs:
                                if hasattr(controller_input, 'video') and controller_input.video is not None:
                                    if hasattr(controller_input.video, 'video_cache') and controller_input.video.video_cache is not None:
                                        if hasattr(controller_input.video.video_cache, 'cache') and controller_input.video.video_cache.cache is not None:
                                            cache = controller_input.video.video_cache.cache
                                            if len(cache) > 15:
                                                keys_to_remove = sorted(cache.keys())[:-15]
                                                for cache_key in keys_to_remove:
                                                    if cache_key in cache:
                                                        cache[cache_key] = None
                                                        del cache[cache_key]
                                                        cleared_frames += 1
            
            log.debug(f"Gentle cleanup cleared {cleared_frames} old video frames")
            
            # Single garbage collection
            collected = gc.collect()
            log.debug(f"Gentle GC collected {collected} objects")
            
        except Exception as e:
            log.error(f"Gentle cleanup failed: {e}")
    
    def get_current_memory_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_peak_memory_mb(self) -> float:
        """Get peak memory usage in MB"""
        return self.peak_memory / 1024 / 1024
    
    def get_stats(self) -> dict:
        """Get monitoring statistics"""
        return {
            "cleanup_count": self.cleanup_count,
            "peak_memory_mb": self.get_peak_memory_mb(),
            "current_memory_mb": self.get_current_memory_mb(),
            "warning_threshold_mb": self.warning_threshold / 1024 / 1024,
            "critical_threshold_mb": self.critical_threshold / 1024 / 1024
        }