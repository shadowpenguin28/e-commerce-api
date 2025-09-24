from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class SearchLog(models.Model):
    """
    Log search queries for analytics
    """
    query = models.CharField(max_length=255)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    results_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Search: '{self.query}' ({self.results_count} results)"
    
    class Meta:
        db_table = 'shop_search_log'
        ordering = ['-created_at']


class ProductView(models.Model):
    """
    Track product views for analytics
    """
    item = models.ForeignKey(
        'inventory.Item',
        on_delete=models.CASCADE,
        related_name='views'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"View: {self.item.name}"
    
    class Meta:
        db_table = 'shop_product_view'
        ordering = ['-created_at']