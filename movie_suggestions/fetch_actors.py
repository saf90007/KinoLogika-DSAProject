import requests
from movie_suggestions.data_structures import Trie, cache_manager
from myproject.settings import TMDB_API_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple
import logging
import threading

logger = logging.getLogger(__name__)

class ActorMovieManager:
    def __init__(self):
        self.actor_trie = Trie()
        self.actor_movies: Dict[str, List] = {}
        self.actor_details: Dict[str, Dict] = {}
        self.lock = threading.Lock()  
        self.stop_fetching = False 
        self._initialize_data()
        self._start_background_fetching()

    def _initialize_data(self):
        cached_data = cache_manager.actor_cache.get('actor_movie_data')
        logger.debug(f"Cached data found: {bool(cached_data)}")
        
        if cached_data:
            self.actor_movies = cached_data.get('movies', {})
            self.actor_details = cached_data.get('actor_details', {})
            logger.debug(f"Loaded {len(self.actor_movies)} actors from cache")
            
            self.actor_trie = Trie()
            for actor_name in self.actor_movies.keys():
                self.actor_trie.insert(actor_name.lower()) 
            
            logger.debug(f"Populated trie with {len(self.actor_movies)} actors")
        else:
            logger.debug("No cached data found, fetching fresh data")
            self._fetch_initial_actors()

    def _fetch_initial_actors(self):
        self._fetch_and_cache_actor_data(pages_to_fetch=10) 

    def _start_background_fetching(self):
        thread = threading.Thread(target=self._fetch_additional_actors, daemon=True)
        thread.start()

    def _fetch_additional_actors(self):
        page = 11 
        while not self.stop_fetching:
            logger.debug(f"Background fetching actors from page {page}")
            actors = self.fetch_popular_actors(page)
            if actors:
                with self.lock: 
                    for actor in actors:
                        actor_name = actor['name'].strip().lower()
                        if actor_name not in self.actor_movies:
                            self.actor_trie.insert(actor_name)
                    logger.debug(f"Background fetched {len(actors)} actors from page {page}")
            page += 1

    def fetch_actor_movies(self, actor_id: int) -> List:
        url = f'https://api.themoviedb.org/3/person/{actor_id}/movie_credits?api_key={TMDB_API_KEY}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json().get('cast', [])
        except requests.RequestException:
            pass
        return []

    def fetch_popular_actors(self, page: int = 1) -> List:
        cache_key = f'popular_actors_page_{page}'
        cached_actors = cache_manager.actor_cache.get(cache_key)
        if cached_actors:
            return cached_actors

        url = f'https://api.themoviedb.org/3/person/popular?page={page}&api_key={TMDB_API_KEY}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                actors = response.json().get('results', [])
                cache_manager.actor_cache.put(cache_key, actors)
                return actors
        except requests.RequestException:
            pass
        return []

    def _fetch_and_cache_actor_data(self, pages_to_fetch: int):
        all_actors = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(self.fetch_popular_actors, page): page for page in range(1, pages_to_fetch + 1)}
            for future in as_completed(futures):
                page = futures[future]
                try:
                    actors = future.result()
                    all_actors.extend(actors)
                    logger.debug(f"Fetched {len(actors)} actors from page {page}")
                except Exception as e:
                    logger.error(f"Error fetching actors from page {page}: {e}")

        with self.lock:
            for actor in all_actors:
                actor_name = actor['name'].strip().lower()
                self.actor_trie.insert(actor_name)

            cache_manager.actor_cache.put('actor_movie_data', {
                'movies': self.actor_movies,
                'actor_details': self.actor_details
            })
            logger.debug(f"Cached {len(self.actor_movies)} actor-movie relationships and {len(self.actor_details)} actor details")

    def stop_background_fetching(self):
       self.stop_fetching = True


    def search_actors(self, prefix: str) -> List[Tuple[str, List]]:
        prefix = prefix.strip().lower()
        logger.debug(f"Searching for actors with prefix: {prefix}")
        
        logger.debug(f"Trie node count: {len(self.actor_trie.root.children)}")
        
        matching_actors = self.actor_trie.search_prefix(prefix)
        logger.debug(f"Found {len(matching_actors)} matching actors")
        
        results = [(actor, self.actor_movies.get(actor, [])) for actor in matching_actors]
        logger.debug(f"First few results: {results[:3]}")
        
        return results

    def get_actor_movies(self, actor_name: str) -> List:
        if actor_name in self.actor_movies:
            return self.actor_movies[actor_name]

        url = f'https://api.themoviedb.org/3/search/person?query={actor_name}&language=en-US&api_key={TMDB_API_KEY}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                actor_data = response.json().get('results', [])
                if actor_data:
                    actor_id = actor_data[0]['id']
                    movies = self.fetch_actor_movies(actor_id)
                    self.actor_movies[actor_name] = movies
                    return movies
        except requests.RequestException:
            pass
        return []

    def get_actor_details(self, actor_name: str):
        if actor_name in self.actor_details:
            logger.debug(f"Returning cached details for actor: {actor_name}")
            return self.actor_details[actor_name]
        
        url = f'https://api.themoviedb.org/3/search/person?query={actor_name}&language=en-US&api_key={TMDB_API_KEY}'
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                actor_data = response.json().get('results', [])
                if actor_data:
                    actor_details = actor_data[0] 
                    actor_id = actor_details['id']
                    actor_name = actor_details['name']
           
                    details_url = f'https://api.themoviedb.org/3/person/{actor_id}?api_key={TMDB_API_KEY}'
                    details_response = requests.get(details_url)
                    if details_response.status_code == 200:
                        detailed_info = details_response.json()
                        self.actor_details[actor_name] = detailed_info
                        cache_manager.actor_cache.put('actor_movie_data', {
                            'movies': self.actor_movies,
                            'actor_details': self.actor_details 
                        })
                        return detailed_info
                else:
                    logger.debug(f"No actor found for {actor_name}")
            else:
                logger.debug(f"Error from TMDB API: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Error fetching actor details: {e}")
        
        return {} 

actor_manager = ActorMovieManager()
