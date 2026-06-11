# SpotUI

SpotUI is a small Dockerized web app that wraps `spotDL` with a queue-based browser UI. It is designed for self-hosting and for turning into a Docker image you can later use on Unraid.

## What it does

- Submit a Spotify track, album, playlist, artist URL, or a plain search query
- Queue downloads and process them one at a time
- Pick format, bitrate, overwrite behavior, and an optional subfolder
- Watch live logs and job history in the browser
- Save app state under `/config` and music under `/music`

## Run with Docker Compose

```bash
docker compose up --build
```

Then open [http://localhost:8080](http://localhost:8080).

On Apple Silicon macOS, if you need to run the container as x86_64/`linux/amd64`, use the x86 override file:

```bash
docker compose -f docker-compose.yml -f docker-compose.x86.yml up --build
```

The default local mounts are:

- `./data/music` -> `/music`
- `./data/config` -> `/config`

## Build your own image

```bash
docker build -t yourname/spotui:latest .
```

```bash
docker push yourname/spotui:latest
```

## Push to Docker Hub for arm64 and amd64

Use Docker Buildx to publish a multi-platform image manifest that includes both `linux/arm64` and `linux/amd64`.

```bash
docker login
docker buildx create --use --name multiarch-builder
docker buildx inspect --bootstrap
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t yourname/spotui:latest \
  -t yourname/spotui:0.1.0 \
  --push .
```

After the push completes, you can verify both platforms are present:

```bash
docker buildx imagetools inspect yourname/spotui:latest
```

You should see both `linux/amd64` and `linux/arm64` in the published manifest.

## Unraid notes

When you create the container in Unraid, map:

- AppData/config path to `/config`
- Your music share path to `/music`
- Container port `8080` to any host port you want

Recommended environment variables:

- `SPOTUI_OUTPUT_DIR=/music`
- `SPOTUI_CONFIG_DIR=/config`
- `SPOTUI_COOKIE_FILE=/config/cookies.txt`
- `SPOTUI_OUTPUT_TEMPLATE={artist}/{album}/{track-number} - {title}.{output-ext}`

If you use YouTube Music cookies for better matching or premium downloads, place `cookies.txt` inside the mapped config directory.

## App behavior

- Jobs are persisted in `/config/jobs.json`
- Downloads are restricted to the configured output root
- Cancelling a running job sends a terminate signal to the underlying `spotdl` process

## Useful examples

- Track: `https://open.spotify.com/track/...`
- Playlist: `https://open.spotify.com/playlist/...`
- Album: `https://open.spotify.com/album/...`
- Search: `Daft Punk - Something About Us`

## Reference

This project uses `spotDL` v4.5.0 and its `download` command. The official usage docs show the current syntax as `spotdl download [trackUrl]`, and the project also documents a built-in `spotdl web` mode plus the `--web-use-output-dir` flag for web flows:

- [spotDL repository](https://github.com/spotDL/spotify-downloader)
- [spotDL usage docs](https://spotdl.github.io/spotify-downloader/usage/)
