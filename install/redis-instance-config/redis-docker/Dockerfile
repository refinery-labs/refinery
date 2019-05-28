FROM redis:latest
COPY redis.conf /usr/local/etc/redis/redis.conf
COPY docker-entrypoint.sh /usr/local/bin/
EXPOSE 6379
ENTRYPOINT [ "/usr/local/bin/docker-entrypoint.sh" ]
