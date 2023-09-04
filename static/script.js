var preloader = document.getElementById("preloader");
const element = document.getElementsByClassName("tagvisibility");

function loader() {
  preloader.style.display = "none";
  document.getElementById('body_id').classList.remove('hidden');

  for (let i = 0; i < element.length; i++) {
    element[i].style.visibility = "visible"
  }
}

window.addEventListener("load", setTimeout(loader, 1000));

fetch('/average_rating')
            .then(response => response.json())
            .then(data => {
                document.getElementById('average_rating').innerHTML = 'Average Rating: ' + data.average_rating.toFixed(2);
            });
