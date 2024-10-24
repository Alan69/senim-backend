from accounts.views import UserDetailView, LogoutView, update_user_view, current_user_view, RegisterView, ChangePasswordView, RegionViewSet

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from test_logic.views import ( 
    ProductViewSet, TestViewSet, QuestionViewSet, OptionViewSet,
    # OptionViewSet, ResultViewSet, BookSuggestionViewSet, 
    product_tests_view, required_tests_by_product,
    complete_test_view, get_all_completed_tests,
    get_completed_test_by_id
)

from payments.views import AddBalanceView

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'subjects', TestViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'options', OptionViewSet)
router.register(r'regions', RegionViewSet, basename='region')
# router.register(r'results', ResultViewSet)
# router.register(r'booksuggestions', BookSuggestionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    # path('login/', login, name='token_obtain_pair'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('change/password/', ChangePasswordView.as_view(), name='change-password'),

    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('user/', UserDetailView.as_view(), name='user_detail'),
    path('user/auth/', current_user_view, name='current_user_view'),

    path('user/update/', update_user_view, name='update-user'),

    path('current/test/', product_tests_view, name='get-tests'),

    path('product/<uuid:product_id>/tests/', required_tests_by_product, name='required-tests-by-product'),

    path('complete/test/', complete_test_view, name='complete-test'),
    path('completed-tests/<uuid:completed_test_id>/', get_completed_test_by_id, name='get-completed-test-by-id'),
    path('completed-tests/', get_all_completed_tests, name='get-all-completed-tests'),

    path('update/balance/', AddBalanceView.as_view(), name='add_balance'),
]
