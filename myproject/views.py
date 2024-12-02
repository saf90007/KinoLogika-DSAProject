from django.shortcuts import render
from django.http import JsonResponse
from django.views import View
import requests
from myproject.settings import TMDB_API_KEY
from movie_suggestions.data_structures import (
    movie_trie,
    MovieSimilarityGraph,
    cache_manager,
)
from movie_suggestions.fetch_actors import actor_manager
from concurrent.futures import ThreadPoolExecutor
import time


class SearchActorsView(View):
    def get(self, request):
        prefix = request.GET.get("prefix", "")
        results = actor_manager.search_actors(prefix)
        formatted_results = [(actor.title(), movies) for actor, movies in results]
        return JsonResponse({"suggestions": formatted_results})

class FetchMovieDetails(View):
    def get(self, request):
        movie_id = request.GET.get("movie_id")
        if movie_id:
            movie_details = self.fetch_movie_details(movie_id)
            if movie_details:
                return JsonResponse({"success": True, "movie": movie_details})
        return JsonResponse({"success": False, "message": "Movie not found"})

    @staticmethod
    def fetch_movie_details(movie_id):
        cache_key = f"movie_details_{movie_id}"
        movie_details = cache_manager.movie_cache.get(cache_key)

        if movie_details:
            return movie_details

        movie_url = (
            f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        )
        credits_url = f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}"

        try:
            movie_response = requests.get(movie_url)
            credits_response = requests.get(credits_url)
            if (
                movie_response.status_code == 200
                and credits_response.status_code == 200
            ):
                movie_data = movie_response.json()
                credits_data = credits_response.json()
                director = next(
                    (
                        crew["name"]
                        for crew in credits_data["crew"]
                        if crew["job"] == "Director"
                    ),
                    "N/A",
                )
                cast = [actor["name"] for actor in credits_data["cast"][:5]]
                movie_details = {
                    "title": movie_data["title"],
                    "overview": movie_data["overview"],
                    "poster_path": f"https://image.tmdb.org/t/p/w500{movie_data['poster_path']}",
                    "release_date": movie_data["release_date"],
                    "vote_average": movie_data["vote_average"],
                    "genres": [genre["name"] for genre in movie_data["genres"]],
                    "runtime": movie_data["runtime"],
                    "director": director,
                    "cast": cast,
                    "budget": movie_data["budget"],
                    "revenue": movie_data["revenue"],
                }
                cache_manager.movie_cache.put(cache_key, movie_details)
                return movie_details
        except Exception as e:
            print(f"Error fetching movie details: {e}")
        return None

class GetMovieAutocomplete(View):
    def get(self, request):
        query = request.GET.get("query", "")
        if query:
            cache_key = f"search_{query}"
            cached_results = cache_manager.search_cache.get(cache_key)
            if cached_results:
                return JsonResponse({"suggestions": cached_results})

            suggestions = self.fetch_movies(query)
            for movie in suggestions:
                movie_trie.insert(movie["title"])
            movie_titles = [
                {
                    "title": movie["title"],
                    "year": movie["release_date"][:4],
                    "id": movie["id"],
                }
                for movie in suggestions
            ]

            cache_manager.search_cache.put(cache_key, movie_titles)
        else:
            movie_titles = []
        return JsonResponse({"suggestions": movie_titles})

    @staticmethod
    def fetch_movies(movie_name):
        url = f"https://api.themoviedb.org/3/search/movie?query={movie_name}&language=en-US&api_key={TMDB_API_KEY}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                movie_data = response.json()
                return movie_data["results"]
        except Exception as e:
            print(f"Error fetching movie data: {e}")
        return []


class GetActorAutocomplete(View):
    def get(self, request):
        query = request.GET.get("query", "").lower()
        
        if not query:
            return JsonResponse({"suggestions": []})
            
        results = actor_manager.search_actors(query)
        
        suggestions = [{
            "name": actor[0].title(),
            "id": None,  
            "known_for": actor[1][:3] if actor[1] else [] 
        } for actor in results]
        
        return JsonResponse({
            "success": True,
            "suggestions": suggestions
        })

class GetActorMovies(View):
    def get(self, request):
        actor_name = request.GET.get("actor_name", "").lower()
        try:
            movies = actor_manager.get_actor_movies(actor_name)
            movie_details = []
            with ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(FetchMovieDetails.fetch_movie_details, movie["id"])
                    for movie in movies
                    if "id" in movie
                ]
                for future in futures:
                    try:
                        movie_detail = future.result()
                        if movie_detail:
                            movie_detail["year"] = movie_detail["release_date"][:4]
                            movie_details.append(movie_detail)
                    except Exception as e:
                        continue
            return JsonResponse({"success": True, "movies": movie_details})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

