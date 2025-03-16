from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserRegistration.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('update-profile/', views.UpdateProfile.as_view(), name='update-profile'),
    path('verify-email/',views.VerifyEmailView.as_view(), name="verify-mail"),
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]