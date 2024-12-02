from django.urls import path
from . import views

urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("recs/", views.RecsView.as_view(), name="recs"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("movieData/", views.MovieDataView.as_view(), name="movieData"),
    path("actorData/", views.ActorDataView.as_view(), name="actorData"),
    path(
        "get_movie_autocomplete",
        views.GetMovieAutocomplete.as_view(),
        name="get_movie_autocomplete",
    ),
    path(
        "get_movie_autocomplete/",
        views.GetMovieAutocomplete.as_view(),
        name="get_movie_autocomplete_slash",
    ),
    path(
        "get_movie_details", views.FetchMovieDetails.as_view(), name="get_movie_details"
    ),
    path(
        "get_actor_autocomplete",
        views.GetActorAutocomplete.as_view(),
        name="get_actor_autocomplete",
    ),
    path(
        "get_actor_autocomplete/",
        views.GetActorAutocomplete.as_view(),
        name="get_actor_autocomplete_slash",
    ),
    path("get_actor_movies", views.GetActorMovies.as_view(), name="get_actor_movies"),
    path(
        "get_actor_details", views.GetActorDetails.as_view(), name="get_actor_details"
    ),
    path(
        "get_actor_details/",
        views.GetActorDetails.as_view(),
        name="get_actor_details_slash",
    ),
    path(
        "api/recommendations/",
        views.MovieRecommendationsView.as_view(),
        name="movie-recommendations",
    ),
]
