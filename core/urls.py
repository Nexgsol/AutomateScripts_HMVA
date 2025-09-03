from django.urls import path
from .views import (
  script_form, request_detail, ScriptGenerateAPI, ScriptGetAPI,
  RenderAvatarAPI, AssembleAPI, DriveAPI, CaptionsAPI, AirtableSyncAPI,
  ScheduleAPI, PublishAPI, MetricsAPI
)

urlpatterns = [
    path("", script_form, name="script-form"),
    path("r/<int:pk>/", request_detail, name="request-detail"),
    path("v1/requests/", ScriptGenerateAPI.as_view()),
    path("v1/requests/<int:pk>/", ScriptGetAPI.as_view()),
    path("v1/requests/<int:pk>/render", RenderAvatarAPI.as_view()),
    path("v1/requests/<int:pk>/assemble", AssembleAPI.as_view()),
    path("v1/requests/<int:pk>/drive", DriveAPI.as_view()),
    path("v1/requests/<int:pk>/captions", CaptionsAPI.as_view()),
    path("v1/requests/<int:pk>/airtable", AirtableSyncAPI.as_view()),
    path("v1/requests/<int:pk>/schedule", ScheduleAPI.as_view()),
    path("v1/requests/<int:pk>/publish", PublishAPI.as_view()),
    path("v1/requests/<int:pk>/metrics24h", MetricsAPI.as_view()),
]
