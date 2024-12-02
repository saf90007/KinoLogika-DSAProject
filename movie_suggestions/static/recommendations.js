document.addEventListener("DOMContentLoaded", function () {
  const movieSearch = document.getElementById("movieSearch");
  const suggestions = document.getElementById("suggestions");
  const movieDetails = document.getElementById("movieDetails");
  const movieRecommendations = document.getElementById("movieRecommendations");
  let timeoutId;

  if (!movieSearch || !suggestions || !movieRecommendations) {
    console.error("Required elements not found!");
    return;
  }

  movieSearch.addEventListener("input", function () {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      const query = this.value.trim();
      if (query) {
        fetch(`/get_movie_autocomplete?query=${encodeURIComponent(query)}`)
          .then((response) => response.json())
          .then((data) => {
            suggestions.innerHTML = "";
            data.suggestions.forEach((movie) => {
              const div = document.createElement("div");
              div.className = "suggestion-item";
              const movieText = `${movie.title} (${movie.year})`;
              div.textContent = movieText;
              div.dataset.movieId = movie.id;
              div.dataset.movieText = movieText;
              div.onclick = () => selectMovie(movie.id, movieText);
              suggestions.appendChild(div);
            });
            suggestions.style.display = "block";
          })
          .catch((error) => {
            console.error("Movie search error:", error);
            suggestions.innerHTML =
              "<div class='suggestion-item'>Error searching for movies</div>";
            suggestions.style.display = "block";
          });
      } else {
        suggestions.style.display = "none";
      }
    }, 300);
  });

  function selectMovie(movieId, movieText) {
    movieSearch.value = movieText;
    suggestions.style.display = "none";
    const loadingAnimation = document.getElementById("loading-animation");
    loadingAnimation.style.display = "flex";
    movieDetails.style.display = "none";
    movieRecommendations.style.display = "none";
    fetch(`/get_movie_details?movie_id=${movieId}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          const movie = data.movie;
          const fillerImage =
            "https://png.pngtree.com/png-vector/20190820/ourmid/pngtree-no-image-vector-illustration-isolated-png-image_1694547.jpg";

          let posterPath;
          const invalidPosterUrl = "https://image.tmdb.org/t/p/w500None";

          if (
            movie.poster_path &&
            movie.poster_path !== "null" &&
            movie.poster_path !== invalidPosterUrl
          ) {
            posterPath = movie.poster_path;
            console.log("Movie poster found:", posterPath);
          } else {
            posterPath = fillerImage;
            console.log(
              "No valid movie poster available. Using filler image:",
              posterPath
            );
          }
          movieDetails.innerHTML = `
                    <div class="movie-header">
                        <img src="${posterPath}" alt="${
            movie.title
          }" class="movie-poster">
                        <div class="movie-info">
                            <h1 class="movie-title">${movie.title}</h1>
                            <div class="movie-meta">
                                <p>Release Date: ${movie.release_date}</p>
                                <p>Runtime: ${movie.runtime} minutes</p>
                                <p>Genres: ${movie.genres.join(", ")}</p>
                                <p class="rating">Rating: ${
                                  movie.vote_average
                                }/10</p>
                            </div>
                            <h3>Overview</h3>
                            <p>${movie.overview}</p>
                            <h3>Director</h3>
                            <p>${movie.director}</p>
                            <h3>Cast</h3>
                            <p>${movie.cast.join(", ")}</p>
                            <div class="movie-stats">
                                <p>Budget: $${(movie.budget / 1000000).toFixed(
                                  2
                                )}M</p>
                                <p>Revenue: $${(
                                  movie.revenue / 1000000
                                ).toFixed(2)}M</p>
                            </div>
                        </div>
                    </div>
                `;
          movieDetails.style.display = "block";
          fetchRecommendations(movieId);
        }
      });
  }

  function fetchRecommendations(movieId) {
    const loadingAnimation = document.getElementById("loading-animation");
    const fillerImage =
      "https://png.pngtree.com/png-vector/20190820/ourmid/pngtree-no-image-vector-illustration-isolated-png-image_1694547.jpg";
    const invalidPosterUrl = "https://image.tmdb.org/t/p/w500None";

    fetch(`/api/recommendations/?movie_id=${movieId}`)
      .then((response) => response.json())
      .then((data) => {
        loadingAnimation.style.display = "none"; 
        if (data.success) {
          movieRecommendations.innerHTML = `
                    <h2>Movie Recommendations</h2>
                    <div class="recommendations-container">
                        ${data.recommendations
                          .map((rec) => {
                            const posterPath =
                              rec.poster_path &&
                              rec.poster_path !== "null" &&
                              rec.poster_path !== invalidPosterUrl
                                ? rec.poster_path
                                : fillerImage;

                            return `
                                    <div class="recommendation-card">
                                        <img 
                                            src="${posterPath}" 
                                            alt="${rec.title}" 
                                            class="movie-poster"
                                        >
                                        <h3>${rec.title} (${
                              rec.release_date
                                ? rec.release_date.split("-")[0]
                                : rec.year || "Unknown"
                            })</h3>
                                    </div>
                                `;
                          })
                          .join("")}
                    </div>
                `;
          movieRecommendations.style.display = "block";
        } else {
          movieRecommendations.innerHTML =
            "<p>No recommendations available.</p>";
          movieRecommendations.style.display = "block";
        }
      })
      .catch((error) => {
        console.error("Error fetching recommendations:", error);
        movieRecommendations.innerHTML =
          "<p>Error loading recommendations.</p>";
        movieRecommendations.style.display = "block";
      });
  }
  document.addEventListener("click", function (e) {
    if (!suggestions.contains(e.target) && e.target !== movieSearch) {
      suggestions.style.display = "none";
    }
  });
});