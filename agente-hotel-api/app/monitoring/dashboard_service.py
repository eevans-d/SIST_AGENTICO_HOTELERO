"""
Custom Dashboard Service
Role-specific dashboards for hotel operations
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class DashboardRole(str, Enum):
    """Dashboard roles for different user types"""
    EXECUTIVE = "executive"
    HOTEL_MANAGER = "hotel_manager"
    FRONT_DESK = "front_desk"
    HOUSEKEEPING = "housekeeping"
    MAINTENANCE = "maintenance"
    REVENUE_MANAGER = "revenue_manager"
    GUEST_RELATIONS = "guest_relations"

class WidgetType(str, Enum):
    """Widget types for dashboard components"""
    KPI_CARD = "kpi_card"
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    TABLE = "table"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    ALERT_LIST = "alert_list"
    STATUS_GRID = "status_grid"

@dataclass
class DashboardWidget:
    """Dashboard widget configuration"""
    id: str
    type: WidgetType
    title: str
    data_source: str
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: int = 60  # seconds
    permissions: List[str] = None

@dataclass
class Dashboard:
    """Dashboard configuration"""
    id: str
    name: str
    role: DashboardRole
    description: str
    widgets: List[DashboardWidget]
    layout: Dict[str, Any]
    auto_refresh: bool = True
    theme: str = "light"

class CustomDashboardService:
    """Service for managing role-specific dashboards"""
    
    def __init__(self, business_metrics_service, redis_client):
        self.business_metrics = business_metrics_service
        self.redis = redis_client
        
        # Dashboard configurations
        self.dashboards = {}
        self.widget_data_cache = {}
        
        # Initialize predefined dashboards
        self._init_dashboards()
    
    def _init_dashboards(self):
        """Initialize predefined role-based dashboards"""
        
        # Executive Dashboard
        self.dashboards[DashboardRole.EXECUTIVE] = Dashboard(
            id="executive_dashboard",
            name="Executive Overview",
            role=DashboardRole.EXECUTIVE,
            description="High-level business performance metrics",
            widgets=[
                DashboardWidget(
                    id="revenue_kpi",
                    type=WidgetType.KPI_CARD,
                    title="Daily Revenue",
                    data_source="daily_revenue",
                    config={
                        "format": "currency",
                        "currency": "EUR",
                        "trend": True,
                        "target": 18000
                    },
                    position={"x": 0, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="occupancy_kpi", 
                    type=WidgetType.KPI_CARD,
                    title="Occupancy Rate",
                    data_source="occupancy_rate",
                    config={
                        "format": "percentage",
                        "trend": True,
                        "target": 80
                    },
                    position={"x": 3, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="adr_kpi",
                    type=WidgetType.KPI_CARD,
                    title="Average Daily Rate",
                    data_source="adr",
                    config={
                        "format": "currency",
                        "currency": "EUR",
                        "trend": True
                    },
                    position={"x": 6, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="nps_kpi",
                    type=WidgetType.KPI_CARD,
                    title="Net Promoter Score",
                    data_source="nps_score",
                    config={
                        "format": "number",
                        "trend": True,
                        "target": 70
                    },
                    position={"x": 9, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="revenue_trend",
                    type=WidgetType.LINE_CHART,
                    title="Revenue Trend (30 Days)",
                    data_source="revenue_trend_30d",
                    config={
                        "x_axis": "date",
                        "y_axis": "revenue",
                        "lines": ["actual", "forecast", "target"]
                    },
                    position={"x": 0, "y": 2, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    id="occupancy_forecast",
                    type=WidgetType.LINE_CHART,
                    title="Occupancy Forecast (14 Days)",
                    data_source="occupancy_forecast_14d",
                    config={
                        "x_axis": "date",
                        "y_axis": "occupancy",
                        "lines": ["actual", "forecast"]
                    },
                    position={"x": 6, "y": 2, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    id="market_segments",
                    type=WidgetType.PIE_CHART,
                    title="Revenue by Market Segment",
                    data_source="market_segment_revenue",
                    config={
                        "value_field": "revenue",
                        "label_field": "segment"
                    },
                    position={"x": 0, "y": 6, "width": 4, "height": 3}
                ),
                DashboardWidget(
                    id="channel_performance",
                    type=WidgetType.BAR_CHART,
                    title="Booking Channel Performance",
                    data_source="channel_performance",
                    config={
                        "x_axis": "channel",
                        "y_axis": "bookings",
                        "color_by": "revenue"
                    },
                    position={"x": 4, "y": 6, "width": 4, "height": 3}
                ),
                DashboardWidget(
                    id="critical_alerts",
                    type=WidgetType.ALERT_LIST,
                    title="Critical Alerts",
                    data_source="critical_alerts",
                    config={
                        "max_items": 5,
                        "severity_filter": ["critical", "high"]
                    },
                    position={"x": 8, "y": 6, "width": 4, "height": 3}
                )
            ],
            layout={
                "columns": 12,
                "row_height": 60,
                "margin": [10, 10],
                "container_padding": [10, 10]
            }
        )
        
        # Hotel Manager Dashboard
        self.dashboards[DashboardRole.HOTEL_MANAGER] = Dashboard(
            id="manager_dashboard",
            name="Hotel Manager Operations",
            role=DashboardRole.HOTEL_MANAGER,
            description="Operational metrics and guest satisfaction",
            widgets=[
                DashboardWidget(
                    id="today_arrivals",
                    type=WidgetType.KPI_CARD,
                    title="Today's Arrivals",
                    data_source="arrivals_today",
                    config={"format": "number"},
                    position={"x": 0, "y": 0, "width": 2, "height": 2}
                ),
                DashboardWidget(
                    id="today_departures",
                    type=WidgetType.KPI_CARD,
                    title="Today's Departures",
                    data_source="departures_today",
                    config={"format": "number"},
                    position={"x": 2, "y": 0, "width": 2, "height": 2}
                ),
                DashboardWidget(
                    id="rooms_ready",
                    type=WidgetType.KPI_CARD,
                    title="Rooms Ready",
                    data_source="rooms_ready",
                    config={"format": "number"},
                    position={"x": 4, "y": 0, "width": 2, "height": 2}
                ),
                DashboardWidget(
                    id="maintenance_pending",
                    type=WidgetType.KPI_CARD,
                    title="Maintenance Pending",
                    data_source="maintenance_pending",
                    config={"format": "number", "alert_threshold": 5},
                    position={"x": 6, "y": 0, "width": 2, "height": 2}
                ),
                DashboardWidget(
                    id="guest_satisfaction",
                    type=WidgetType.GAUGE,
                    title="Guest Satisfaction",
                    data_source="guest_satisfaction_current",
                    config={
                        "min": 0,
                        "max": 10,
                        "thresholds": [6, 8, 9]
                    },
                    position={"x": 8, "y": 0, "width": 4, "height": 3}
                ),
                DashboardWidget(
                    id="room_status_grid",
                    type=WidgetType.STATUS_GRID,
                    title="Room Status Overview",
                    data_source="room_status_all",
                    config={
                        "grid_layout": "floor",
                        "status_colors": {
                            "occupied": "#e74c3c",
                            "vacant_clean": "#27ae60",
                            "vacant_dirty": "#f39c12",
                            "out_of_order": "#8e44ad"
                        }
                    },
                    position={"x": 0, "y": 3, "width": 8, "height": 4}
                ),
                DashboardWidget(
                    id="staff_schedule",
                    type=WidgetType.TABLE,
                    title="Today's Staff Schedule",
                    data_source="staff_schedule_today",
                    config={
                        "columns": ["name", "department", "shift", "status"],
                        "sortable": True
                    },
                    position={"x": 8, "y": 3, "width": 4, "height": 4}
                )
            ],
            layout={
                "columns": 12,
                "row_height": 60,
                "margin": [10, 10],
                "container_padding": [10, 10]
            }
        )
        
        # Front Desk Dashboard
        self.dashboards[DashboardRole.FRONT_DESK] = Dashboard(
            id="frontdesk_dashboard",
            name="Front Desk Operations",
            role=DashboardRole.FRONT_DESK,
            description="Guest services and operational support",
            widgets=[
                DashboardWidget(
                    id="pending_checkins",
                    type=WidgetType.KPI_CARD,
                    title="Pending Check-ins",
                    data_source="pending_checkins",
                    config={"format": "number"},
                    position={"x": 0, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="pending_checkouts",
                    type=WidgetType.KPI_CARD,
                    title="Pending Check-outs",
                    data_source="pending_checkouts",
                    config={"format": "number"},
                    position={"x": 3, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="guest_requests",
                    type=WidgetType.KPI_CARD,
                    title="Open Guest Requests",
                    data_source="open_guest_requests",
                    config={"format": "number", "alert_threshold": 10},
                    position={"x": 6, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="available_rooms_today",
                    type=WidgetType.KPI_CARD,
                    title="Available Rooms",
                    data_source="available_rooms_today",
                    config={"format": "number"},
                    position={"x": 9, "y": 0, "width": 3, "height": 2}
                ),
                DashboardWidget(
                    id="arrivals_timeline",
                    type=WidgetType.BAR_CHART,
                    title="Arrivals by Hour",
                    data_source="arrivals_by_hour",
                    config={
                        "x_axis": "hour",
                        "y_axis": "count",
                        "time_format": "HH:00"
                    },
                    position={"x": 0, "y": 2, "width": 6, "height": 3}
                ),
                DashboardWidget(
                    id="guest_messages",
                    type=WidgetType.TABLE,
                    title="Recent Guest Messages",
                    data_source="recent_guest_messages",
                    config={
                        "columns": ["time", "guest", "room", "message", "status"],
                        "max_rows": 10,
                        "auto_refresh": 30
                    },
                    position={"x": 6, "y": 2, "width": 6, "height": 3}
                ),
                DashboardWidget(
                    id="room_assignments",
                    type=WidgetType.TABLE,
                    title="Room Assignments",
                    data_source="room_assignments_today",
                    config={
                        "columns": ["room", "guest", "checkin", "checkout", "status"],
                        "sortable": True,
                        "filterable": True
                    },
                    position={"x": 0, "y": 5, "width": 12, "height": 4}
                )
            ],
            layout={
                "columns": 12,
                "row_height": 60,
                "margin": [10, 10],
                "container_padding": [10, 10]
            }
        )
        
        # Revenue Manager Dashboard
        self.dashboards[DashboardRole.REVENUE_MANAGER] = Dashboard(
            id="revenue_dashboard",
            name="Revenue Management",
            role=DashboardRole.REVENUE_MANAGER,
            description="Pricing and revenue optimization",
            widgets=[
                DashboardWidget(
                    id="adr_trend",
                    type=WidgetType.LINE_CHART,
                    title="ADR Trend vs Competitor Set",
                    data_source="adr_comparison",
                    config={
                        "x_axis": "date",
                        "y_axis": "adr",
                        "lines": ["our_adr", "comp_set_adr", "market_adr"]
                    },
                    position={"x": 0, "y": 0, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    id="pickup_pace",
                    type=WidgetType.LINE_CHART,
                    title="Booking Pace Analysis",
                    data_source="booking_pace",
                    config={
                        "x_axis": "days_out",
                        "y_axis": "bookings",
                        "lines": ["current_year", "last_year"]
                    },
                    position={"x": 6, "y": 0, "width": 6, "height": 4}
                ),
                DashboardWidget(
                    id="channel_mix",
                    type=WidgetType.PIE_CHART,
                    title="Channel Mix by Revenue",
                    data_source="channel_revenue_mix",
                    config={
                        "value_field": "revenue",
                        "label_field": "channel"
                    },
                    position={"x": 0, "y": 4, "width": 4, "height": 3}
                ),
                DashboardWidget(
                    id="forecast_accuracy",
                    type=WidgetType.GAUGE,
                    title="Forecast Accuracy",
                    data_source="forecast_accuracy",
                    config={
                        "min": 0,
                        "max": 100,
                        "thresholds": [70, 85, 95]
                    },
                    position={"x": 4, "y": 4, "width": 4, "height": 3}
                ),
                DashboardWidget(
                    id="pricing_recommendations",
                    type=WidgetType.TABLE,
                    title="Pricing Recommendations",
                    data_source="pricing_recommendations",
                    config={
                        "columns": ["date", "room_type", "current_rate", "recommended_rate", "reason"],
                        "highlight_changes": True
                    },
                    position={"x": 8, "y": 4, "width": 4, "height": 3}
                )
            ],
            layout={
                "columns": 12,
                "row_height": 60,
                "margin": [10, 10],
                "container_padding": [10, 10]
            }
        )

    async def get_dashboard(self, role: DashboardRole, user_id: str = None) -> Dict[str, Any]:
        """Get dashboard configuration and data for role"""
        
        if role not in self.dashboards:
            raise ValueError(f"Dashboard not found for role: {role}")
        
        dashboard = self.dashboards[role]
        
        # Get widget data
        dashboard_data = {
            "id": dashboard.id,
            "name": dashboard.name,
            "role": dashboard.role,
            "description": dashboard.description,
            "layout": dashboard.layout,
            "auto_refresh": dashboard.auto_refresh,
            "theme": dashboard.theme,
            "widgets": []
        }
        
        for widget in dashboard.widgets:
            widget_data = await self._get_widget_data(widget)
            dashboard_data["widgets"].append({
                "id": widget.id,
                "type": widget.type,
                "title": widget.title,
                "position": widget.position,
                "config": widget.config,
                "data": widget_data,
                "refresh_interval": widget.refresh_interval,
                "last_updated": datetime.utcnow().isoformat()
            })
        
        return dashboard_data

    async def get_widget_data(self, widget_id: str, role: DashboardRole = None) -> Dict[str, Any]:
        """Get data for a specific widget"""
        
        # Find widget in dashboards
        widget = None
        if role and role in self.dashboards:
            for w in self.dashboards[role].widgets:
                if w.id == widget_id:
                    widget = w
                    break
        else:
            # Search all dashboards
            for dashboard in self.dashboards.values():
                for w in dashboard.widgets:
                    if w.id == widget_id:
                        widget = w
                        break
                if widget:
                    break
        
        if not widget:
            raise ValueError(f"Widget not found: {widget_id}")
        
        return await self._get_widget_data(widget)

    async def _get_widget_data(self, widget: DashboardWidget) -> Dict[str, Any]:
        """Get data for widget based on its data source"""
        
        # Check cache first
        cache_key = f"widget_data:{widget.id}"
        cached_data = await self._get_cached_widget_data(cache_key)
        if cached_data:
            return cached_data
        
        try:
            data_source = widget.data_source
            widget_data = {}
            
            # Get data based on data source
            if data_source == "daily_revenue":
                widget_data = await self._get_daily_revenue_data()
            elif data_source == "occupancy_rate":
                widget_data = await self._get_occupancy_data()
            elif data_source == "adr":
                widget_data = await self._get_adr_data()
            elif data_source == "nps_score":
                widget_data = await self._get_nps_data()
            elif data_source == "revenue_trend_30d":
                widget_data = await self._get_revenue_trend_data(30)
            elif data_source == "occupancy_forecast_14d":
                widget_data = await self._get_occupancy_forecast_data(14)
            elif data_source == "market_segment_revenue":
                widget_data = await self._get_market_segment_data()
            elif data_source == "channel_performance":
                widget_data = await self._get_channel_performance_data()
            elif data_source == "critical_alerts":
                widget_data = await self._get_critical_alerts_data()
            elif data_source == "arrivals_today":
                widget_data = await self._get_arrivals_today_data()
            elif data_source == "departures_today":
                widget_data = await self._get_departures_today_data()
            elif data_source == "rooms_ready":
                widget_data = await self._get_rooms_ready_data()
            elif data_source == "maintenance_pending":
                widget_data = await self._get_maintenance_pending_data()
            elif data_source == "guest_satisfaction_current":
                widget_data = await self._get_guest_satisfaction_data()
            elif data_source == "room_status_all":
                widget_data = await self._get_room_status_data()
            elif data_source == "staff_schedule_today":
                widget_data = await self._get_staff_schedule_data()
            elif data_source == "pending_checkins":
                widget_data = await self._get_pending_checkins_data()
            elif data_source == "pending_checkouts":
                widget_data = await self._get_pending_checkouts_data()
            elif data_source == "open_guest_requests":
                widget_data = await self._get_guest_requests_data()
            elif data_source == "available_rooms_today":
                widget_data = await self._get_available_rooms_data()
            elif data_source == "arrivals_by_hour":
                widget_data = await self._get_arrivals_by_hour_data()
            elif data_source == "recent_guest_messages":
                widget_data = await self._get_recent_messages_data()
            elif data_source == "room_assignments_today":
                widget_data = await self._get_room_assignments_data()
            else:
                widget_data = {"error": f"Unknown data source: {data_source}"}
            
            # Cache the data
            await self._cache_widget_data(cache_key, widget_data, widget.refresh_interval)
            
            return widget_data
            
        except Exception as e:
            logger.error(f"Error getting widget data for {widget.id}: {e}")
            return {"error": str(e)}

    async def create_custom_dashboard(self, dashboard_config: Dict[str, Any]) -> str:
        """Create a custom dashboard"""
        
        dashboard_id = dashboard_config.get("id", f"custom_{int(datetime.utcnow().timestamp())}")
        
        widgets = []
        for widget_config in dashboard_config.get("widgets", []):
            widget = DashboardWidget(
                id=widget_config["id"],
                type=WidgetType(widget_config["type"]),
                title=widget_config["title"],
                data_source=widget_config["data_source"],
                config=widget_config.get("config", {}),
                position=widget_config["position"],
                refresh_interval=widget_config.get("refresh_interval", 60)
            )
            widgets.append(widget)
        
        dashboard = Dashboard(
            id=dashboard_id,
            name=dashboard_config["name"],
            role=DashboardRole(dashboard_config.get("role", "custom")),
            description=dashboard_config.get("description", ""),
            widgets=widgets,
            layout=dashboard_config.get("layout", {}),
            auto_refresh=dashboard_config.get("auto_refresh", True),
            theme=dashboard_config.get("theme", "light")
        )
        
        # Store custom dashboard
        await self._store_custom_dashboard(dashboard)
        
        return dashboard_id

    async def _get_cached_widget_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached widget data"""
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Error getting cached widget data: {e}")
        return None

    async def _cache_widget_data(self, cache_key: str, data: Dict[str, Any], ttl: int):
        """Cache widget data"""
        try:
            await self.redis.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.warning(f"Error caching widget data: {e}")

    # Data source methods (these would connect to actual data)
    async def _get_daily_revenue_data(self) -> Dict[str, Any]:
        """Get daily revenue data"""
        # This would get actual revenue data
        return {
            "value": 15750.00,
            "trend": 8.5,
            "target": 18000.00,
            "previous_period": 14500.00
        }

    async def _get_occupancy_data(self) -> Dict[str, Any]:
        """Get occupancy data"""
        return {
            "value": 78.5,
            "trend": 5.2,
            "target": 80.0,
            "previous_period": 74.6
        }

    async def _get_adr_data(self) -> Dict[str, Any]:
        """Get ADR data"""
        return {
            "value": 185.50,
            "trend": 3.8,
            "target": 190.00,
            "previous_period": 178.75
        }

    async def _get_nps_data(self) -> Dict[str, Any]:
        """Get NPS data"""
        return {
            "value": 67.0,
            "trend": -2.1,
            "target": 70.0,
            "previous_period": 68.5
        }

    async def _get_revenue_trend_data(self, days: int) -> Dict[str, Any]:
        """Get revenue trend data"""
        # This would generate actual trend data
        dates = [(datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days, 0, -1)]
        actual = [14000 + (i * 100) + (i % 7 * 500) for i in range(len(dates))]
        forecast = [actual[-1] + (i * 150) for i in range(1, 8)]
        target = [16000] * len(dates)
        
        return {
            "dates": dates,
            "series": {
                "actual": actual,
                "forecast": forecast[:len(dates)],
                "target": target
            }
        }

    async def _get_occupancy_forecast_data(self, days: int) -> Dict[str, Any]:
        """Get occupancy forecast data"""
        dates = [(datetime.utcnow() + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
        actual = [75 + (i % 7 * 5) for i in range(7)]
        forecast = [78 + (i % 5 * 3) for i in range(days)]
        
        return {
            "dates": dates,
            "series": {
                "actual": actual + [None] * (days - len(actual)),
                "forecast": [None] * len(actual) + forecast[len(actual):]
            }
        }

    async def _get_market_segment_data(self) -> Dict[str, Any]:
        """Get market segment revenue data"""
        return {
            "segments": [
                {"segment": "Corporate", "revenue": 4500, "percentage": 30},
                {"segment": "Leisure", "revenue": 6750, "percentage": 45},
                {"segment": "Group", "revenue": 2250, "percentage": 15},
                {"segment": "Government", "revenue": 1500, "percentage": 10}
            ]
        }

    async def _get_channel_performance_data(self) -> Dict[str, Any]:
        """Get booking channel performance data"""
        return {
            "channels": [
                {"channel": "Direct", "bookings": 45, "revenue": 8100},
                {"channel": "OTA", "bookings": 35, "revenue": 5250},
                {"channel": "Corporate", "bookings": 15, "revenue": 2700},
                {"channel": "Travel Agent", "bookings": 8, "revenue": 1200}
            ]
        }

    async def _get_critical_alerts_data(self) -> Dict[str, Any]:
        """Get critical alerts data"""
        return {
            "alerts": [
                {
                    "id": "alert_1",
                    "severity": "critical",
                    "message": "Occupancy below 70% for weekend",
                    "timestamp": "2024-01-15T14:30:00Z",
                    "category": "revenue"
                },
                {
                    "id": "alert_2",
                    "severity": "high",
                    "message": "Maintenance backlog exceeding SLA",
                    "timestamp": "2024-01-15T13:45:00Z",
                    "category": "operations"
                }
            ]
        }

    async def _get_arrivals_today_data(self) -> Dict[str, Any]:
        """Get today's arrivals data"""
        return {"value": 42}

    async def _get_departures_today_data(self) -> Dict[str, Any]:
        """Get today's departures data"""
        return {"value": 38}

    async def _get_rooms_ready_data(self) -> Dict[str, Any]:
        """Get rooms ready data"""
        return {"value": 85}

    async def _get_maintenance_pending_data(self) -> Dict[str, Any]:
        """Get maintenance pending data"""
        return {"value": 7}

    async def _get_guest_satisfaction_data(self) -> Dict[str, Any]:
        """Get guest satisfaction data"""
        return {
            "value": 8.7,
            "max": 10,
            "min": 0,
            "threshold_good": 8.0,
            "threshold_excellent": 9.0
        }

    async def _get_room_status_data(self) -> Dict[str, Any]:
        """Get room status grid data"""
        # This would return actual room status for all rooms
        return {
            "rooms": [
                {"room": "101", "status": "occupied", "floor": 1},
                {"room": "102", "status": "vacant_clean", "floor": 1},
                {"room": "103", "status": "vacant_dirty", "floor": 1},
                # ... more rooms
            ],
            "summary": {
                "occupied": 65,
                "vacant_clean": 25,
                "vacant_dirty": 8,
                "out_of_order": 2
            }
        }

    async def _get_staff_schedule_data(self) -> Dict[str, Any]:
        """Get staff schedule data"""
        return {
            "staff": [
                {"name": "Maria Garcia", "department": "Front Desk", "shift": "Morning", "status": "On Duty"},
                {"name": "Carlos Lopez", "department": "Housekeeping", "shift": "Day", "status": "On Duty"},
                {"name": "Ana Martinez", "department": "Maintenance", "shift": "Day", "status": "Break"},
                # ... more staff
            ]
        }

    async def _get_pending_checkins_data(self) -> Dict[str, Any]:
        """Get pending check-ins data"""
        return {"value": 15}

    async def _get_pending_checkouts_data(self) -> Dict[str, Any]:
        """Get pending check-outs data"""
        return {"value": 23}

    async def _get_guest_requests_data(self) -> Dict[str, Any]:
        """Get open guest requests data"""
        return {"value": 8}

    async def _get_available_rooms_data(self) -> Dict[str, Any]:
        """Get available rooms data"""
        return {"value": 33}

    async def _get_arrivals_by_hour_data(self) -> Dict[str, Any]:
        """Get arrivals by hour data"""
        return {
            "hours": ["14:00", "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"],
            "counts": [5, 12, 18, 15, 8, 3, 1]
        }

    async def _get_recent_messages_data(self) -> Dict[str, Any]:
        """Get recent guest messages data"""
        return {
            "messages": [
                {
                    "time": "14:30",
                    "guest": "Smith, J.",
                    "room": "205",
                    "message": "Extra towels needed",
                    "status": "Pending"
                },
                {
                    "time": "14:15",
                    "guest": "Garcia, M.",
                    "room": "312",
                    "message": "Restaurant reservation",
                    "status": "Completed"
                }
                # ... more messages
            ]
        }

    async def _get_room_assignments_data(self) -> Dict[str, Any]:
        """Get room assignments data"""
        return {
            "assignments": [
                {
                    "room": "101",
                    "guest": "Johnson, R.",
                    "checkin": "2024-01-15",
                    "checkout": "2024-01-17",
                    "status": "Confirmed"
                },
                {
                    "room": "102",
                    "guest": "Brown, S.",
                    "checkin": "2024-01-15",
                    "checkout": "2024-01-16",
                    "status": "Checked In"
                }
                # ... more assignments
            ]
        }

    async def _store_custom_dashboard(self, dashboard: Dashboard):
        """Store custom dashboard configuration"""
        dashboard_key = f"dashboard:{dashboard.id}"
        dashboard_data = {
            "id": dashboard.id,
            "name": dashboard.name,
            "role": dashboard.role,
            "description": dashboard.description,
            "widgets": [asdict(w) for w in dashboard.widgets],
            "layout": dashboard.layout,
            "auto_refresh": dashboard.auto_refresh,
            "theme": dashboard.theme,
            "created_at": datetime.utcnow().isoformat()
        }
        
        await self.redis.set(
            dashboard_key,
            json.dumps(dashboard_data, default=str)
        )

# Create singleton instance
dashboard_service = None

async def get_dashboard_service() -> CustomDashboardService:
    """Get dashboard service instance"""
    global dashboard_service
    if dashboard_service is None:
        # This would be initialized with actual business metrics and Redis
        dashboard_service = CustomDashboardService(None, None)
    return dashboard_service