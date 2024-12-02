document.addEventListener("DOMContentLoaded", function () {
  const actorSearch = document.getElementById("actorSearch");
  const suggestions = document.getElementById("suggestions");
  const actorDetails = document.getElementById("actorDetails");
  const actorMovies = document.getElementById("actorMovies");
  let timeoutId;

  if (!actorSearch || !suggestions) {
    console.error("Required elements not found!");
    return;
  }

  actorSearch.addEventListener("input", function () {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      const query = this.value.trim();
      if (query) {
        console.log("Searching for actor:", query);
        fetch(`/get_actor_autocomplete?query=${encodeURIComponent(query)}`)
          .then((response) => response.json())
          .then((data) => {
            console.log("Received actor data:", data);
            suggestions.innerHTML = "";

            if (
              data.success &&
              data.suggestions &&
              Array.isArray(data.suggestions)
            ) {
              data.suggestions.forEach((actor) => {
                const div = document.createElement("div");
                div.className = "suggestion-item";
                div.textContent = actor.name;

                if (actor.known_for && actor.known_for.length > 0) {
                  const knownFor = document.createElement("small");
                  knownFor.textContent = `Known for: ${actor.known_for.join(
                    ", "
                  )}`;
                  div.appendChild(knownFor);
                }

                div.dataset.actorName = actor.name;
                div.onclick = () => selectActor(actor.name);
                suggestions.appendChild(div);
              });
            } else {
              suggestions.innerHTML =
                "<div class='suggestion-item'>No results found</div>";
            }
            suggestions.style.display = "block";
          })
          .catch((error) => {
            console.error("Actor search error:", error);
            suggestions.innerHTML =
              "<div class='suggestion-item'>Error searching for actors</div>";
            suggestions.style.display = "block";
          });
      } else {
        suggestions.style.display = "none";
      }
    }, 300);
  });

  function selectActor(actorName) {
    actorSearch.value = actorName;
    suggestions.style.display = "none";

    fetch(`/get_actor_details?actor_name=${encodeURIComponent(actorName)}`)
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          const actor = data.actor;
          actorDetails.innerHTML = `
                      <div class="actor-header">
                          ${
                            actor.profile_path
                              ? `<img src="${actor.profile_path}" alt="${actor.name}" class="actor-poster">`
                              : ""
                          }
                          <div class="actor-info">
                              <h1 class="actor-title">${actor.name}</h1>
                              <div class="actor-meta">
                                  <p>Birthday: ${actor.birthday}</p>
                                  <p>Place of Birth: ${actor.place_of_birth}</p>
                                  <p>Known For: ${
                                    actor.known_for_department
                                  }</p>
                                  <p>Popularity: ${actor.popularity}</p>
                              </div>
                              ${
                                actor.also_known_as.length > 0
                                  ? `<h3>Also Known As</h3><p>${actor.also_known_as.join(
                                      ", "
                                    )}</p>`
                                  : ""
                              }
                          </div>
                      </div>
                  `;
          actorDetails.style.display = "block";

          actorMovies.innerHTML = "";
          actor.movies.forEach((movie) => {
            const div = document.createElement("div");
            div.className = "recommendation-card";
            div.innerHTML = `
              <div class="recommendation-container">
                <div class="recommendation-card" style="pointer-events: none;">
                  <img src="${movie.poster_path}" alt="${movie.title}" class="movie-poster" style="width:320px; height:450px;">
                  <h3>${movie.title} (${movie.release_date.split("-")[0]})</h3>
                </div>
              </div>
            `;
            actorMovies.appendChild(div);
          });
          actorMovies.style.display = "grid";
        }
      });
  }

  document.addEventListener("click", function (e) {
    if (!suggestions.contains(e.target) && e.target !== actorSearch) {
      suggestions.style.display = "none";
    }
  });
});
