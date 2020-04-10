FROM node:12
# Note: Using Node 10 because it's the current LTS release and fabric doesn't work with odd numbers.

# Needed for node-gyp
#RUN apt-get update
#RUN apt-get install -y g++ build-essential

RUN mkdir /work/
RUN mkdir /work/front-end
# It seems like it is safe to copy these files and then "mount" over them.
COPY ./package.json /work/front-end
COPY ./package-lock.json /work/front-end
WORKDIR /work/front-end

# This is used by the production build script
RUN mkdir /work/output

# Necessary for certain modules to install correctly (mostly fabric).
#RUN npm install -g node-gyp

RUN npm install

COPY . /work/front-end

RUN npm run modernizr
RUN npm run compile-validators

# The "serve" mode will hot-reload components and watch for changes automatically.
ENTRYPOINT ["npm", "run"]
CMD ["serve"]
