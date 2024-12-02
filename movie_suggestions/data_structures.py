from typing import Any, Dict, List, Optional, Set
from collections import defaultdict, OrderedDict
import time
from collections import defaultdict
from typing import List, Dict, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

class TrieNode:
    def __init__(self):
        self.children = {}
        self.is_end_of_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word):
        node = self.root
        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True

    def search_prefix(self, prefix):
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        return self._get_words_from_node(node, prefix)

    def _get_words_from_node(self, node, prefix):
        words = []
        if node.is_end_of_word:
            words.append(prefix)
        for char, child in node.children.items():
            words.extend(self._get_words_from_node(child, prefix + char))
        return words

movie_trie = Trie()
actor_trie = Trie()

class LRUCache:
    def __init__(self, capacity: int = 1000, ttl: int = 3600):
        self.capacity = capacity
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}

    def get(self, key: str) -> Optional[Any]:
        if key not in self.cache:
            return None

        if time.time() - self.timestamps[key] > self.ttl:
            self.remove(key)
            return None

        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def put(self, key: str, value: Any) -> None:
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            oldest_key, _ = self.cache.popitem(last=False)
            del self.timestamps[oldest_key]

        self.cache[key] = value
        self.timestamps[key] = time.time()

    def remove(self, key: str) -> None:
        if key in self.cache:
            del self.cache[key]
            del self.timestamps[key]

    def clear(self) -> None:
        self.cache.clear()
        self.timestamps.clear()

class CacheManager:
    def __init__(self):
        self.movie_cache = LRUCache(capacity=1000, ttl=86400)
        self.actor_cache = LRUCache(capacity=1000, ttl=86400)
        self.search_cache = LRUCache(capacity=500, ttl=1800)
        self.similarity_cache = LRUCache(capacity=2000, ttl=3600)

cache_manager = CacheManager()

