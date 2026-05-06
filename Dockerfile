FROM postgis/postgis:15-3.4

COPY db/init_obrail_db.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
