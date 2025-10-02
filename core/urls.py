from django.urls import path
from django.contrib.auth import views as auth_views
from . import views                                 
from product.views import product                   

urlpatterns = [
    path('', views.frontpage, name='frontpage'),
    path('signup/', views.signup, name='signup'),
    path('myaccount/', views.myaccount, name='myaccount'),
    path('myaccount/edit/', views.edit_myaccount, name='edit_myaccount'),
    path('shop/', views.shop, name='shop'),
    path('about/', views.about, name='about'),
    path('shop/<slug:slug>/', product, name='product'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]