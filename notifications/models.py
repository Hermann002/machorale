from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Notification persistante. Une ligne par destinataire."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    chorale = models.ForeignKey(
        'manage_chorale.Chorale',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True, blank=True,
    )
    kind = models.CharField(max_length=50, default='generic')
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_at']),
            models.Index(fields=['user', 'chorale', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} → {self.user}"
