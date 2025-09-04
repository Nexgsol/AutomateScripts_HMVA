from django.urls import path
from .views import (
  script_avatar_page, script_avatar_page, script_form, ParagraphAPI
)

urlpatterns = [
    path("", script_form, name="script-form"),
    # path("r/<int:pk>/", request_detail, name="request-detail"),
    # path("v1/requests/", ScriptGenerateAPI.as_view()),
    # path("v1/requests/<int:pk>/", ScriptGetAPI.as_view()),
    # path("v1/requests/<int:pk>/render", RenderAvatarAPI.as_view()),
    # path("v1/requests/<int:pk>/assemble", AssembleAPI.as_view()),
    # path("v1/requests/<int:pk>/drive", DriveAPI.as_view()),
    # path("v1/requests/<int:pk>/captions", CaptionsAPI.as_view()),
    # path("v1/requests/<int:pk>/airtable", AirtableSyncAPI.as_view()),
    # path("v1/requests/<int:pk>/schedule", ScheduleAPI.as_view()),
    # path("v1/requests/<int:pk>/publish", PublishAPI.as_view()),
    # path("v1/requests/<int:pk>/metrics24h", MetricsAPI.as_view()),
    # path("avatar/new/", avatar_quick_create, name="avatar-new"),
    path("api/v1/paragraph", ParagraphAPI.as_view(), name="paragraph-api"),


    path("studio/", script_avatar_page, name="script-avatar"),
    # path("api/v1/ssml", SSMLAPI.as_view(), name="ssml-api"),

    # path("api/heygen/avatars", heygen_avatars_api, name="heygen-avatars"),
    # path("api/heygen/voices", heygen_voices_api, name="heygen-voices"),
    # path("api/icons/<int:pk>/meta", icon_meta_api, name="icon-meta"),
    
]