class GetActorDetails(View):
    def get(self, request):
        actor_name = request.GET.get("actor_name")
        if not actor_name:
            return JsonResponse({"error": "Actor name is required"}, status=400)

        cache_key = f"actor_details_{actor_name}"
        cached_details = cache_manager.actor_cache.get(cache_key)
        if cached_details:
            return JsonResponse(cached_details)

        print(f"Searching for actor: {actor_name}")

        search_url = f"https://api.themoviedb.org/3/search/person?query={actor_name}&api_key={TMDB_API_KEY}"
        response = requests.get(search_url)
        data = response.json()

        if data.get("results"):
            actor_id = data["results"][0]["id"]
            details_url = f"https://api.themoviedb.org/3/person/{actor_id}?append_to_response=movie_credits&api_key={TMDB_API_KEY}"
            details_response = requests.get(details_url)
            actor_details = details_response.json()

            response_data = {
                "success": True,
                "actor": {
                    "name": actor_details["name"],
                    "birthday": actor_details.get("birthday"),
                    "place_of_birth": actor_details.get("place_of_birth"),
                    "profile_path": (
                        f"https://image.tmdb.org/t/p/w500{actor_details['profile_path']}"
                        if actor_details.get("profile_path")
                        else None
                    ),
                    "known_for_department": actor_details.get("known_for_department"),
                    "also_known_as": actor_details.get("also_known_as", []),
                    "popularity": actor_details.get("popularity"),
                    "movies": [
                        {
                            "id": movie["id"],
                            "title": movie["title"],
                            "character": movie.get("character", ""),
                            "release_date": movie.get("release_date", ""),
                            "poster_path": (
                                f"https://image.tmdb.org/t/p/w500{movie['poster_path']}"
                                if movie.get("poster_path")
                                else None
                            ),
                        }
                        for movie in actor_details.get("movie_credits", {}).get(
                            "cast", []
                        )
                    ],
                },
            }

            cache_manager.actor_cache.put(cache_key, response_data)
            return JsonResponse(response_data)
        else:
            print("No results found for actor.")
            return JsonResponse({"success": False, "error": "Actor not found"})

class MovieRecommendationsView(View):
    def get(self, request):
        movie_id = request.GET.get("movie_id")
        if not movie_id:
            return JsonResponse({"success": False, "message": "Movie ID is required"})

        cache_key = f"recommendations_{movie_id}"
        cached_recommendations = cache_manager.similarity_cache.get(cache_key)
        if cached_recommendations:
            return JsonResponse(cached_recommendations)

        try:
            graph = MovieSimilarityGraph()

            movie_details = self.fetch_movie_details(movie_id)
            if not movie_details:
                return JsonResponse({"success": False, "message": "Movie not found"})

            self.add_movie_to_graph(graph, movie_details)

            recommended = self.fetch_recommendations(movie_id)
            for rec in recommended[:20]:
                rec_details = self.fetch_movie_details(rec["id"])
                if rec_details:
                    self.add_movie_to_graph(graph, rec_details)
                    time.sleep(0.25)  

            similar = self.fetch_similar_movies(movie_id)
            for sim in similar[:20]:
                sim_details = self.fetch_movie_details(sim["id"])
                if sim_details:
                    self.add_movie_to_graph(graph, sim_details)
                    time.sleep(0.25)

            director = self.get_director(movie_details)
            if director:
                director_movies = self.search_movies(director)
                for movie in director_movies[:10]:
                    dir_movie_details = self.fetch_movie_details(movie["id"])
                    if dir_movie_details:
                        self.add_movie_to_graph(graph, dir_movie_details)
                        time.sleep(0.25)

            graph.build_graph()
            recommendations = graph.get_recommendations(int(movie_id))

            if recommendations:
                response_data = {
                    "success": True,
                    "recommendations": [
                        {
                            "title": rec["title"],
                            "year": rec["year"] if rec["year"] else "Unknown Year",
                            "poster_path": (
                                f"https://image.tmdb.org/t/p/w500{rec.get('poster_path')}"
                                if rec.get("poster_path")
                                else None
                            ),
                        }
                        for rec in recommendations
                    ],
                }

                cache_manager.similarity_cache.put(cache_key, response_data)
                return JsonResponse(response_data)
            return JsonResponse(
                {"success": False, "message": "No recommendations found"}
            )

        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    def fetch_movie_details(self, movie_id):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "append_to_response": "credits,keywords",
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"Error fetching movie details: {e}")
            return None

    def fetch_recommendations(self, movie_id):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/recommendations"
        params = {"api_key": TMDB_API_KEY, "language": "en-US", "page": 1}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception:
            return []

    def fetch_similar_movies(self, movie_id):
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/similar"
        params = {"api_key": TMDB_API_KEY, "language": "en-US", "page": 1}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception:
            return []

    def search_movies(self, query):
        url = f"https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "language": "en-US",
            "query": query,
            "page": 1,
            "include_adult": False,
        }
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json().get("results", [])
            return []
        except Exception:
            return []

    def get_director(self, movie_details):
        try:
            return next(
                (
                    crew["name"]
                    for crew in movie_details.get("credits", {}).get("crew", [])
                    if crew["job"] == "Director"
                ),
                None,
            )
        except Exception:
            return None

    def add_movie_to_graph(self, graph, movie_details):
        if not movie_details:
            return
        try:
            director = self.get_director(movie_details) or "Unknown Director"

            cast = [
                c["name"]
                for c in movie_details.get("credits", {}).get("cast", [])
                if c.get("order", 10) < 5
            ]

            keywords = [
                kw["name"]
                for kw in movie_details.get("keywords", {}).get("keywords", [])
            ]

            year = (
                int(movie_details.get("release_date", "").split("-")[0])
                if movie_details.get("release_date", "")
                else 0
            )

            graph.add_movie(
                movie_id=movie_details["id"],
                title=movie_details.get("title", "Unknown Title"),
                genres=[g["name"] for g in movie_details.get("genres", [])],
                cast=cast,
                director=director,
                year=year,
                rating=movie_details.get("vote_average", 0.0),
                popularity=movie_details.get("popularity", 0.0),
                keywords=keywords,
                poster_path=movie_details.get("poster_path"),  
                release_date=movie_details.get("release_date"),  
            )
        except Exception as e:
            print(f"Error adding movie to graph: {e}")


class IndexView(View):
    def get(self, request):
        return render(request, "index.html")


class RecsView(View):
    def get(self, request):
        return render(request, "recs.html")


class AboutView(View):
    def get(self, request):
        return render(request, "about.html")


class MovieDataView(View):
    def get(self, request):
        return render(request, "movieData.html")


class ActorDataView(View):
    def get(self, request):
        return render(request, "actorData.html")