class MovieSimilarityGraph:
    def __init__(self):
        self.movies = {}
        self.graph = defaultdict(dict)
        self.genre_weights = {}
        self.genre_hierarchy = {
            'Action': ['Adventure', 'Thriller'],
            'Drama': ['Romance', 'Family'],
            'Science Fiction': ['Fantasy', 'Adventure'],
            'Comedy': ['Romance', 'Family'],
            'Horror': ['Thriller', 'Mystery'],
            'Documentary': ['History', 'Biography'],
            'Animation': ['Family', 'Adventure'],
            'Romance': ['Drama', 'Comedy'],
            'Thriller': ['Mystery', 'Crime'],
            'Fantasy': ['Adventure', 'Family'],
            'Crime': ['Drama', 'Thriller'],
            'Adventure': ['Action', 'Fantasy'],
            'Mystery': ['Thriller', 'Crime'],
            'Family': ['Comedy', 'Animation'],
            'History': ['Drama', 'Biography'],
            'Biography': ['Drama', 'History']
        }
        self.mood_indicators = {
            'dark': ['thriller', 'horror', 'crime', 'mystery', 'noir', 'dark', 'violent', 'suspense', 'dystopian'],
            'light': ['comedy', 'animation', 'family', 'adventure', 'fun', 'heartwarming', 'uplifting', 'romantic comedy'],
            'emotional': ['drama', 'romance', 'tragedy', 'emotional', 'touching', 'tearjerker', 'meaningful'],
            'intellectual': ['documentary', 'biography', 'historical', 'philosophical', 'political', 'thought-provoking'],
            'action-packed': ['action', 'adventure', 'superhero', 'war', 'martial arts', 'explosive', 'fast-paced'],
            'surreal': ['fantasy', 'science fiction', 'supernatural', 'magical', 'dreamlike', 'bizarre']
        }
        self.similarities_computed = False

    def preprocess_keywords(self, keywords: List[str]) -> Set[str]:
        stemmer = PorterStemmer()
        processed = set()
        
        for keyword in keywords:
            tokens = word_tokenize(keyword.lower())
            stems = {stemmer.stem(token) for token in tokens}
            processed.update(stems)
            if len(tokens) > 1:
                processed.add(keyword.lower())
            
        return processed

    def add_movie(self, movie_id: int, title: str, genres: List[str], 
             cast: List[str], director: str, year: int, rating: float,
             popularity: float = 0.0, keywords: List[str] = None,
             runtime: int = None, synopsis: str = None,
             poster_path: str = None,  
             release_date: str = None):  
        processed_keywords = self.preprocess_keywords(keywords or [])
        mood_scores = self.analyze_mood(keywords or [], synopsis or '')

        if release_date:
            try:
                year = int(release_date.split('-')[0])
            except Exception as e:
                print(f"Error extracting year from release_date {release_date}: {e}")
                year = 0

        print(f"Adding movie: {title} with year: {year}") 

        year = int(release_date.split('-')[0]) if release_date else 0
        
        self.movies[movie_id] = {
            'title': title,
            'genres': set(genres),
            'cast': list(cast),
            'director': director,
            'year': year,
            'rating': rating,
            'popularity': popularity,
            'keywords': processed_keywords,
            'runtime': runtime,
            'synopsis': synopsis,
            'mood_scores': mood_scores,
            'poster_path': poster_path,  
            'release_date': release_date  
        }
        self.similarities_computed = False

    def calculate_genre_similarity(self, genres1: Set[str], genres2: Set[str]) -> float:
        score = 0
        total_possible = max(len(genres1), len(genres2))
        
        if total_possible == 0:
            return 0
            
        for g1 in genres1:
            for g2 in genres2:
                if g1 == g2:
                    score += 1.0
                elif g2 in self.genre_hierarchy.get(g1, []) or g1 in self.genre_hierarchy.get(g2, []):
                    score += 0.5
                    
        return score / total_possible

    def calculate_cast_similarity(self, cast1: List[str], cast2: List[str]) -> float:
        score = 0
        for i, actor1 in enumerate(cast1):
            if actor1 in cast2:
                position_weight = 1 / (1 + min(i, cast2.index(actor1)))
                score += position_weight
        return score

    def calculate_runtime_similarity(self, runtime1: Optional[int], runtime2: Optional[int]) -> float:
        if runtime1 is None or runtime2 is None:
            return 0
            
        diff = abs(runtime1 - runtime2)
        return max(0, 1 - (diff / 30) ** 2)

    def calculate_plot_similarity(self, synopsis1: Optional[str], synopsis2: Optional[str]) -> float:
        if not synopsis1 or not synopsis2:
            return 0
            
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform([synopsis1, synopsis2])
            return cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        except Exception:
            return 0

    def analyze_mood(self, keywords: List[str], synopsis: str) -> Dict[str, float]:
        movie_words = set(word.lower() for word in keywords)
        if synopsis:
            movie_words.update(word.lower() for word in synopsis.split())
        
        mood_scores = {}
        for mood, indicators in self.mood_indicators.items():
            matches = sum(1 for indicator in indicators if any(
                indicator in word for word in movie_words
            ))
            mood_scores[mood] = matches / len(indicators)
            
        return mood_scores

    def calculate_temporal_rating(self, movie: Dict, current_year: int = 2024) -> float:
        time_weight = 0.95 ** (current_year - movie['year'])
        return movie['rating'] * time_weight

    def calculate_similarity(self, movie_1: Dict, movie_2: Dict) -> float:
        score = 0
        
        genre_score = self.calculate_genre_similarity(movie_1['genres'], movie_2['genres'])
        score += genre_score * 3
        
        shared_keywords = movie_1['keywords'] & movie_2['keywords']
        keyword_score = len(shared_keywords) * 2
        score += keyword_score
        
        cast_score = self.calculate_cast_similarity(movie_1['cast'], movie_2['cast'])
        score += cast_score * 2
        
        if movie_1['director'] == movie_2['director'] and movie_1['director'] != 'Unknown Director':
            score += 2
        
        rating1 = self.calculate_temporal_rating(movie_1)
        rating2 = self.calculate_temporal_rating(movie_2)
        rating_diff = abs(rating1 - rating2)
        rating_score = 2 * (1 - (rating_diff / 10) ** 2)
        score += rating_score
        
        runtime_score = self.calculate_runtime_similarity(
            movie_1.get('runtime'), movie_2.get('runtime')
        )
        score += runtime_score
        
        if movie_1.get('synopsis') and movie_2.get('synopsis'):
            plot_score = self.calculate_plot_similarity(
                movie_1['synopsis'], movie_2['synopsis']
            )
            score += plot_score * 2
        
        mood_diff = sum(
            abs(movie_1['mood_scores'][mood] - movie_2['mood_scores'][mood])
            for mood in self.mood_indicators.keys()
        ) / len(self.mood_indicators)
        mood_score = (1 - mood_diff) * 2
        score += mood_score
        
        year_diff = abs(movie_1['year'] - movie_2['year'])
        year_score = 1 * (0.9 ** year_diff)
        score += year_score
        
        pop_diff = abs(movie_1['popularity'] - movie_2['popularity'])
        pop_score = 1 * (1 - min(pop_diff / 100, 1))
        score += pop_score
        
        return score

    def build_graph(self):
        self._calculate_genre_weights()
        movie_ids = list(self.movies.keys())
        
        for i in range(len(movie_ids)):
            for j in range(i + 1, len(movie_ids)):
                movie1_id = movie_ids[i]
                movie2_id = movie_ids[j]
                
                cache_key = f"similarity_{min(movie1_id, movie2_id)}_{max(movie1_id, movie2_id)}"
                cached_similarity = cache_manager.similarity_cache.get(cache_key)
                
                if cached_similarity is not None:
                    weight = cached_similarity
                else:
                    weight = self.calculate_similarity(
                        self.movies[movie1_id],
                        self.movies[movie2_id]
                    )
                    cache_manager.similarity_cache.put(cache_key, weight)
                
                if weight > 0:
                    self.graph[movie1_id][movie2_id] = weight
                    self.graph[movie2_id][movie1_id] = weight
        
        self.similarities_computed = True

    def _calculate_genre_weights(self):
        genre_count = defaultdict(int)
        for movie in self.movies.values():
            for genre in movie['genres']:
                genre_count[genre] += 1
        
        total_movies = len(self.movies)
        for genre, count in genre_count.items():
            self.genre_weights[genre] = 1 - (count / total_movies)

    def get_recommendations(self, movie_id: int, limit: int = 20) -> List[Dict]:
        if movie_id not in self.movies:
            return []

        if not self.similarities_computed:
            self.build_graph()

        cache_key = f"recommendations_{movie_id}_{limit}"
        cached_recommendations = cache_manager.search_cache.get(cache_key)
        if cached_recommendations:
            return cached_recommendations

        recommendations = []
        if movie_id in self.graph:
            for other_id in self.graph[movie_id]:
                other_movie = self.movies[other_id]
                
                year = other_movie.get('year', 0)
                print(f"Fetching recommendation: {other_movie['title']} with year: {year}")

                if year == 0 and other_movie.get('release_date'):
                    try:
                        year = int(other_movie['release_date'].split('-')[0])
                    except (ValueError, IndexError) as e:
                        print(f"Year extraction failed for {other_movie['title']}: {e}")
                        year = 'Unknown Year'
                else:
                    year = str(year) if year else 'Unknown Year'

                poster_path = other_movie.get('poster_path', None)
                poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else None

                similarity_score = self.graph[movie_id].get(other_id, 0)

                recommendations.append({
                    'title': other_movie['title'],
                    'year': year,
                    'poster_path': poster_url,
                    'similarity_score': similarity_score
                })

        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
        recommendations = recommendations[:limit]
        cache_manager.search_cache.put(cache_key, recommendations)
        return recommendations