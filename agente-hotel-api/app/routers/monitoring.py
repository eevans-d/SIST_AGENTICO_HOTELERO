"""
Monitoring API Router
Comprehensive monitoring endpoints for business intelligence and system observability
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from app.monitoring.business_metrics import get_business_metrics_service
from app.monitoring.dashboard_service import get_dashboard_service
from app.monitoring.alerting_service import get_alerting_service, AlertCategory, AlertSeverity
from app.monitoring.performance_service import get_performance_service, PerformanceStatus
from app.monitoring.health_service import get_health_service, CheckType, HealthStatus
from app.monitoring.tracing_service import get_tracing_service, SpanStatus
from app.core.settings import get_settings

router = APIRouter(prefix="/monitoring", tags=["monitoring"])
settings = get_settings()

class TimeRange(str, Enum):
    """Time range options"""
    HOUR = "1h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"

# Business Metrics Endpoints
@router.get("/business/metrics")
async def get_business_metrics(
    time_range: TimeRange = TimeRange.DAY,
    include_forecasts: bool = False,
    metrics_service = Depends(get_business_metrics_service)
):
    """Get comprehensive business metrics"""
    
    try:
        hours = {
            TimeRange.HOUR: 1,
            TimeRange.DAY: 24,
            TimeRange.WEEK: 168,
            TimeRange.MONTH: 720
        }[time_range]
        
        metrics = await metrics_service.get_business_metrics(hours=hours)
        
        if include_forecasts:
            forecasts = await metrics_service.get_forecasts()
            metrics["forecasts"] = forecasts
        
        return {
            "status": "success",
            "data": metrics,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving business metrics: {str(e)}")

@router.get("/business/kpis")
async def get_key_performance_indicators(
    time_range: TimeRange = TimeRange.DAY,
    metrics_service = Depends(get_business_metrics_service)
):
    """Get key performance indicators"""
    
    try:
        hours = {
            TimeRange.HOUR: 1,
            TimeRange.DAY: 24,
            TimeRange.WEEK: 168,
            TimeRange.MONTH: 720
        }[time_range]
        
        kpis = await metrics_service.calculate_kpis(hours=hours)
        
        return {
            "status": "success",
            "data": kpis,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving KPIs: {str(e)}")

@router.get("/business/alerts")
async def get_business_alerts(
    metrics_service = Depends(get_business_metrics_service)
):
    """Get business metric alerts"""
    
    try:
        alerts = await metrics_service.check_business_alerts()
        
        return {
            "status": "success",
            "data": alerts,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving business alerts: {str(e)}")

# Dashboard Endpoints
@router.get("/dashboards")
async def list_dashboards(
    dashboard_service = Depends(get_dashboard_service)
):
    """List available dashboards"""
    
    try:
        dashboards = await dashboard_service.list_dashboards()
        
        return {
            "status": "success",
            "data": dashboards,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing dashboards: {str(e)}")

@router.get("/dashboards/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    time_range: TimeRange = TimeRange.DAY,
    refresh: bool = False,
    dashboard_service = Depends(get_dashboard_service)
):
    """Get dashboard data"""
    
    try:
        hours = {
            TimeRange.HOUR: 1,
            TimeRange.DAY: 24,
            TimeRange.WEEK: 168,
            TimeRange.MONTH: 720
        }[time_range]
        
        dashboard_data = await dashboard_service.get_dashboard_data(
            dashboard_id=dashboard_id,
            time_range_hours=hours,
            force_refresh=refresh
        )
        
        return {
            "status": "success",
            "data": dashboard_data,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dashboard: {str(e)}")

@router.post("/dashboards/{dashboard_id}/widgets")
async def add_dashboard_widget(
    dashboard_id: str,
    widget_config: Dict[str, Any],
    dashboard_service = Depends(get_dashboard_service)
):
    """Add widget to dashboard"""
    
    try:
        widget = await dashboard_service.add_widget(dashboard_id, widget_config)
        
        return {
            "status": "success",
            "data": widget,
            "message": "Widget added successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding widget: {str(e)}")

@router.get("/dashboards/executive/summary")
async def get_executive_summary(
    time_range: TimeRange = TimeRange.DAY,
    dashboard_service = Depends(get_dashboard_service)
):
    """Get executive summary dashboard"""
    
    try:
        hours = {
            TimeRange.HOUR: 1,
            TimeRange.DAY: 24,
            TimeRange.WEEK: 168,
            TimeRange.MONTH: 720
        }[time_range]
        
        summary = await dashboard_service.get_executive_dashboard(time_range_hours=hours)
        
        return {
            "status": "success",
            "data": summary,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving executive summary: {str(e)}")

# Alert Management Endpoints
@router.get("/alerts")
async def get_alerts(
    category: Optional[AlertCategory] = None,
    severity: Optional[AlertSeverity] = None,
    status: Optional[str] = None,
    alerting_service = Depends(get_alerting_service)
):
    """Get active alerts with optional filtering"""
    
    try:
        alerts = await alerting_service.get_active_alerts(
            category=category,
            severity=severity
        )
        
        # Filter by status if provided
        if status:
            alerts = [alert for alert in alerts if alert.status == status]
        
        return {
            "status": "success",
            "data": [
                {
                    "id": alert.id,
                    "title": alert.title,
                    "description": alert.description,
                    "severity": alert.severity,
                    "category": alert.category,
                    "status": alert.status,
                    "current_value": alert.current_value,
                    "threshold": alert.threshold,
                    "created_at": alert.created_at.isoformat(),
                    "escalation_level": alert.escalation_level
                }
                for alert in alerts
            ],
            "total_count": len(alerts),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    user_id: str,
    comment: Optional[str] = None,
    alerting_service = Depends(get_alerting_service)
):
    """Acknowledge an alert"""
    
    try:
        await alerting_service.acknowledge_alert(
            alert_id=alert_id,
            user_id=user_id,
            comment=comment
        )
        
        return {
            "status": "success",
            "message": f"Alert {alert_id} acknowledged by {user_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error acknowledging alert: {str(e)}")

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    user_id: str,
    comment: Optional[str] = None,
    alerting_service = Depends(get_alerting_service)
):
    """Resolve an alert"""
    
    try:
        await alerting_service.resolve_alert(
            alert_id=alert_id,
            user_id=user_id,
            comment=comment
        )
        
        return {
            "status": "success",
            "message": f"Alert {alert_id} resolved by {user_id}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving alert: {str(e)}")

@router.get("/alerts/statistics")
async def get_alert_statistics(
    days: int = Query(7, ge=1, le=30),
    alerting_service = Depends(get_alerting_service)
):
    """Get alert statistics"""
    
    try:
        stats = await alerting_service.get_alert_statistics(days=days)
        
        return {
            "status": "success",
            "data": stats,
            "period_days": days,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving alert statistics: {str(e)}")

# Performance Monitoring Endpoints
@router.get("/performance")
async def get_performance_report(
    hours: int = Query(24, ge=1, le=168),
    performance_service = Depends(get_performance_service)
):
    """Get performance analysis report"""
    
    try:
        report = await performance_service.analyze_performance(hours=hours)
        
        return {
            "status": "success",
            "data": {
                "overall_status": report.overall_status,
                "performance_score": report.performance_score,
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "metric_summaries": report.metric_summaries,
                "recommendations": [
                    {
                        "id": rec.id,
                        "type": rec.type,
                        "title": rec.title,
                        "description": rec.description,
                        "priority": rec.priority,
                        "impact_estimate": rec.impact_estimate,
                        "effort_estimate": rec.effort_estimate
                    }
                    for rec in report.recommendations
                ],
                "trends": report.trends,
                "alerts_triggered": report.alerts_triggered
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance report: {str(e)}")

@router.get("/performance/realtime")
async def get_realtime_performance(
    performance_service = Depends(get_performance_service)
):
    """Get real-time performance metrics"""
    
    try:
        metrics = await performance_service.get_real_time_metrics()
        
        return {
            "status": "success",
            "data": {
                metric_name: {
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "percentiles": metric.percentiles,
                    "trend": metric.trend
                }
                for metric_name, metric in metrics.items()
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving real-time metrics: {str(e)}")

@router.get("/performance/insights/{metric_name}")
async def get_performance_insights(
    metric_name: str,
    hours: int = Query(24, ge=1, le=168),
    performance_service = Depends(get_performance_service)
):
    """Get detailed insights for specific metric"""
    
    try:
        insights = await performance_service.get_performance_insights(
            metric_name=metric_name,
            hours=hours
        )
        
        return {
            "status": "success",
            "data": insights,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving performance insights: {str(e)}")

@router.post("/performance/optimize/{recommendation_id}")
async def apply_optimization(
    recommendation_id: str,
    background_tasks: BackgroundTasks,
    performance_service = Depends(get_performance_service)
):
    """Apply performance optimization recommendation"""
    
    try:
        # Apply optimization in background
        background_tasks.add_task(
            performance_service.optimize_performance,
            recommendation_id
        )
        
        return {
            "status": "success",
            "message": f"Optimization {recommendation_id} is being applied",
            "estimated_completion": "5-10 minutes"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying optimization: {str(e)}")

# Health Check Endpoints
@router.get("/health")
async def get_system_health(
    check_types: Optional[List[CheckType]] = Query(None),
    health_service = Depends(get_health_service)
):
    """Get comprehensive system health check"""
    
    try:
        health = await health_service.check_health(check_types=check_types)
        
        return {
            "status": "success",
            "data": {
                "overall_status": health.overall_status,
                "last_updated": health.last_updated.isoformat(),
                "components": {
                    name: {
                        "status": result.status,
                        "check_type": result.check_type,
                        "duration_ms": result.duration_ms,
                        "message": result.message,
                        "error": result.error
                    }
                    for name, result in health.components.items()
                },
                "dependencies": {
                    name: {
                        "status": dep.status,
                        "type": dep.type,
                        "response_time_ms": dep.response_time_ms,
                        "success_rate": dep.success_rate,
                        "error_count": dep.error_count
                    }
                    for name, dep in health.dependencies.items()
                },
                "system_metrics": health.system_metrics,
                "business_metrics": health.business_metrics,
                "performance_indicators": health.performance_indicators,
                "alerts_active": health.alerts_active
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving system health: {str(e)}")

@router.get("/health/liveness")
async def check_liveness(
    health_service = Depends(get_health_service)
):
    """Simple liveness check"""
    
    try:
        result = await health_service.check_liveness()
        
        status_code = 200 if result.status == HealthStatus.HEALTHY else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": result.status,
                "message": result.message,
                "timestamp": result.timestamp.isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": f"Liveness check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/health/readiness")
async def check_readiness(
    health_service = Depends(get_health_service)
):
    """Comprehensive readiness check"""
    
    try:
        result = await health_service.check_readiness()
        
        status_code = 200 if result.status == HealthStatus.HEALTHY else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": result.status,
                "message": result.message,
                "duration_ms": result.duration_ms,
                "details": result.details,
                "timestamp": result.timestamp.isoformat()
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "message": f"Readiness check failed: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/health/dependencies")
async def get_dependency_health(
    dependency_name: Optional[str] = None,
    health_service = Depends(get_health_service)
):
    """Get dependency health status"""
    
    try:
        dependencies = await health_service.get_dependency_health(dependency_name)
        
        return {
            "status": "success",
            "data": {
                name: {
                    "status": dep.status,
                    "type": dep.type,
                    "endpoint": dep.endpoint,
                    "last_check": dep.last_check.isoformat(),
                    "response_time_ms": dep.response_time_ms,
                    "success_rate": dep.success_rate,
                    "error_count": dep.error_count
                }
                for name, dep in dependencies.items()
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving dependency health: {str(e)}")

@router.get("/health/diagnose")
async def diagnose_issues(
    health_service = Depends(get_health_service)
):
    """Get intelligent issue diagnosis"""
    
    try:
        diagnosis = await health_service.diagnose_issues()
        
        return {
            "status": "success",
            "data": diagnosis,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing diagnosis: {str(e)}")

# Distributed Tracing Endpoints
@router.get("/traces")
async def get_traces(
    service_name: Optional[str] = None,
    operation_name: Optional[str] = None,
    status: Optional[SpanStatus] = None,
    min_duration_ms: Optional[float] = None,
    hours: int = Query(24, ge=1, le=168),
    tracing_service = Depends(get_tracing_service)
):
    """Get traces with filtering"""
    
    try:
        traces = await tracing_service.get_traces(
            service_name=service_name,
            operation_name=operation_name,
            status=status,
            min_duration_ms=min_duration_ms,
            hours=hours
        )
        
        return {
            "status": "success",
            "data": [
                {
                    "trace_id": trace.trace_id,
                    "start_time": trace.start_time.isoformat(),
                    "end_time": trace.end_time.isoformat(),
                    "duration_ms": trace.duration_ms,
                    "span_count": trace.span_count,
                    "error_count": trace.error_count,
                    "root_operation": trace.root_operation,
                    "service_map": trace.service_map
                }
                for trace in traces
            ],
            "total_count": len(traces),
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving traces: {str(e)}")

@router.get("/traces/{trace_id}")
async def get_trace_details(
    trace_id: str,
    tracing_service = Depends(get_tracing_service)
):
    """Get detailed trace information"""
    
    try:
        trace = await tracing_service.get_trace(trace_id)
        
        if not trace:
            raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")
        
        return {
            "status": "success",
            "data": {
                "trace_id": trace.trace_id,
                "start_time": trace.start_time.isoformat(),
                "end_time": trace.end_time.isoformat(),
                "duration_ms": trace.duration_ms,
                "span_count": trace.span_count,
                "error_count": trace.error_count,
                "root_operation": trace.root_operation,
                "service_map": trace.service_map,
                "spans": [
                    {
                        "span_id": span.span_id,
                        "parent_span_id": span.parent_span_id,
                        "operation_name": span.operation_name,
                        "service_name": span.service_name,
                        "span_kind": span.span_kind,
                        "start_time": span.start_time.isoformat(),
                        "end_time": span.end_time.isoformat() if span.end_time else None,
                        "duration_ms": span.duration_ms,
                        "status": span.status,
                        "tags": span.tags,
                        "attributes": span.attributes,
                        "events": [
                            {
                                "name": event.name,
                                "timestamp": event.timestamp.isoformat(),
                                "attributes": event.attributes
                            }
                            for event in span.events
                        ]
                    }
                    for span in trace.spans
                ]
            },
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving trace details: {str(e)}")

@router.get("/traces/{trace_id}/critical-path")
async def get_critical_path_analysis(
    trace_id: str,
    tracing_service = Depends(get_tracing_service)
):
    """Get critical path analysis for a trace"""
    
    try:
        analysis = await tracing_service.get_critical_path_analysis(trace_id)
        
        return {
            "status": "success",
            "data": analysis,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error performing critical path analysis: {str(e)}")

@router.get("/traces/analytics/operations")
async def get_operation_analytics(
    hours: int = Query(24, ge=1, le=168),
    tracing_service = Depends(get_tracing_service)
):
    """Get operation performance analytics"""
    
    try:
        analytics = await tracing_service.get_operation_analytics(hours=hours)
        
        return {
            "status": "success",
            "data": analytics,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving operation analytics: {str(e)}")

@router.get("/traces/analytics/service-map")
async def get_service_map(
    hours: int = Query(24, ge=1, le=168),
    tracing_service = Depends(get_tracing_service)
):
    """Get service dependency map"""
    
    try:
        service_map = await tracing_service.get_service_map(hours=hours)
        
        return {
            "status": "success",
            "data": service_map,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving service map: {str(e)}")

@router.post("/traces/search")
async def search_traces(
    query: Dict[str, Any],
    tracing_service = Depends(get_tracing_service)
):
    """Search traces with complex query"""
    
    try:
        traces = await tracing_service.search_traces(query)
        
        return {
            "status": "success",
            "data": [
                {
                    "trace_id": trace.trace_id,
                    "start_time": trace.start_time.isoformat(),
                    "duration_ms": trace.duration_ms,
                    "span_count": trace.span_count,
                    "error_count": trace.error_count,
                    "root_operation": trace.root_operation
                }
                for trace in traces
            ],
            "total_count": len(traces),
            "query": query,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching traces: {str(e)}")

# System Overview Endpoint
@router.get("/overview")
async def get_monitoring_overview(
    time_range: TimeRange = TimeRange.DAY,
    business_service = Depends(get_business_metrics_service),
    dashboard_service = Depends(get_dashboard_service),
    alerting_service = Depends(get_alerting_service),
    performance_service = Depends(get_performance_service),
    health_service = Depends(get_health_service)
):
    """Get comprehensive monitoring overview"""
    
    try:
        hours = {
            TimeRange.HOUR: 1,
            TimeRange.DAY: 24,
            TimeRange.WEEK: 168,
            TimeRange.MONTH: 720
        }[time_range]
        
        # Get key metrics from each service
        business_metrics = await business_service.get_business_metrics(hours=hours)
        active_alerts = await alerting_service.get_active_alerts()
        performance_report = await performance_service.analyze_performance(hours=hours)
        system_health = await health_service.check_health()
        
        # Build overview
        overview = {
            "system_status": {
                "overall_health": system_health.overall_status,
                "performance_score": performance_report.performance_score,
                "active_alerts": len(active_alerts),
                "critical_alerts": len([a for a in active_alerts if a.severity == "critical"])
            },
            "business_summary": {
                "occupancy_rate": business_metrics.get("occupancy_rate", 0),
                "revenue_today": business_metrics.get("revenue_today", 0),
                "guest_satisfaction": business_metrics.get("guest_satisfaction_score", 0),
                "active_reservations": business_metrics.get("active_reservations", 0)
            },
            "performance_summary": {
                "api_response_time_p95": performance_report.metric_summaries.get("api_response_time_p95", {}).get("p95", 0),
                "error_rate": performance_report.metric_summaries.get("api_error_rate", {}).get("mean", 0),
                "throughput": performance_report.metric_summaries.get("api_throughput", {}).get("mean", 0)
            },
            "system_resources": {
                "cpu_usage": system_health.system_metrics.get("cpu_percent", 0),
                "memory_usage": system_health.system_metrics.get("memory_percent", 0),
                "disk_usage": system_health.system_metrics.get("disk_percent", 0)
            },
            "recent_trends": performance_report.trends,
            "top_recommendations": [
                {
                    "title": rec.title,
                    "priority": rec.priority,
                    "impact": rec.impact_estimate
                }
                for rec in performance_report.recommendations[:3]
            ]
        }
        
        return {
            "status": "success",
            "data": overview,
            "time_range": time_range,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving monitoring overview: {str(e)}")

# Export endpoint for external monitoring tools
@router.get("/export/prometheus")
async def export_prometheus_metrics():
    """Export metrics in Prometheus format"""
    
    try:
        # This would export all metrics in Prometheus format
        # For now, return a simple response
        metrics_text = """
# HELP hotel_agent_info Information about the hotel agent system
# TYPE hotel_agent_info gauge
hotel_agent_info{version="1.0.0",service="agente-hotel-api"} 1

# HELP hotel_occupancy_rate Current hotel occupancy rate
# TYPE hotel_occupancy_rate gauge
hotel_occupancy_rate 78.5

# HELP hotel_reservations_total Total number of reservations
# TYPE hotel_reservations_total counter
hotel_reservations_total 1247

# HELP api_response_time_seconds API response time in seconds
# TYPE api_response_time_seconds histogram
api_response_time_seconds_bucket{le="0.1"} 892
api_response_time_seconds_bucket{le="0.5"} 1205
api_response_time_seconds_bucket{le="1.0"} 1247
api_response_time_seconds_bucket{le="+Inf"} 1247
api_response_time_seconds_sum 245.6
api_response_time_seconds_count 1247
        """.strip()
        
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting metrics: {str(e)}")

from fastapi.responses import Response