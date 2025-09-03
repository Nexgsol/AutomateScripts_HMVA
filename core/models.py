from django.db import models
from django.utils import timezone

class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    timezone = models.CharField(max_length=64, default="America/New_York")
    hashtags = models.TextField(blank=True, help_text="comma separated default tags")
    post_windows = models.CharField(max_length=64, default="08:00,13:00,20:00")
    def __str__(self): return self.name


class AvatarProfile(models.Model):
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    avatar_name = models.CharField(max_length=100)
    heygen_avatar_id = models.CharField(max_length=100, blank=True)
    voice_name = models.CharField(max_length=100)
    elevenlabs_voice_id = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to="avatars/", blank=True, null=True)  
    def __str__(self): return f"{self.brand}:{self.avatar_name}/{self.voice_name}"

class Template(models.Model):
    ENGINE_CHOICES = [("shotstack","Shotstack"),("cloudinary","Cloudinary")]
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    template_id = models.CharField(max_length=64)
    engine = models.CharField(max_length=16, choices=ENGINE_CHOICES, default="shotstack")
    aspect = models.CharField(max_length=16, default="9:16")
    duration_sec = models.PositiveIntegerField(default=30)
    payload_json = models.JSONField(default=dict, blank=True)
    def __str__(self): return f"{self.brand}:{self.template_id}"

class PublishTarget(models.Model):
    PLATFORM_CHOICES = [("yt","YouTube"),("ig","Instagram"),("fb","Facebook"),("tt","TikTok")]
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    platform = models.CharField(max_length=8, choices=PLATFORM_CHOICES)
    enabled = models.BooleanField(default=True)
    channel_or_page_id = models.CharField(max_length=100, blank=True)
    def __str__(self): return f"{self.brand}:{self.get_platform_display()}"

class ScriptRequest(models.Model):
    MODE = [("Single","Single"),("Discover","Discover"),("GenerateList","GenerateList")]
    DUR = [("15s","15sStory"),("30s","30sReel"),("60s","60sReel")]
    STATUS = [
        ("New","New"),("Drafted","Drafted"),("NeedsFix","Needs Fix"),
        ("Assembling","Assembling"),("Rendered","Rendered"),
        ("Ready","Ready to Schedule"),("Scheduled","Scheduled"),
        ("Posted","Posted"),("Pulled","24h Pulled"),("Published","Published"),
        ("Approved","Approved for Editing")
    ]
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE)
    mode = models.CharField(max_length=16, choices=MODE, default="Single")
    icon_or_topic = models.CharField(max_length=200)
    notes = models.TextField(blank=True)
    duration = models.CharField(max_length=8, choices=DUR, default="30s")
    avatar = models.ForeignKey(AvatarProfile, on_delete=models.SET_NULL, null=True, blank=True)
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="New")

    draft_script = models.TextField(blank=True)
    qc_json = models.JSONField(null=True, blank=True)
    final_script = models.TextField(blank=True)

    caption_yt = models.TextField(blank=True)
    caption_tt = models.TextField(blank=True)
    caption_ig_reels = models.TextField(blank=True)
    caption_ig_stories = models.TextField(blank=True)
    caption_fb_reels = models.TextField(blank=True)

    audio_url = models.URLField(blank=True)
    asset_url = models.URLField(blank=True)
    edit_url = models.URLField(blank=True)
    file_name = models.CharField(max_length=200, blank=True)

    scheduled_slot = models.CharField(max_length=16, blank=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    post_ids = models.JSONField(default=dict, blank=True)
    performance_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self): return f"{self.brand} · {self.icon_or_topic} [{self.status}]"
