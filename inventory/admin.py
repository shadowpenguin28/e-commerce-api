from django.contrib import admin

# Register your models here.

from django.contrib import admin
from .models import Category, Item, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'category', 'price', 'quantity', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['sku', 'created_at', 'updated_at', 'restocked_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'sku')
        }),
        ('Pricing & Stock', {
            'fields': ('price', 'quantity', 'is_active')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'restocked_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ['item', 'quantity_change', 'reason', 'created_at']
    list_filter = ['reason', 'created_at']
    search_fields = ['item__name', 'reason']
    readonly_fields = ['created_at']