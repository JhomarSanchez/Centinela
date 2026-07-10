import type { components } from "./generated/openapi";

export type SessionRead = components["schemas"]["SessionRead"];
export type DashboardSummary = components["schemas"]["DashboardSummaryRead"];
export type Service = components["schemas"]["ServiceSummary"];
export type ServiceRead = components["schemas"]["ServiceRead"];
export type ServiceCreate = components["schemas"]["ServiceCreate"];
export type ServiceUpdate = components["schemas"]["ServiceUpdate"];
export type Check = components["schemas"]["CheckRead"];
export type Timeline = components["schemas"]["ServiceTimelineRead"];
export type TimelinePoint = components["schemas"]["TimelinePoint"];
export type Incident = components["schemas"]["IncidentRead"];
export type IncidentDetail = components["schemas"]["IncidentDetailRead"];
export type IncidentContext = components["schemas"]["IncidentContextRead"];
export type AISettings = components["schemas"]["AISettingsRead"];
export type AISettingsUpdate = components["schemas"]["AISettingsUpdate"];
export type AIProviderTest = components["schemas"]["AIProviderTestRead"];
