docker rm $(docker ps -a | grep front-end | cut -c1-12); docker-compose build front-end; docker-compose up front-end
