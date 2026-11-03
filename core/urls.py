from django.urls import path
from . import views

urlpatterns = [
    # ── Legacy HTML views ────────────────────────────────────────────────
    path('',                    views.home,               name='home'),
    path('check-eligibility/',  views.check_eligibility,  name='check_eligibility'),
    path('match/',              views.match_api,           name='match_api'),

    # ── REST API endpoints ───────────────────────────────────────────────
    path('api/match-schemes/',  views.MatchSchemesAPIView.as_view(),  name='api_match_schemes'),
    path('api/schemes/',        views.SchemeListAPIView.as_view(),    name='api_schemes_list'),
    path('api/add-scheme/',     views.add_scheme,                  name='api_add_scheme'),
    path('api/undo-last/',      views.UndoAPIView.as_view(),          name='api_undo_last'),
]
