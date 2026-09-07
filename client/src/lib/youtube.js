// Loads the YouTube IFrame API once and resolves with window.YT.
let promise = null;

export function loadYouTubeAPI() {
  if (promise) return promise;
  promise = new Promise((resolve) => {
    if (window.YT && window.YT.Player) {
      resolve(window.YT);
      return;
    }
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
    window.onYouTubeIframeAPIReady = () => resolve(window.YT);
  });
  return promise;
}
