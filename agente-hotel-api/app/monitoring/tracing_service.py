"""
Distributed Tracing Service
Advanced distributed tracing with correlation tracking and performance insights
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextvars import ContextVar
from collections import defaultdict, deque
import json
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SpanKind(str, Enum):
    """Span types for distributed tracing"""

    SERVER = "server"  # Server-side span
    CLIENT = "client"  # Client-side span
    PRODUCER = "producer"  # Message producer
    CONSUMER = "consumer"  # Message consumer
    INTERNAL = "internal"  # Internal operation


class SpanStatus(str, Enum):
    """Span status"""

    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class TraceLevel(str, Enum):
    """Trace detail levels"""

    BASIC = "basic"  # Basic timing and status
    DETAILED = "detailed"  # Include parameters and results
    DEBUG = "debug"  # Include all internal details


@dataclass
class TraceContext:
    """Trace context for correlation"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)
    sampling_decision: bool = True
    trace_flags: int = 0


@dataclass
class SpanAttribute:
    """Span attribute with metadata"""

    key: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanEvent:
    """Event within a span"""

    name: str
    timestamp: datetime
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    """Distributed tracing span"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    operation_name: str
    service_name: str
    span_kind: SpanKind
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    error_message: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[str] = field(default_factory=list)  # Links to other spans
    trace_level: TraceLevel = TraceLevel.BASIC


@dataclass
class Trace:
    """Complete trace with all spans"""

    trace_id: str
    spans: List[Span]
    start_time: datetime
    end_time: datetime
    duration_ms: float
    service_map: Dict[str, List[str]]  # service -> operations
    error_count: int
    span_count: int
    root_operation: str
    business_context: Dict[str, Any] = field(default_factory=dict)


# Context variables for trace correlation
trace_context: ContextVar[Optional[TraceContext]] = ContextVar("trace_context", default=None)
current_span: ContextVar[Optional[Span]] = ContextVar("current_span", default=None)


class DistributedTracingService:
    """Advanced distributed tracing with business intelligence"""

    def __init__(self, redis_client, service_name: str = "agente-hotel-api"):
        self.redis = redis_client
        self.service_name = service_name

        # Trace storage
        self.active_traces = {}
        self.completed_traces = deque(maxlen=1000)
        self.span_buffer = defaultdict(list)

        # Performance analytics
        self.operation_stats = defaultdict(
            lambda: {
                "count": 0,
                "total_duration": 0.0,
                "error_count": 0,
                "p95_duration": 0.0,
                "last_updated": datetime.utcnow(),
            }
        )

        # Sampling configuration
        self.sampling_rules = {
            "default": 0.1,  # 10% sampling
            "error": 1.0,  # 100% sampling for errors
            "slow": 0.5,  # 50% sampling for slow operations
            "business_critical": 1.0,  # 100% for critical operations
        }

        # Trace enrichment rules
        self.enrichment_rules = {}

        # Start background tasks
        self._start_background_tasks()

    async def start_trace(
        self,
        operation_name: str,
        span_kind: SpanKind = SpanKind.INTERNAL,
        tags: Dict[str, str] = None,
        trace_level: TraceLevel = TraceLevel.BASIC,
        parent_context: TraceContext = None,
    ) -> TraceContext:
        """Start a new trace or child span"""

        current_context = trace_context.get()

        if parent_context:
            # Use provided parent context
            trace_id = parent_context.trace_id
            parent_span_id = parent_context.span_id
        elif current_context:
            # Continue existing trace
            trace_id = current_context.trace_id
            parent_span_id = current_context.span_id
        else:
            # Start new trace
            trace_id = self._generate_trace_id()
            parent_span_id = None

        # Generate span ID
        span_id = self._generate_span_id()

        # Create trace context
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            sampling_decision=self._should_sample(operation_name, tags),
            baggage=current_context.baggage.copy() if current_context else {},
        )

        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=self.service_name,
            span_kind=span_kind,
            start_time=datetime.utcnow(),
            tags=tags or {},
            trace_level=trace_level,
        )

        # Store span if sampling
        if context.sampling_decision:
            self.span_buffer[trace_id].append(span)

            # Store in active traces
            if trace_id not in self.active_traces:
                self.active_traces[trace_id] = {
                    "start_time": span.start_time,
                    "root_operation": operation_name,
                    "service": self.service_name,
                    "span_count": 0,
                }

            self.active_traces[trace_id]["span_count"] += 1

        # Set context
        trace_context.set(context)
        current_span.set(span)

        logger.debug(f"Started span: {operation_name} (trace: {trace_id[:8]}...)")

        return context

    async def finish_span(
        self, status: SpanStatus = SpanStatus.OK, error_message: str = None, attributes: Dict[str, Any] = None
    ) -> Optional[Span]:
        """Finish the current span"""

        span = current_span.get()
        if not span:
            logger.warning("No active span to finish")
            return None

        # Update span
        span.end_time = datetime.utcnow()
        span.duration_ms = (span.end_time - span.start_time).total_seconds() * 1000
        span.status = status

        if error_message:
            span.error_message = error_message

        if attributes:
            span.attributes.update(attributes)

        # Update operation statistics
        await self._update_operation_stats(span)

        # Check if trace is complete
        context = trace_context.get()
        if context and context.sampling_decision:
            await self._check_trace_completion(span.trace_id)

        logger.debug(f"Finished span: {span.operation_name} ({span.duration_ms:.2f}ms)")

        return span

    @asynccontextmanager
    async def trace_operation(
        self,
        operation_name: str,
        span_kind: SpanKind = SpanKind.INTERNAL,
        tags: Dict[str, str] = None,
        trace_level: TraceLevel = TraceLevel.BASIC,
    ):
        """Context manager for tracing operations"""

        await self.start_trace(operation_name, span_kind, tags, trace_level)
        span = current_span.get()
        exception_occurred = False

        try:
            yield span
        except Exception as e:
            exception_occurred = True

            # Add error details to span
            if span:
                span.status = SpanStatus.ERROR
                span.error_message = str(e)
                span.attributes["error.type"] = type(e).__name__
                span.attributes["error.message"] = str(e)

            raise
        finally:
            # Finish span
            status = SpanStatus.ERROR if exception_occurred else SpanStatus.OK
            await self.finish_span(status)

    async def add_span_event(self, name: str, attributes: Dict[str, Any] = None):
        """Add event to current span"""

        span = current_span.get()
        if not span:
            return

        event = SpanEvent(name=name, timestamp=datetime.utcnow(), attributes=attributes or {})

        span.events.append(event)
        logger.debug(f"Added span event: {name}")

    async def set_span_attribute(self, key: str, value: Any, metadata: Dict[str, Any] = None):
        """Set attribute on current span"""

        span = current_span.get()
        if not span:
            return

        span.attributes[key] = value

        if metadata:
            span.attributes[f"{key}.metadata"] = metadata

    async def set_baggage(self, key: str, value: str):
        """Set baggage item that propagates across spans"""

        context = trace_context.get()
        if context:
            context.baggage[key] = value

    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get complete trace by ID"""

        # Check completed traces first
        for trace in self.completed_traces:
            if trace.trace_id == trace_id:
                return trace

        # Check Redis for older traces
        trace_key = f"trace:{trace_id}"
        cached_trace = await self.redis.get(trace_key)

        if cached_trace:
            trace_data = json.loads(cached_trace)
            return self._deserialize_trace(trace_data)

        return None

    async def get_traces(
        self,
        service_name: str = None,
        operation_name: str = None,
        status: SpanStatus = None,
        min_duration_ms: float = None,
        hours: int = 24,
    ) -> List[Trace]:
        """Get traces with filtering"""

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Filter from memory
        traces = [trace for trace in self.completed_traces if trace.start_time > cutoff_time]

        # Apply filters
        if service_name:
            traces = [t for t in traces if service_name in t.service_map]

        if operation_name:
            traces = [t for t in traces if any(operation_name in ops for ops in t.service_map.values())]

        if status:
            traces = [t for t in traces if any(span.status == status for span in t.spans)]

        if min_duration_ms:
            traces = [t for t in traces if t.duration_ms >= min_duration_ms]

        return sorted(traces, key=lambda t: t.start_time, reverse=True)

    async def get_operation_analytics(self, hours: int = 24) -> Dict[str, Any]:
        """Get operation performance analytics"""

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get recent traces
        recent_traces = [trace for trace in self.completed_traces if trace.start_time > cutoff_time]

        # Analyze operations
        operation_metrics = defaultdict(lambda: {"count": 0, "total_duration": 0.0, "error_count": 0, "durations": []})

        service_metrics = defaultdict(
            lambda: {"trace_count": 0, "span_count": 0, "error_count": 0, "operations": set()}
        )

        for trace in recent_traces:
            for span in trace.spans:
                op_key = f"{span.service_name}.{span.operation_name}"

                # Operation metrics
                operation_metrics[op_key]["count"] += 1
                operation_metrics[op_key]["total_duration"] += span.duration_ms or 0
                operation_metrics[op_key]["durations"].append(span.duration_ms or 0)

                if span.status == SpanStatus.ERROR:
                    operation_metrics[op_key]["error_count"] += 1

                # Service metrics
                service_metrics[span.service_name]["span_count"] += 1
                service_metrics[span.service_name]["operations"].add(span.operation_name)

                if span.status == SpanStatus.ERROR:
                    service_metrics[span.service_name]["error_count"] += 1

            # Count traces per service
            for service in trace.service_map:
                service_metrics[service]["trace_count"] += 1

        # Calculate percentiles and rates
        operation_analytics = {}
        for op_name, metrics in operation_metrics.items():
            durations = metrics["durations"]

            if durations:
                durations.sort()
                count = len(durations)

                analytics = {
                    "operation": op_name,
                    "total_calls": metrics["count"],
                    "error_count": metrics["error_count"],
                    "error_rate": (metrics["error_count"] / metrics["count"]) * 100,
                    "avg_duration_ms": metrics["total_duration"] / metrics["count"],
                    "p50_duration_ms": durations[int(count * 0.5)],
                    "p95_duration_ms": durations[int(count * 0.95)],
                    "p99_duration_ms": durations[int(count * 0.99)],
                    "min_duration_ms": min(durations),
                    "max_duration_ms": max(durations),
                }

                operation_analytics[op_name] = analytics

        # Service analytics
        service_analytics = {}
        for service_name, metrics in service_metrics.items():
            service_analytics[service_name] = {
                "service": service_name,
                "trace_count": metrics["trace_count"],
                "span_count": metrics["span_count"],
                "error_count": metrics["error_count"],
                "operation_count": len(metrics["operations"]),
                "operations": list(metrics["operations"]),
            }

        return {
            "period_hours": hours,
            "total_traces": len(recent_traces),
            "total_spans": sum(len(t.spans) for t in recent_traces),
            "operations": operation_analytics,
            "services": service_analytics,
            "error_summary": {
                "total_errors": sum(t.error_count for t in recent_traces),
                "error_rate": (sum(t.error_count for t in recent_traces) / sum(len(t.spans) for t in recent_traces))
                * 100
                if recent_traces
                else 0,
            },
        }

    async def get_service_map(self, hours: int = 24) -> Dict[str, Any]:
        """Generate service dependency map"""

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)

        # Get recent traces
        recent_traces = [trace for trace in self.completed_traces if trace.start_time > cutoff_time]

        # Build service map
        service_calls = defaultdict(
            lambda: defaultdict(
                lambda: {"call_count": 0, "error_count": 0, "avg_duration_ms": 0.0, "total_duration": 0.0}
            )
        )

        services = set()

        for trace in recent_traces:
            sorted_spans = sorted(trace.spans, key=lambda s: s.start_time)

            for i, span in enumerate(sorted_spans):
                services.add(span.service_name)

                # Find downstream calls
                for j in range(i + 1, len(sorted_spans)):
                    next_span = sorted_spans[j]

                    # If next span starts within current span timeframe
                    if (
                        span.end_time
                        and next_span.start_time
                        and next_span.start_time <= span.end_time
                        and span.span_id == next_span.parent_span_id
                    ):
                        # Record service call
                        call_data = service_calls[span.service_name][next_span.service_name]
                        call_data["call_count"] += 1
                        call_data["total_duration"] += next_span.duration_ms or 0

                        if next_span.status == SpanStatus.ERROR:
                            call_data["error_count"] += 1

        # Calculate averages
        for source_service, targets in service_calls.items():
            for target_service, data in targets.items():
                if data["call_count"] > 0:
                    data["avg_duration_ms"] = data["total_duration"] / data["call_count"]
                    data["error_rate"] = (data["error_count"] / data["call_count"]) * 100

        return {
            "services": list(services),
            "service_calls": dict(service_calls),
            "period_hours": hours,
            "trace_count": len(recent_traces),
        }

    async def get_critical_path_analysis(self, trace_id: str) -> Dict[str, Any]:
        """Analyze critical path for a trace"""

        trace = await self.get_trace(trace_id)
        if not trace:
            return {"error": "Trace not found"}

        # Build span tree
        span_tree = self._build_span_tree(trace.spans)

        # Find critical path (longest duration path)
        critical_path = self._find_critical_path(span_tree)

        # Calculate path statistics
        path_duration = sum(span.duration_ms or 0 for span in critical_path)
        path_percentage = (path_duration / trace.duration_ms) * 100 if trace.duration_ms > 0 else 0

        # Identify bottlenecks
        bottlenecks = [
            span
            for span in critical_path
            if (span.duration_ms or 0) > (path_duration * 0.2)  # >20% of critical path
        ]

        return {
            "trace_id": trace_id,
            "critical_path": [
                {
                    "operation": span.operation_name,
                    "service": span.service_name,
                    "duration_ms": span.duration_ms,
                    "percentage": ((span.duration_ms or 0) / path_duration) * 100 if path_duration > 0 else 0,
                }
                for span in critical_path
            ],
            "path_duration_ms": path_duration,
            "path_percentage": path_percentage,
            "bottlenecks": [
                {
                    "operation": span.operation_name,
                    "service": span.service_name,
                    "duration_ms": span.duration_ms,
                    "impact": ((span.duration_ms or 0) / path_duration) * 100 if path_duration > 0 else 0,
                }
                for span in bottlenecks
            ],
            "optimization_suggestions": self._generate_optimization_suggestions(critical_path, bottlenecks),
        }

    async def search_traces(self, query: Dict[str, Any]) -> List[Trace]:
        """Search traces with complex query"""

        # Extract search parameters
        service_name = query.get("service")
        operation_name = query.get("operation")
        min_duration = query.get("min_duration_ms")
        max_duration = query.get("max_duration_ms")
        status = query.get("status")
        tag_filters = query.get("tags", {})
        attribute_filters = query.get("attributes", {})
        time_range = query.get("time_range", {"hours": 24})

        # Get traces in time range
        hours = time_range.get("hours", 24)
        traces = await self.get_traces(hours=hours)

        # Apply filters
        filtered_traces = []

        for trace in traces:
            # Check service filter
            if service_name and service_name not in trace.service_map:
                continue

            # Check operation filter
            if operation_name:
                found_operation = any(operation_name in operations for operations in trace.service_map.values())
                if not found_operation:
                    continue

            # Check duration filters
            if min_duration and trace.duration_ms < min_duration:
                continue

            if max_duration and trace.duration_ms > max_duration:
                continue

            # Check status filter
            if status:
                found_status = any(span.status == status for span in trace.spans)
                if not found_status:
                    continue

            # Check tag filters
            if tag_filters:
                found_tags = any(all(span.tags.get(k) == v for k, v in tag_filters.items()) for span in trace.spans)
                if not found_tags:
                    continue

            # Check attribute filters
            if attribute_filters:
                found_attributes = any(
                    all(span.attributes.get(k) == v for k, v in attribute_filters.items()) for span in trace.spans
                )
                if not found_attributes:
                    continue

            filtered_traces.append(trace)

        return filtered_traces

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID"""
        return str(uuid.uuid4()).replace("-", "")

    def _generate_span_id(self) -> str:
        """Generate unique span ID"""
        return str(uuid.uuid4()).replace("-", "")[:16]

    def _should_sample(self, operation_name: str, tags: Dict[str, str] = None) -> bool:
        """Determine if trace should be sampled"""

        # Check for error sampling
        if tags and tags.get("error") == "true":
            return self.sampling_rules["error"] > 0.5

        # Check for business critical operations
        if any(keyword in operation_name.lower() for keyword in ["reservation", "payment", "checkin", "checkout"]):
            return self.sampling_rules["business_critical"] > 0.5

        # Default sampling
        import random

        return random.random() < self.sampling_rules["default"]

    async def _update_operation_stats(self, span: Span):
        """Update operation statistics"""

        op_key = f"{span.service_name}.{span.operation_name}"
        stats = self.operation_stats[op_key]

        stats["count"] += 1
        stats["total_duration"] += span.duration_ms or 0

        if span.status == SpanStatus.ERROR:
            stats["error_count"] += 1

        stats["last_updated"] = datetime.utcnow()

    async def _check_trace_completion(self, trace_id: str):
        """Check if trace is complete and process it"""

        # Simple heuristic: trace is complete if no new spans for 5 seconds
        # In real implementation, this would be more sophisticated

        if trace_id not in self.active_traces:
            return

        trace_info = self.active_traces[trace_id]
        time_since_start = (datetime.utcnow() - trace_info["start_time"]).total_seconds()

        # Consider trace complete after reasonable time or explicit completion
        if time_since_start > 30:  # 30 seconds max trace duration
            await self._complete_trace(trace_id)

    async def _complete_trace(self, trace_id: str):
        """Complete and store a trace"""

        if trace_id not in self.span_buffer:
            return

        spans = self.span_buffer[trace_id]
        if not spans:
            return

        # Sort spans by start time
        spans.sort(key=lambda s: s.start_time)

        # Calculate trace metrics
        start_time = min(span.start_time for span in spans)
        end_time = max(span.end_time for span in spans if span.end_time)
        duration_ms = (end_time - start_time).total_seconds() * 1000

        # Build service map
        service_map = defaultdict(set)
        for span in spans:
            service_map[span.service_name].add(span.operation_name)

        # Convert sets to lists for serialization
        service_map = {k: list(v) for k, v in service_map.items()}

        # Count errors
        error_count = sum(1 for span in spans if span.status == SpanStatus.ERROR)

        # Get root operation
        root_spans = [span for span in spans if span.parent_span_id is None]
        root_operation = root_spans[0].operation_name if root_spans else spans[0].operation_name

        # Create trace object
        trace = Trace(
            trace_id=trace_id,
            spans=spans,
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            service_map=service_map,
            error_count=error_count,
            span_count=len(spans),
            root_operation=root_operation,
        )

        # Store completed trace
        self.completed_traces.append(trace)

        # Store in Redis for persistence
        trace_key = f"trace:{trace_id}"
        await self.redis.setex(
            trace_key,
            86400 * 7,  # 7 days retention
            json.dumps(asdict(trace), default=str),
        )

        # Clean up
        del self.span_buffer[trace_id]
        if trace_id in self.active_traces:
            del self.active_traces[trace_id]

        logger.info(f"Completed trace: {trace_id} ({duration_ms:.2f}ms, {len(spans)} spans)")

    def _build_span_tree(self, spans: List[Span]) -> Dict[str, List[Span]]:
        """Build span parent-child tree"""

        tree = defaultdict(list)

        for span in spans:
            parent_id = span.parent_span_id or "root"
            tree[parent_id].append(span)

        return dict(tree)

    def _find_critical_path(self, span_tree: Dict[str, List[Span]]) -> List[Span]:
        """Find critical path (longest duration) through span tree"""

        def find_longest_path(node_id: str, current_path: List[Span]) -> List[Span]:
            children = span_tree.get(node_id, [])

            if not children:
                return current_path

            longest_path = current_path
            max_duration = sum(span.duration_ms or 0 for span in current_path)

            for child in children:
                child_path = find_longest_path(child.span_id, current_path + [child])
                child_duration = sum(span.duration_ms or 0 for span in child_path)

                if child_duration > max_duration:
                    max_duration = child_duration
                    longest_path = child_path

            return longest_path

        # Start from root spans
        root_spans = span_tree.get("root", [])
        if not root_spans:
            return []

        # Find longest path from each root
        longest_overall = []
        max_duration = 0

        for root_span in root_spans:
            path = find_longest_path(root_span.span_id, [root_span])
            path_duration = sum(span.duration_ms or 0 for span in path)

            if path_duration > max_duration:
                max_duration = path_duration
                longest_overall = path

        return longest_overall

    def _generate_optimization_suggestions(self, critical_path: List[Span], bottlenecks: List[Span]) -> List[str]:
        """Generate optimization suggestions based on critical path analysis"""

        suggestions = []

        if not critical_path:
            return suggestions

        # Analyze bottlenecks
        for bottleneck in bottlenecks:
            operation = bottleneck.operation_name.lower()

            if "database" in operation or "query" in operation:
                suggestions.append(f"Optimize database queries in {bottleneck.operation_name}")
                suggestions.append("Consider adding database indexes or query caching")

            elif "http" in operation or "api" in operation:
                suggestions.append(f"Optimize external API calls in {bottleneck.operation_name}")
                suggestions.append("Consider implementing request caching or connection pooling")

            elif "file" in operation or "io" in operation:
                suggestions.append(f"Optimize I/O operations in {bottleneck.operation_name}")
                suggestions.append("Consider async I/O or batch processing")

            else:
                suggestions.append(f"Optimize processing logic in {bottleneck.operation_name}")

        # General suggestions based on critical path
        total_duration = sum(span.duration_ms or 0 for span in critical_path)

        if total_duration > 5000:  # > 5 seconds
            suggestions.append("Consider implementing async processing for long-running operations")
            suggestions.append("Break down large operations into smaller, parallelizable tasks")

        if len(critical_path) > 10:  # Many sequential operations
            suggestions.append("Look for opportunities to parallelize sequential operations")
            suggestions.append("Consider batching multiple operations together")

        return list(set(suggestions))  # Remove duplicates

    def _deserialize_trace(self, trace_data: Dict[str, Any]) -> Trace:
        """Deserialize trace from stored data"""

        # Convert span data back to Span objects
        spans = []
        for span_data in trace_data.get("spans", []):
            # Convert datetime strings back to datetime objects
            span_data["start_time"] = datetime.fromisoformat(span_data["start_time"])
            if span_data.get("end_time"):
                span_data["end_time"] = datetime.fromisoformat(span_data["end_time"])

            spans.append(Span(**span_data))

        # Convert datetime strings
        trace_data["start_time"] = datetime.fromisoformat(trace_data["start_time"])
        trace_data["end_time"] = datetime.fromisoformat(trace_data["end_time"])
        trace_data["spans"] = spans

        return Trace(**trace_data)

    def _start_background_tasks(self):
        """Start background tasks for tracing"""

        # Start trace completion checker
        asyncio.create_task(self._trace_completion_checker())

        # Start metrics aggregation
        asyncio.create_task(self._metrics_aggregation())

    async def _trace_completion_checker(self):
        """Background task to check for completed traces"""

        while True:
            try:
                current_time = datetime.utcnow()

                # Check active traces for completion
                for trace_id in list(self.active_traces.keys()):
                    trace_info = self.active_traces[trace_id]
                    time_since_start = (current_time - trace_info["start_time"]).total_seconds()

                    # Auto-complete old traces
                    if time_since_start > 60:  # 1 minute timeout
                        await self._complete_trace(trace_id)

                await asyncio.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Error in trace completion checker: {e}")
                await asyncio.sleep(30)

    async def _metrics_aggregation(self):
        """Background task for metrics aggregation"""

        while True:
            try:
                # Aggregate operation statistics
                datetime.utcnow()

                # This would push metrics to monitoring system
                for op_name, stats in self.operation_stats.items():
                    if stats["count"] > 0:
                        avg_duration = stats["total_duration"] / stats["count"]
                        error_rate = (stats["error_count"] / stats["count"]) * 100

                        # Log metrics (in real implementation, send to metrics service)
                        logger.debug(f"Operation {op_name}: {avg_duration:.2f}ms avg, {error_rate:.1f}% errors")

                await asyncio.sleep(300)  # Aggregate every 5 minutes

            except Exception as e:
                logger.error(f"Error in metrics aggregation: {e}")
                await asyncio.sleep(300)


# Create singleton instance
tracing_service = None


async def get_tracing_service() -> DistributedTracingService:
    """Get distributed tracing service instance"""
    global tracing_service
    if tracing_service is None:
        # This would be initialized with actual Redis
        tracing_service = DistributedTracingService(None)
    return tracing_service


# Convenience functions for easy tracing
async def trace_operation(operation_name: str, **kwargs):
    """Decorator/context manager for easy operation tracing"""
    service = await get_tracing_service()
    return service.trace_operation(operation_name, **kwargs)


async def add_trace_event(name: str, **attributes):
    """Add event to current trace"""
    service = await get_tracing_service()
    await service.add_span_event(name, attributes)


async def set_trace_attribute(key: str, value: Any):
    """Set attribute on current trace"""
    service = await get_tracing_service()
    await service.set_span_attribute(key, value)
