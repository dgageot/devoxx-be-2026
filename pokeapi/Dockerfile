# syntax=docker/dockerfile:1
FROM pokeapi/pokeapi:master@sha256:99a2553e2d19702a556ff6d939ef4dcbfff6f39e25f2ea3b8ca8fa776c050f2a

ENV DJANGO_SETTINGS_MODULE=config.demo SERVER_PORT=8000
COPY --chown=pokeapi:pokeapi pokeapi/settings.py /code/config/demo.py
COPY --chown=pokeapi:pokeapi pokeapi/urls.py /code/config/demo_urls.py
COPY --chown=pokeapi:pokeapi agents/openapi.yml /code/openapi.yml
# Upstream's rolling release: fail rather than silently using a different snapshot.
ADD --chown=pokeapi:pokeapi --checksum=sha256:0804b314729da981ed09b80e00c65872736be7853ffe889caaa62f88c739e32f https://github.com/PokeAPI/pokeapi/releases/download/master-branch/db.sqlite3 /code/db.sqlite3
RUN python manage.py migrate --noinput

EXPOSE 8000
# The upstream CPU-based defaults are excessive for a laptop demo.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--access-logfile", "-"]
