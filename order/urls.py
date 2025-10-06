from django.urls import path
from .views import start_order, success

urlpatterns = [
    path('start_order/', start_order, name='start_order'),
    path('success/', success, name='order_success'),
]
